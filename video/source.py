import abc
import threading
from typing import Optional, Tuple

import cv2
import numpy as np


class VideoSource(abc.ABC):
    @abc.abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        ...

    @abc.abstractmethod
    def release(self):
        ...

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


class RTMPSource(VideoSource):
    """Low-latency RTMP reader for DJI Mimo → MediaMTX pipeline.

    A background thread drains the decoder queue continuously so read()
    always returns the most recent frame, not a buffered-up stale one.
    Requires FFmpeg-enabled OpenCV; install ffmpeg via Homebrew on macOS.
    """

    def __init__(self, url: str):
        self._cap = cv2.VideoCapture(url)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._lock = threading.Lock()
        self._ok = False
        self._frame: Optional[np.ndarray] = None
        self._alive = True

        self._thread = threading.Thread(target=self._drain, daemon=True)
        self._thread.start()

    def _drain(self):
        while self._alive:
            ok, frame = self._cap.read()
            with self._lock:
                self._ok = ok
                self._frame = frame

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            return self._ok, self._frame

    def release(self):
        self._alive = False
        self._thread.join(timeout=2)
        self._cap.release()


class V4L2Source(VideoSource):
    """HDMI-capture via a USB capture card.
    macOS: device index (0, 1, …). Linux: /dev/videoN passed as int."""

    def __init__(self, device: int = 0):
        self._cap = cv2.VideoCapture(device)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        return self._cap.read()

    def release(self):
        self._cap.release()
