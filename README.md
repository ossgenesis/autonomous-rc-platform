# Autonomous RC Platform

An open-source framework that transforms affordable, off-the-shelf RC cars into autonomous, computer-vision-powered vehicles — built step by step, using only a laptop and a toy car.

---

## Roadmap

- [x] **Phase 1 — BLE Protocol Reverse Engineering** *(complete)*
- [x] **Phase 2 — FPV Video Telemetry & Data Collection** *(complete)*
- [ ] **Phase 3 — Computer Vision & AI Self-Driving** *(up next)*

---

## System Architecture (Phase 2)

```
 ┌──────────────────┐        Wi-Fi         ┌──────────────────┐
 │  DJI Action 2    │ ──────────────────▶  │  DJI Mimo (phone)│
 │  (on RC car)     │    DJI proprietary   │                  │
 └──────────────────┘                      └────────┬─────────┘
                                                    │ RTMP push
                                                    │ rtmp://<laptop-ip>/live/car
                                                    ▼
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         Your Laptop                                  │
 │                                                                      │
 │   ┌─────────────────┐    frames    ┌──────────────────────────────┐  │
 │   │ MediaMTX server │ ──────────▶  │     telemetry_app.py         │  │
 │   │ (Docker)        │  RTMP ingest │                              │  │
 │   │ port 1935       │              │  ┌──────────┐  ┌──────────┐  │  │
 │   └─────────────────┘              │  │RTMPSource│  │ BLE ctrl │  │  │
 │                                    │  └────┬─────┘  └────┬─────┘  │  │
 │                                    │       │ frames       │ cmds   │  │
 │                                    │  ┌────▼─────────────▼──────┐ │  │
 │                                    │  │   draw_hud() overlay    │ │  │
 │                                    │  └────────────┬────────────┘ │  │
 │                                    │               │              │  │
 │                                    │  ┌────────────▼────────────┐ │  │
 │                                    │  │  cv2 window (FPV view)  │ │  │
 │                                    │  └─────────────────────────┘ │  │
 │                                    │                              │  │
 │                                    │  ┌──────────────────────┐   │  │
 │                                    │  │  DataRecorder (R key) │  │  │
 │                                    │  │  dataset/<session>/   │  │  │
 │                                    │  │  ├─ frames/*.jpg      │  │  │
 │                                    │  │  ├─ labels.csv        │  │  │
 │                                    │  │  └─ meta.json         │  │  │
 │                                    │  └──────────────────────┘   │  │
 │                                    └──────────────────────────────┘  │
 └───────────────────────────────────────────┬──────────────────────────┘
                                             │ Bluetooth Low Energy (BLE)
                                             │ 10-byte proprietary packets
                                             │ every 100 ms
                                             ▼
                                    ┌──────────────────┐
                                    │   RC Car         │
                                    │  (YC_CAR_DEMO)   │
                                    └──────────────────┘
```

---

## Repository Structure

```
rc-car-bluetooth/
│
│  ── Phase 2 entry point ──────────────────────────────────────
├─ telemetry_app.py          # Main FPV app: video + drive + record
│
│  ── Video pipeline ───────────────────────────────────────────
├─ video/
│   ├─ source.py             # VideoSource ABC, RTMPSource, V4L2Source
│   └─ hud.py               # Overlay: D-pad, REC dot, BLE/FPS telemetry
│
│  ── BLE control layer ────────────────────────────────────────
├─ control/
│   └─ ble.py               # BLEController class (extracted, reusable)
│
│  ── Dataset recorder ─────────────────────────────────────────
├─ recorder/
│   └─ dataset.py            # Saves frames + labels.csv + meta.json
│
│  ── RTMP server infra ────────────────────────────────────────
├─ infra/
│   ├─ mediamtx.yml          # MediaMTX server config (Docker)
│   └─ run_mediamtx.sh       # One-command server launcher
│
│  ── Dataset output (git-ignored) ────────────────────────────
├─ dataset/
│   └─ <session_id>/
│       ├─ frames/000000.jpg ...
│       ├─ labels.csv
│       └─ meta.json
│
│  ── Session reviewer ─────────────────────────────────────────
├─ tools/
│   └─ replay_session.py     # Plays back a recorded session with HUD
│
│  ── Phase 1 scripts (standalone, still work) ─────────────────
├─ ble_controller.py         # Original WASD driver (no video)
├─ ble_scanner.py            # Scan for nearby BLE devices
├─ ble_inspector.py          # Inspect a device's GATT services/chars
├─ ble_fuzzer.py             # Fuzz 1–2 byte BLE commands
├─ ble_smart_fuzzer.py       # Fuzz common 3–4 byte manufacturer sequences
└─ ble_brute_fuzzer.py       # Exhaustive 65,536-combination brute-force
```

