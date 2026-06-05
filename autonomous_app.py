"""
RC Car autonomous driving app — Phase 3.

The CNN watches the live DJI Action 2 feed and predicts steering commands.
You can toggle between AI and MANUAL mode at any time.

Usage:
    python autonomous_app.py
    python autonomous_app.py --model models/steer_net.pt --threshold 0.6

Controls:
    TAB          — toggle AI / MANUAL mode
    W/A/S/D      — manual drive; hold combos for diagonal (W+A, W+D, etc.)
    SPACE        — emergency stop (stays in current mode)
    X or Q       — quit
"""

import argparse
import asyncio
import os
import time
from typing import Optional

import cv2
import numpy as np
from bleak import BleakClient
from pynput import keyboard as pynput_kb

from control.ble import BLEController, DEVICE_UUID
from video.source import RTMPSource
from video.hud import draw_hud
from inference.engine import DEFAULT_CONFIDENCE_THRESHOLD, InferenceEngine

_URL_FILE = os.path.join(os.path.dirname(__file__), "infra", ".rtmp_url")


def _default_rtmp() -> str:
    try:
        url = open(_URL_FILE).read().strip()
        if url:
            return url
    except OSError:
        pass
    return "rtmp://localhost/live/car"


# ── Shared state ─────────────────────────────────────────────────────────────
ble = BLEController()
_running = True
_mode = "MANUAL"
_last_ai_cmd = "stop"
_last_confidence = 0.0


def _make_listener() -> pynput_kb.Listener:
    def on_press(key):
        global _running, _mode
        try:
            ch = key.char.lower()
        except AttributeError:
            ch = None

        if ch in ('x', 'q'):
            _running = False
        elif ch in ('w', 'a', 's', 'd'):
            _mode = "MANUAL"
            ble.press(ch)
        elif key == pynput_kb.Key.space:
            ble.release_all()
            print("\r\n[STOP] Emergency stop")
        elif key == pynput_kb.Key.tab:
            _mode = "AI" if _mode == "MANUAL" else "MANUAL"
            ble.release_all()
            print(f"\r\n[MODE] Switched to {_mode}")

    def on_release(key):
        try:
            ch = key.char.lower()
        except AttributeError:
            return
        if ch in ('w', 'a', 's', 'd'):
            ble.release(ch)

    return pynput_kb.Listener(on_press=on_press, on_release=on_release)


async def _run(rtmp_url: str, model_path: str, threshold: float):
    global _running, _mode, _last_ai_cmd, _last_confidence

    print(f"Loading model: {model_path}")
    engine = InferenceEngine(model_path, confidence_threshold=threshold)
    print(f"Model loaded on {engine.device}")

    source = RTMPSource(rtmp_url)
    loop = asyncio.get_running_loop()

    listener = _make_listener()
    listener.start()

    print("Connecting to RC car via Bluetooth…")
    async with BleakClient(DEVICE_UUID) as client:
        print("BLE connected.")
        print("Controls: TAB = toggle AI/MANUAL  W/A/S/D = manual (combos OK)  SPACE = stop  X = quit\n")

        ble_task = asyncio.create_task(ble.run(client))

        fps_count, fps_t, fps = 0, time.monotonic(), 0.0

        while _running:
            ok, frame = await loop.run_in_executor(None, source.read)

            if not ok or frame is None:
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "Waiting for RTMP stream…",
                            (60, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
                cv2.imshow("RC Car Autonomous", placeholder)
                if cv2.waitKey(200) & 0xFF == ord('q'):
                    _running = False
                continue

            fps_count += 1
            now = time.monotonic()
            if now - fps_t >= 1.0:
                fps = fps_count / (now - fps_t)
                fps_count, fps_t = 0, now

            if _mode == "AI":
                cmd, conf = await loop.run_in_executor(None, engine.predict, frame)
                _last_ai_cmd = cmd
                _last_confidence = conf
                ble.set_command(cmd)

            state = {
                "command":     ble.current_key,
                "recording":   False,
                "frame_count": 0,
                "fps":         fps,
                "ble_status":  ble.link_state,
                "latency_ms":  2000,
                "mode":        _mode,
                "ai_command":  _last_ai_cmd,
                "confidence":  _last_confidence,
                "infer_ms":    engine.latency_ms,
            }

            display = draw_hud(frame, state)
            cv2.imshow("RC Car Autonomous", display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                _running = False

        ble_task.cancel()
        await asyncio.gather(ble_task, return_exceptions=True)

    listener.stop()
    source.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Autonomous RC car driver")
    parser.add_argument("--rtmp",      default=_default_rtmp(), help="RTMP stream URL")
    parser.add_argument("--model",     default="models/steer_net.pt", help="Path to trained checkpoint")
    parser.add_argument("--threshold", type=float, default=DEFAULT_CONFIDENCE_THRESHOLD,
                        help="Confidence threshold below which AI sends 'stop'")
    args = parser.parse_args()

    if not os.path.exists(args.model):
        print(f"Error: model not found at '{args.model}'.")
        print("Train it first:  python training/train.py")
        import sys; sys.exit(1)

    asyncio.run(_run(args.rtmp, args.model, args.threshold))


if __name__ == "__main__":
    main()
