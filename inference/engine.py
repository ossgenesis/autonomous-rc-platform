"""
Real-time inference engine for SteerNet.

Usage:
    from inference.engine import InferenceEngine
    engine = InferenceEngine("models/steer_net.pt")
    command, confidence = engine.predict(frame)   # frame: np.ndarray BGR

    # Suppress stop predictions temporarily (G key nudge):
    engine.nudge(seconds=3)
"""

import time
from typing import Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from training.dataset_loader import CLASS_TO_IDX, CLASSES, IDX_TO_CLASS, IMG_H, IMG_W
from training.model import SteerNet, load_model

DEFAULT_CONFIDENCE_THRESHOLD = 0.25
# Scale the stop logit down so model needs strong evidence to predict stop.
# 0.4 = stop must be ~2.5x more likely than it would otherwise be to win.
DEFAULT_STOP_BIAS = 0.4

_STOP_IDX = CLASS_TO_IDX['stop']


class InferenceEngine:
    """Loads a SteerNet checkpoint and runs real-time steering prediction."""

    def __init__(
        self,
        checkpoint_path: str = "models/steer_net.pt",
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        stop_bias: float = DEFAULT_STOP_BIAS,
    ):
        self._device = self._pick_device()
        self._model = load_model(checkpoint_path, self._device)
        self._threshold = confidence_threshold
        self._stop_bias = stop_bias          # multiplier applied to stop logit (< 1 suppresses stop)
        self._nudge_until = 0.0              # monotonic time until which stop is fully suppressed
        self._last_latency_ms = 0.0
        self._dbg_count = 0

    @staticmethod
    def _pick_device() -> torch.device:
        if torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    def nudge(self, seconds: float = 3.0):
        """Suppress stop predictions for `seconds` — call this on G key press."""
        self._nudge_until = time.monotonic() + seconds

    @property
    def is_nudging(self) -> bool:
        return time.monotonic() < self._nudge_until

    def _preprocess(self, frame: np.ndarray) -> torch.Tensor:
        frame = cv2.resize(frame, (IMG_W, IMG_H))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(frame).permute(2, 0, 1).float() / 255.0
        return tensor.unsqueeze(0).to(self._device)

    def predict(self, frame: np.ndarray) -> Tuple[str, float]:
        """
        Return (command, confidence).

        Stop logit is scaled by stop_bias before softmax to reduce over-prediction of stop.
        If a nudge is active (G key), stop is zeroed out entirely for the nudge duration.
        If confidence < threshold after bias, returns ('stop', confidence).
        """
        t0 = time.monotonic()

        with torch.no_grad():
            logits = self._model(self._preprocess(frame))

        # Apply stop bias: scale down the stop logit before softmax
        logits = logits.clone()
        if time.monotonic() < self._nudge_until:
            logits[0, _STOP_IDX] = -1e9   # nudge active: stop is impossible
        else:
            logits[0, _STOP_IDX] *= self._stop_bias

        probs = F.softmax(logits, dim=1)[0]
        confidence, pred_idx = probs.max(0)
        confidence = confidence.item()
        command = IDX_TO_CLASS[pred_idx.item()]

        self._last_latency_ms = (time.monotonic() - t0) * 1000

        # Debug print every ~30 frames
        self._dbg_count += 1
        if self._dbg_count % 30 == 0:
            prob_str = '  '.join(f'{CLASSES[i]}:{probs[i].item():.2f}' for i in range(len(CLASSES)))
            nudge_tag = ' [NUDGE]' if self.is_nudging else ''
            print(f'\r[INFER] {prob_str}  →  {command} ({confidence:.0%}){nudge_tag}',
                  end='', flush=True)

        if confidence < self._threshold:
            return 'stop', confidence

        return command, confidence

    def predict_all(self, frame: np.ndarray) -> dict:
        """Return full probability dict — useful for HUD confidence bars."""
        with torch.no_grad():
            logits = self._model(self._preprocess(frame))
        logits[0, _STOP_IDX] *= self._stop_bias
        probs = F.softmax(logits, dim=1)[0]
        return {CLASSES[i]: probs[i].item() for i in range(len(CLASSES))}

    @property
    def latency_ms(self) -> float:
        return self._last_latency_ms

    @property
    def device(self) -> str:
        return str(self._device)