---

## Script Reference

### `telemetry_app.py` — Main FPV app

The top-level glue that runs everything together.

```
 Keyboard input (W/A/S/D/SPACE/R/X)
        │
        ▼
 _keyboard_loop()            ← asyncio task (runs in thread executor)
        │
        ├─── set_command() ──▶ BLEController ──▶ RC Car (every 100ms)
        │
        └─── toggle record ──▶ DataRecorder.record()
                                      │
 RTMPSource.read() ──▶ draw_hud() ──▶ cv2.imshow("RC Car FPV")
```

**Controls:**

| Key | Action |
|-----|--------|
| `W` | Forward |
| `S` | Backward |
| `A` | Left |
| `D` | Right |
| `SPACE` | Stop |
| `R` | Toggle recording on/off |
| `X` or `Q` | Quit |

**Flags:**
```bash
python telemetry_app.py                        # normal mode
python telemetry_app.py --rtmp rtmp://x/live/car  # custom RTMP URL
python telemetry_app.py --no-ble               # video-only (no car needed)
```

---

### `video/source.py` — Video input abstraction

```
VideoSource (abstract base)
    │
    ├─ RTMPSource(url)      ← DJI Mimo → MediaMTX → OpenCV
    │    • Background drain thread keeps frame buffer fresh (low latency)
    │    • CAP_PROP_BUFFERSIZE = 1 to minimize stale frames
    │
    └─ V4L2Source(device)   ← HDMI capture card (bench / Phase 3 training)
         • device=0 for macOS, /dev/videoN for Linux
```

Swapping video sources requires one line change in `telemetry_app.py`. The rest of the app is source-agnostic.

---

### `video/hud.py` — On-screen display overlay

Draws three regions onto every frame before displaying:

```
 ┌─────────────────────────────────────────────────┐
 │                                  ● REC  #001234 │  ← Top right
 │                                                 │
 │              [ live camera feed ]               │
 │                                                 │
 │  ┌───┐                       FPS:  29.8         │
 │  │ W │   ← active key        BLE:  OK           │  ← Bottom
 │  ┌───┬───┬───┐               RTMP: ~2000ms      │
 │  │ A │ S │ D │                                  │
 │  └───┴───┴───┘                                  │
 │  D-Pad (bottom left)       Telemetry (bottom right) │
 └─────────────────────────────────────────────────┘
```

API: `draw_hud(frame: np.ndarray, state: dict) -> np.ndarray`

State dict keys: `command`, `recording`, `frame_count`, `fps`, `ble_status`, `latency_ms`

---

### `control/ble.py` — Bluetooth controller

```
BLEController
    │
    ├─ set_command(key)    ← called from keyboard thread (thread-safe)
    │   'w' | 's' | 'a' | 'd' | 'stop'
    │
    ├─ run(client)         ← asyncio coroutine, sends packet every 100ms
    │   writes 10-byte hex payload to GATT characteristic fff2
    │
    ├─ link_state          ← "OK" | "ERROR" | "DISCONNECTED" | "DISABLED"
    └─ current_key         ← last command sent (used by HUD + recorder)
```

Intercepted BLE payloads (reverse-engineered from iPhone traffic):

| Command | Hex payload |
|---------|-------------|
| Forward | `AA 00 02 00 00 00 00 42 00 02` |
| Backward | `AA 00 02 00 00 00 00 41 00 02` |
| Left | `AA 00 02 00 00 00 00 44 00 02` |
| Right | `AA 00 02 00 00 00 00 48 00 02` |
| Stop | `AA 00 02 00 00 00 00 40 00 02` |

---

### `recorder/dataset.py` — Training data recorder

Saves every frame paired with the steering command being sent at that exact moment, using `time.monotonic_ns()` for sub-millisecond timestamp sync between frame and label.

