"""
RC Car FPV telemetry app.

Usage:
    python telemetry_app.py [--rtmp URL] [--no-ble]

Controls:
    W / A / S / D  — drive (hold multiple keys for diagonal: W+A, W+D, etc.)
    SPACE          — stop
    R              — toggle dataset recording
    X or Q         — quit

Start the RTMP server first:
    bash infra/run_mediamtx.sh

Then set DJI Mimo live-stream URL to what the script prints.
"""

import argparse
import asyncio
import os
import threading
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from bleak import BleakClient
from pynput import keyboard as pynput_kb

from control.ble import BLEController, DEVICE_UUID
from video.source import RTMPSource
from video.hud import draw_hud
from recorder.dataset import DataRecorder

# Camera mount geometry recorded by user on 2026-05-28
MOUNT_META = {
    "camera": "DJI Action 2",
    "mount_height_mm": 105,
    "mount_tilt_deg": 0,
    "mount_offset_mm": 0,
    "rtmp_nominal_latency_ms": 2000,
}

_URL_FILE = os.path.join(os.path.dirname(__file__), "infra", ".rtmp_url")


def _default_rtmp() -> str:
    try:
        url = open(_URL_FILE).read().strip()
        if url:
            return url
    except OSError:
        pass
    return "rtmp://localhost/live/car"


DEFAULT_RTMP = _default_rtmp()

# ---------------------------------------------------------------------------
# Shared mutable state
# ---------------------------------------------------------------------------
ble = BLEController()
_running = True
_recording = False
_recorder: Optional[DataRecorder] = None
_rec_lock = threading.Lock()


def _toggle_recording():
    global _recording, _recorder
    with _rec_lock:
        _recording = not _recording
        if _recording and _recorder is None:
            session_id = datetime.now().strftime("%Y%m%dT%H%M%S")
            _recorder = DataRecorder(f"dataset/{session_id}")
            _recorder.write_meta(MOUNT_META)
            print(f"\r\n[REC] Recording → dataset/{session_id}")
        elif _recording:
            print("\r\n[REC] Resumed")
        else:
            print("\r\n[REC] Paused")


def _make_listener() -> pynput_kb.Listener:
    def on_press(key):
        global _running
        try:
            ch = key.char.lower()
        except AttributeError:
            ch = None

        if ch in ('x', 'q'):
            _running = False
        elif ch in ('w', 'a', 's', 'd'):
            ble.press(ch)
        elif ch == 'r':
            _toggle_recording()
        elif key == pynput_kb.Key.space:
            ble.release_all()

    def on_release(key):
        try:
            ch = key.char.lower()
        except AttributeError:
            return
        if ch in ('w', 'a', 's', 'd'):
            ble.release(ch)

    return pynput_kb.Listener(on_press=on_press, on_release=on_release)


async def _run(rtmp_url: str, skip_ble: bool):
    global _running, _recorder

    source = RTMPSource(rtmp_url)
    loop = asyncio.get_running_loop()

    listener = _make_listener()
    listener.start()

    print(f"Opening stream: {rtmp_url}")
    print("Controls: W/A/S/D = drive (hold combos OK)  SPACE = stop  R = record  X/Q = quit\n")

    fps_count = 0
    fps_t = time.monotonic()
    fps = 0.0

    async def main_loop():
        global _running, _recorder
        nonlocal fps, fps_count, fps_t

        while _running:
            ok, frame = await loop.run_in_executor(None, source.read)

            if not ok or frame is None:
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(
                    placeholder,
                    "Waiting for RTMP stream…  (start DJI Mimo live)",
                    (30, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2,
                )
                cv2.imshow("RC Car FPV", placeholder)
                if cv2.waitKey(200) & 0xFF == ord('q'):
                    _running = False
                continue

            fps_count += 1
            now = time.monotonic()
            if now - fps_t >= 1.0:
                fps = fps_count / (now - fps_t)
                fps_count = 0
                fps_t = now

            ts_ns = time.monotonic_ns()

            with _rec_lock:
                recording_now = _recording
                rec = _recorder

            if recording_now and rec is not None:
                frame_count = rec.record(frame, ble.current_key, ts_ns)
            else:
                frame_count = rec.frame_count if rec else 0

            state = {
                "command":     ble.current_key,
                "recording":   recording_now,
                "frame_count": frame_count,
                "fps":         fps,
                "ble_status":  ble.link_state,
                "latency_ms":  MOUNT_META["rtmp_nominal_latency_ms"],
            }

            display = draw_hud(frame, state)
            cv2.imshow("RC Car FPV", display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                _running = False

    async def _with_ble():
        print("Connecting to RC car via Bluetooth…")
        async with BleakClient(DEVICE_UUID) as client:
            print("BLE connected.")
            ble_task = asyncio.create_task(ble.run(client))
            await main_loop()
            ble_task.cancel()
            await asyncio.gather(ble_task, return_exceptions=True)

    async def _without_ble():
        ble.link_state = "DISABLED"
        await main_loop()

    if skip_ble:
        await _without_ble()
    else:
        await _with_ble()

    listener.stop()

    with _rec_lock:
        rec = _recorder
    if rec:
        rec.close()
        print(f"\r\nDataset saved ({rec.frame_count} frames).")

    source.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="RC Car FPV telemetry")
    parser.add_argument("--rtmp", default=DEFAULT_RTMP, help="RTMP stream URL")
    parser.add_argument("--no-ble", action="store_true", help="Skip BLE (video-only mode for testing)")
    args = parser.parse_args()

    asyncio.run(_run(args.rtmp, args.no_ble))


if __name__ == "__main__":
    main()
