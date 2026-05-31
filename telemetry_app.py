"""
RC Car FPV telemetry app.

Usage:
    python telemetry_app.py [--rtmp URL] [--no-ble]

Controls (terminal window must be focused):
    W / A / S / D  — drive
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
import sys
import time
import tty
import termios
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from bleak import BleakClient

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
# Shared mutable state (all writes from asyncio main thread or executor pool)
# ---------------------------------------------------------------------------
ble = BLEController()
_running = True
_recording = False
_recorder = None  # type: Optional[DataRecorder]


def _get_char() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


async def _keyboard_loop():
    global _running, _recording, _recorder
    loop = asyncio.get_running_loop()
    while _running:
        ch = await loop.run_in_executor(None, _get_char)
        ch = ch.lower()
        if ch in ('x', 'q'):
            _running = False
        elif ch in ('w', 'a', 's', 'd'):
            ble.set_command(ch)
        elif ch == ' ':
            ble.set_command('stop')
        elif ch == 'r':
            _recording = not _recording
            if _recording:
                if _recorder is None:
                    session_id = datetime.now().strftime("%Y%m%dT%H%M%S")
                    _recorder = DataRecorder(f"dataset/{session_id}")
                    _recorder.write_meta(MOUNT_META)
                    print(f"\r\n[REC] Recording → dataset/{session_id}")
                else:
                    print("\r\n[REC] Resumed")
            else:
                print("\r\n[REC] Paused")


async def _run(rtmp_url: str, skip_ble: bool):
    global _running, _recording, _recorder

    source = RTMPSource(rtmp_url)
    loop = asyncio.get_running_loop()

    async def _with_ble(fn):
        print("Connecting to RC car via Bluetooth…")
        async with BleakClient(DEVICE_UUID) as client:
            print("BLE connected.")
            ble_task = asyncio.create_task(ble.run(client))
            await fn()
            ble_task.cancel()
            await asyncio.gather(ble_task, return_exceptions=True)

    async def _without_ble(fn):
        ble.link_state = "DISABLED"
        await fn()

    print(f"Opening stream: {rtmp_url}")
    print("Controls: W/A/S/D = drive  SPACE = stop  R = record  X/Q = quit\n")

    fps_tracker_count = 0
    fps_tracker_t = time.monotonic()
    fps = 0.0

    kb_task = asyncio.create_task(_keyboard_loop())

    async def main_loop():
        global _running, _recording, _recorder
        nonlocal fps, fps_tracker_count, fps_tracker_t

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

            # FPS — rolling 1-second window
            fps_tracker_count += 1
            now = time.monotonic()
            if now - fps_tracker_t >= 1.0:
                fps = fps_tracker_count / (now - fps_tracker_t)
                fps_tracker_count = 0
                fps_tracker_t = now

            ts_ns = time.monotonic_ns()

            if _recording and _recorder is not None:
                frame_count = _recorder.record(frame, ble.current_key, ts_ns)
            else:
                frame_count = _recorder.frame_count if _recorder else 0

            state = {
                "command":    ble.current_key,
                "recording":  _recording,
                "frame_count": frame_count,
                "fps":        fps,
                "ble_status": ble.link_state,
                "latency_ms": MOUNT_META["rtmp_nominal_latency_ms"],
            }

            display = draw_hud(frame, state)
            cv2.imshow("RC Car FPV", display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                _running = False

        kb_task.cancel()
        await asyncio.gather(kb_task, return_exceptions=True)

    if skip_ble:
        await _without_ble(main_loop)
    else:
        await _with_ble(main_loop)

    if _recorder:
        _recorder.close()
        print(f"\r\nDataset saved ({_recorder.frame_count} frames).")

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