```
dataset/
└─ 20260528T143012/          ← session folder (datetime)
    ├─ frames/
    │   ├─ 000000.jpg        ← JPEG 90% quality, native resolution
    │   ├─ 000001.jpg
    │   └─ ...
    ├─ labels.csv            ← ts_ms, command, frame_file
    └─ meta.json             ← camera model, mount geometry, latency
```

`labels.csv` example:
```
ts_ms,command,frame_file
1748430612345,w,000000.jpg
1748430612378,w,000001.jpg
1748430612411,stop,000002.jpg
```

---

### `infra/run_mediamtx.sh` — RTMP server launcher

```
 run_mediamtx.sh
       │
       ├─ detects your LAN IP  (en0 → en1 → en2 → fallback)
       ├─ saves it to infra/.rtmp_url  (auto-read by telemetry_app.py)
       ├─ starts Docker: bluenviron/mediamtx, port 1935
       ├─ waits until port 1935 is open
       └─ prints a box with the URL to paste into DJI Mimo
```

Output:
```
  ┌─────────────────────────────────────────────┐
  │  SERVER READY — paste this into DJI Mimo:   │
  │                                             │
  │  URL: rtmp://192.168.31.114/live/car        │
  │                                             │
  │  Press Ctrl+C to stop.                      │
  └─────────────────────────────────────────────┘
```

---

### `tools/replay_session.py` — Dataset viewer

Plays back a recorded session frame-by-frame with the HUD overlay, so you can visually review what the car saw and what command was being sent.

```bash
python tools/replay_session.py dataset/20260528T143012
```

**Controls during replay:**

| Key | Action |
|-----|--------|
| `SPACE` | Pause / resume |
| `←` / `→` | Step one frame (when paused) |
| `Q` | Quit |

---

### Phase 1 scripts (protocol tools)

These are standalone tools for reverse-engineering and testing BLE devices. They do not depend on any Phase 2 modules.

| Script | What it does |
|--------|-------------|
| `ble_controller.py` | Original standalone WASD driver. No video. Use this if you only want to drive without the camera. |
| `ble_scanner.py` | Scans the air for all nearby BLE devices and prints their name + UUID. |
| `ble_inspector.py` | Connects to a specific device and lists all its GATT services and characteristics. |
| `ble_fuzzer.py` | Sends every possible 1-byte and 2-byte command to find which ones the car responds to. |
| `ble_smart_fuzzer.py` | Tests common 3- and 4-byte manufacturer command patterns. Faster than brute force. |
| `ble_brute_fuzzer.py` | Exhaustively tries all 65,536 possible 2-byte combinations. Last resort. |

---

## Setup & Usage

### Requirements

- Python 3.9+
- Docker Desktop (for the RTMP server)
- Homebrew (macOS)
- A DJI Action 2 with DJI Mimo installed on your phone
- A BLE-capable laptop

### Installation

```bash
git clone https://github.com/ossgenesis/autonomous-rc-platform.git
cd autonomous-rc-platform

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
brew install ffmpeg
```

### Running Phase 2 (FPV driving + data collection)

**Step 1 — Start the RTMP server** (keep this terminal open):
```bash
bash infra/run_mediamtx.sh
```
Copy the RTMP URL it prints (e.g. `rtmp://192.168.31.114/live/car`).

**Step 2 — Go live on your phone:**
Open DJI Mimo → connect Action 2 → Live Stream → Custom RTMP → paste the URL → Go Live.

**Step 3 — Launch the app** (in a new terminal):
```bash
source venv/bin/activate
python telemetry_app.py
```

Drive with `W/A/S/D`. Press `R` to record a dataset session. Press `X` to quit.

**Step 4 — Review your recordings:**
```bash
python tools/replay_session.py dataset/<session_id>
```

### Running Phase 1 only (no camera)

```bash
source venv/bin/activate
python ble_controller.py
```

---

## Phase 3 Preview

The dataset collected in Phase 2 will be used to train a CNN that predicts steering commands from camera frames. The trained model will then replace the keyboard loop — the car drives itself using the same BLE abstraction layer we built in Phase 1.

```
Phase 3 target architecture:

 Camera frame ──▶ CNN model ──▶ predicted command ──▶ BLEController ──▶ RC Car
                  (trained on
                   Phase 2 data)
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). We are looking for contributions to:
- Phase 3 (CNN training pipeline, lane detection)
- BLE payloads for other toy car models
- Hardware mount designs for the DJI Action 2

## License

Apache 2.0 — see [LICENSE](./LICENSE).
