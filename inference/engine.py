"""
Real-time inference engine for SteerNet.

Usage:
    from inference.engine import InferenceEngine
    engine = InferenceEngine("models/steer_net.pt")
    command, confidence = engine.predict(frame)   # frame: np.ndarray BGR
"""

import time
from typing import Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from training.dataset_loader import CLASS_TO_IDX, CLASSES, IDX_TO_CLASS, IMG_H, IMG_W
from training.model import SteerNet, load_model

# If model confidence is below this, send 'stop' instead (safety rule)
DEFAULT_CONFIDENCE_THRESHOLD = 0.55


class InferenceEngine:
    """Loads a SteerNet checkpoint and runs real-time steering prediction."""

    def __init__(
        self,
        checkpoint_path: str = "models/steer_net.pt",
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        self._device = self._pick_device()
        self._model = load_model(checkpoint_path, self._device)
        self._threshold = confidence_threshold
        self._last_latency_ms = 0.0

    @staticmethod
    def _pick_device() -> torch.device:
        if torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    def _preprocess(self, frame: np.ndarray) -> torch.Tensor:
        """BGR frame (any size) → (1, 3, H, W) normalised tensor."""
        frame = cv2.resize(frame, (IMG_W, IMG_H))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(frame).permute(2, 0, 1).float() / 255.0
        return tensor.unsqueeze(0).to(self._device)

    def predict(self, frame: np.ndarray) -> Tuple[str, float]:
        """
        Return (command, confidence).
        If confidence < threshold, returns ('stop', confidence) regardless of prediction.
        """
        t0 = time.monotonic()

        with torch.no_grad():
            logits = self._model(self._preprocess(frame))
            probs = F.softmax(logits, dim=1)[0]

        confidence, pred_idx = probs.max(0)
        confidence = confidence.item()
        command = IDX_TO_CLASS[pred_idx.item()]

        self._last_latency_ms = (time.monotonic() - t0) * 1000

        if confidence < self._threshold:
            return 'stop', confidence

        return command, confidence

    def predict_all(self, frame: np.ndarray) -> dict:
        """Return full probability dict for each class — useful for HUD confidence bars."""
        with torch.no_grad():
            logits = self._model(self._preprocess(frame))
            probs = F.softmax(logits, dim=1)[0]
        return {CLASSES[i]: probs[i].item() for i in range(len(CLASSES))}

    @property
    def latency_ms(self) -> float:
        return self._last_latency_ms

    @property
    def device(self) -> str:
        return str(self._device)
