# Phase 2: Video Telemetry & Data Collection

**Status:** Planning · **Owner:** Claude + Gemini (Antigravity) · **Started:** 2026-05-26

---

## 1. Goal

Transform the existing headless BLE controller into an **FPV-style driving cockpit**: the operator sees live video from a DJI Action 2 mounted on the RC car while driving it from the laptop via WASD, and every frame + command is recorded as training data for Phase 3.

### Non-goals (defer to Phase 3)
- CNN training, lane detection, obstacle avoidance.
- Closed-loop autonomous driving.
- Multi-car / multi-camera support.
- Remote (off-LAN) operation.

---

## 2. Why DJI Action 2 (and what it costs us)

The user is mounting a DJI Action 2 that they already own. The Action 2 has **no public SDK and no RTSP**, which constrains the video pipeline:

| Path | Latency | Use case |
|---|---|---|
| **RTMP via DJI Mimo phone bridge** (chosen default) | 1.5–3 s | Live wireless driving |
| HDMI-out via front-touchscreen module + USB capture card | <200 ms | Bench / clean training data |
| Hardware-replace with ESP32-CAM | ~300 ms | Not in scope — user wants DJI |

We accept the RTMP latency for Phase 2 because the goal is *teleoperation + data capture*, not real-time control. Phase 3 may revisit this.

---

## 3. Architecture

```
                    ┌──────────────────┐
                    │  DJI Action 2    │  (mounted on RC car)
                    └────────┬─────────┘
                             │ DJI Wi-Fi
                             ▼
                    ┌──────────────────┐
                    │ Phone (DJI Mimo) │  Live → RTMP destination
                    └────────┬─────────┘
                             │ RTMP push
                             │ rtmp://<laptop-ip>/live/car
                             ▼
                    ┌──────────────────┐
                    │ MediaMTX (local) │  docker container, port 1935
                    └────────┬─────────┘
                             │ rtmp://localhost/live/car
                             ▼
   ┌──────────────────────────────────────────────────────────┐
   │                  telemetry_app.py                        │
   │                                                          │
   │   ┌────────────────┐   ┌──────────────────────────┐     │
   │   │  VideoSource   │──▶│  HUD overlay (OpenCV)    │     │
   │   │  (RTMPSource)  │   │  • current command       │     │
   │   └────────┬───────┘   │  • FPS / link latency    │     │
   │            │           │  • BLE link state        │     │
   │            ▼           └──────────────────────────┘     │
   │   ┌────────────────┐                                    │
   │   │ DataRecorder   │   writes frames + labels.csv       │
   │   └────────────────┘                                    │
   │                                                          │
   │   ┌────────────────┐   ┌──────────────────────────┐     │
   │   │  KeyboardLoop  │──▶│  BLESender (existing)    │──┐  │
   │   └────────────────┘   └──────────────────────────┘  │  │
   └──────────────────────────────────────────────────────┼──┘
                                                          │
                                                          ▼
                                                   ┌────────────┐
                                                   │  RC car    │
                                                   └────────────┘
```

---

## 4. Module breakdown

| Path | Purpose | New / Refactor |
|---|---|---|
| `control/ble.py` | Extract `bluetooth_sender`, `keyboard_listener`, `COMMANDS` from current `ble_controller.py`. Expose `BLEController` class with `set_command(cmd)` and `link_state` property. | Refactor |
| `video/source.py` | `VideoSource` ABC + `RTMPSource(url)` (ffmpeg/OpenCV `VideoCapture`) + stub `V4L2Source(device)` for HDMI capture later. | New |
| `video/hud.py` | `draw_hud(frame, state)` — overlays command, FPS, BLE state, RTMP latency estimate. Pure function, easy to test. | New |
| `recorder/dataset.py` | `DataRecorder(session_dir)` — `record(frame, command, ts)` → `frames/NNNNNN.jpg` + append to `labels.csv`. | New |
| `telemetry_app.py` | Top-level: asyncio event loop wiring BLE + video + recorder + cv2 window. | New |
| `infra/mediamtx.yml` | Minimal MediaMTX config exposing `/live/car` on RTMP 1935. | New |
| `infra/run_mediamtx.sh` | `docker run --rm -v ./infra/mediamtx.yml:/mediamtx.yml -p 1935:1935 bluenviron/mediamtx` | New |
| `ble_controller.py` | **Keep as-is** until `telemetry_app.py` is verified end-to-end. | Untouched |
| `requirements.txt` | Add `opencv-python`, `numpy`. Keep `bleak`. | New / update |
| `README.md` | Update Phase 2 checkbox + driving instructions once shipped. | Defer |

### Dataset format
```
dataset/
  <session_id>/                  # e.g. 20260526T143012
    frames/
      000000.jpg                 # JPEG 90% quality, native resolution
      000001.jpg
      ...
    labels.csv                   # ts_ms,command,frame_file
    meta.json                    # camera, lens FOV, BLE device id, notes
```
Simple, append-only, easy to load with pandas/torch in Phase 3.

---

## 5. Milestones

| # | Milestone | Owner | Done when |
|---|---|---|---|
| M1 | MediaMTX runs locally and accepts RTMP from phone | USER + CLAUDE | `ffplay rtmp://localhost/live/car` shows DJI feed |
| M2 | `RTMPSource` reads frames from MediaMTX in Python | CLAUDE | unit test displays 100 frames in cv2 window |
| M3 | `control/ble.py` refactor — `ble_controller.py` still works against it | CLAUDE | manual drive test with refactored code |
| M4 | `telemetry_app.py` minimal: video + WASD, no recording, no HUD | CLAUDE | user can drive while seeing video |
| M5 | HUD overlay (FPS, command, BLE link) | GEMINI (UI strength) | visual review |
| M6 | `DataRecorder` writes frames + labels.csv | CLAUDE | 60-sec drive produces a valid dataset dir |
| M7 | End-to-end field test, README updated, Phase 2 checkbox ticked | USER | demo video / sign-off |

---

## 6. Open questions (need user or Gemini input)

1. **Phone OS?** iOS vs Android Mimo apps have slightly different RTMP UX. → blocks M1.
2. **DJI Mimo RTMP availability** — Action 2 RTMP may require a current Mimo version + sometimes a DJI account. Need to confirm before M1.
3. **Lens / FOV** — DJI Action 2 has multiple FOV modes. Pick one and lock it; switching mid-dataset poisons Phase 3 training.
4. **Mount geometry** — height + tilt + offset from car centerline. Must be repeatable session-to-session. Photo + measurements in `dataset/<session>/meta.json`.
5. **Latency tolerance** — at what RTMP lag do we abort a session? Tentative: >4 s end-to-end = unusable.
6. **Branch strategy** — single `dev` branch or split (`claude/phase2-*` vs `gemini/phase2-*`)? Default: single `dev`, use COLLAB.md ownership to avoid stomping.

---

## 7. Risks

- **DJI Mimo RTMP feature gets disabled/changed** — fallback: HDMI capture path via `V4L2Source`. Worth pre-building the stub.
- **Action 2 thermal shutdown** during long drives — known issue. Mitigation: limit sessions to ~15 min, log start/stop times in `meta.json`.
- **BLE event loop starvation** when cv2 window blocks — mitigation: run cv2 in main thread, BLE + video read in asyncio tasks, communicate via `asyncio.Queue`.
- **Frame/command sync skew** — record both with monotonic `time.monotonic_ns()`, not wall clock.

---

## 8. References

- Current control code: [ble_controller.py](ble_controller.py)
- MediaMTX: https://github.com/bluenviron/mediamtx
- Collaboration ledger: [COLLAB.md](COLLAB.md)
