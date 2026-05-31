import csv
import json
import os
import time

import cv2
import numpy as np


class DataRecorder:
    """Writes (frame, command, timestamp) tuples to disk in a Phase-3-ready format.

    Layout:
        dataset/<session_id>/
            frames/000000.jpg ...
            labels.csv          (ts_ms, command, frame_file)
            meta.json
    """

    def __init__(self, session_dir: str):
        self._dir = session_dir
        self._frames_dir = os.path.join(session_dir, "frames")
        os.makedirs(self._frames_dir, exist_ok=True)

        self._csv_file = open(os.path.join(session_dir, "labels.csv"), "w", newline="")
        self._writer = csv.writer(self._csv_file)
        self._writer.writerow(["ts_ms", "command", "frame_file"])

        self._count = 0

    def record(self, frame: np.ndarray, command: str, ts_ns: int) -> int:
        """Save one frame + label. Returns the new total frame count."""
        filename = f"{self._count:06d}.jpg"
        cv2.imwrite(
            os.path.join(self._frames_dir, filename),
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 90],
        )
        self._writer.writerow([ts_ns // 1_000_000, command, filename])
        self._count += 1
        return self._count

    def write_meta(self, meta: dict):
        with open(os.path.join(self._dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

    def close(self):
        self._csv_file.flush()
        self._csv_file.close()

    @property
    def frame_count(self) -> int:
        return self._count

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
