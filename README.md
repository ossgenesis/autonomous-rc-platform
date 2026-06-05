# Autonomous RC Platform

An open-source framework that transforms affordable, off-the-shelf RC cars into autonomous, computer-vision-powered vehicles — built step by step, using only a laptop and a toy car.

---

## Roadmap

- [x] **Phase 1 — BLE Protocol Reverse Engineering** *(complete)*
- [x] **Phase 2 — FPV Video Telemetry & Data Collection** *(complete)*
- [x] **Phase 3 — Computer Vision & AI Self-Driving** *(in progress — model trained, autonomous loop running)*

---

## System Architecture (Phase 3 — Full Stack)

```
 ┌──────────────────┐        Wi-Fi         ┌──────────────────┐
 │  DJI Action 2    │ ──────────────────▶  │  DJI Mimo (phone)│
 │  (on RC car)     │    DJI proprietary   │                  │
 └──────────────────┘                      └────────┬─────────┘
                                                    │ RTMP push
                                                    ▼
 ┌──────────────────────────────────────────────────────────────────────┐
 │                         Your Laptop                                  │
 │                                                                      │
 │   ┌─────────────────┐    frames    ┌──────────────────────────────┐  │
 │   │ MediaMTX server │ ──────────▶  │     autonomous_app.py        │  │
 │   │ (Docker)        │  RTMP ingest │                              │  │
 │   │ port 1935       │              │  ┌──────────┐  ┌──────────┐  │  │
 │   └─────────────────┘              │  │RTMPSource│  │ BLE ctrl │  │  │
 │                                    │  └────┬─────┘  └────┬─────┘  │  │
 │                                    │       │ frames       │ cmds   │  │
 │                                    │  ┌────▼──────────┐  │        │  │
 │                                    │  │InferenceEngine│  │        │  │
 │                                    │  │  (SteerNet)   │──┘        │  │
 │                                    │  └────┬──────────┘           │  │
 │                                    │       │ command + confidence  │  │
 │                                    │  ┌────▼─────────────────────┐│  │
 │                                    │  │   draw_hud() overlay     ││  │
 │                                    │  └────────────┬─────────────┘│  │
 │                                    │  ┌────────────▼─────────────┐│  │
 │                                    │  │  cv2 window (FPV + HUD)  ││  │
 │                                    │  └──────────────────────────┘│  │
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
│  ── Phase 3 entry point ──────────────────────────────────────
├─ autonomous_app.py         # AI self-driving app (TAB = toggle AI/manual)
│
│  ── Phase 3: AI training pipeline ───────────────────────────
├─ training/
│   ├─ dataset_loader.py     # Loads dataset/, stratified split, weighted sampler
│   ├─ model.py              # SteerNet CNN architecture definition
│   ├─ train.py              # Training loop with weighted loss + cosine LR
│   └─ evaluate.py           # Confusion matrix + training curves → models/eval/
│
│  ── Phase 3: Real-time inference ────────────────────────────
├─ inference/
│   └─ engine.py             # InferenceEngine: loads checkpoint, runs predict()
│
│  ── Trained model output (git-ignored) ──────────────────────
├─ models/
│   ├─ steer_net.pt          # Best checkpoint (saved whenever val acc improves)
│   ├─ train_log.csv         # Per-epoch loss/accuracy log for evaluate.py
│   └─ eval/
│       ├─ confusion_matrix.png
│       └─ curves.png
│
│  ── Phase 2 entry point ──────────────────────────────────────
├─ telemetry_app.py          # FPV app: video + drive + record training data
│
│  ── Video pipeline ───────────────────────────────────────────
├─ video/
│   ├─ source.py             # VideoSource ABC, RTMPSource, V4L2Source
│   └─ hud.py               # HUD overlay: D-pad, mode, AI confidence, telemetry
│
│  ── BLE control layer ────────────────────────────────────────
├─ control/
│   └─ ble.py               # BLEController class (thread-safe, reusable)
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

## Phase 3 — AI Self-Driving

### How it works

The car learns to steer by watching recordings of you driving. You drive manually while the app records what the camera sees and what command you're sending at every frame. That (image → command) pair becomes one training example.

After enough sessions, a small CNN called **SteerNet** is trained on those recordings. At runtime, every camera frame is passed through the model, which predicts the best command (`w`, `a`, `s`, `d`, or `stop`). The prediction is sent to the BLE controller exactly like a keyboard press would be.

```
Training time:
  recorded frame  ──▶  SteerNet  ──▶  predicted command
                        (trains to match)
                                  ──▶  actual command (label)

Run time:
  live frame  ──▶  SteerNet  ──▶  predicted command  ──▶  BLE  ──▶  RC car
```

### SteerNet model

SteerNet is a lightweight CNN designed to run in real-time on a laptop CPU or Apple Silicon MPS. Input frames are resized to 160×120 pixels.

```
Input: (B, 3, 120, 160)  — RGB frame

Conv2d(3, 16, 3) + ReLU + MaxPool     → (B, 16, 59, 79)
Conv2d(16, 32, 3) + ReLU + MaxPool    → (B, 32, 28, 38)
Conv2d(32, 64, 3) + ReLU + MaxPool    → (B, 64, 13, 18)

Flatten → Linear(64*13*18, 256) + ReLU + Dropout(0.5)
         → Linear(256, 5)

Output: logits over 5 classes: [w, a, s, d, stop]
```

### Dataset format

Each training session produces a folder under `dataset/`:

```
dataset/
└─ 20260605T115827/          ← session folder (datetime)
    ├─ frames/
    │   ├─ 000000.jpg        ← JPEG, native camera resolution
    │   ├─ 000001.jpg
    │   └─ ...
    ├─ labels.csv            ← ts_ms, command, frame_file
    └─ meta.json             ← camera model, mount height, RTMP latency
```

`labels.csv` example:
```
ts_ms,command,frame_file
44687,stop,000000.jpg
44711,w,000001.jpg
44735,w,000002.jpg
44759,a,000003.jpg
```

Commands in the CSV are raw keystrokes: `w` (forward), `a` (left), `s` (backward), `d` (right), `stop` (no key). Diagonal combos recorded as `a+w`, `d+w` etc. are automatically mapped to their dominant direction (`a`, `d`) during loading.

### Class imbalance — what we learned

The biggest challenge in this kind of imitation learning dataset is class imbalance. When you drive manually, the car spends far more time stopped than actively turning. A naive model will exploit this and just predict `stop` for everything — it will score high overall accuracy while being completely useless as a driver.

In our dataset (~106k frames across 5 sessions):

| Command | Frames | % of dataset |
|---------|--------|-------------|
| stop | ~92,000 | 87% |
| a (left) | ~5,400 | 5% |
| d (right) | ~3,800 | 4% |
| w (forward) | ~2,600 | 2% |
| s (backward) | ~1,900 | 2% |

We fixed this with two techniques applied together:

**1. WeightedRandomSampler** — during training, each class is sampled with equal probability regardless of how many examples it has. Minority classes like `d` are oversampled so the model sees them as often as `stop`.

**2. Weighted CrossEntropyLoss** — the loss function penalises mistakes on rare classes more heavily. A wrong prediction on a `d` frame costs ~24× more than a wrong prediction on a `stop` frame.

**3. Stratified validation split** — the validation set is built by sampling 20% from each class separately (rather than taking the last 20% of the timeline, which can be almost entirely `stop` frames). This ensures val accuracy reflects real per-class performance.

### Training results (current best)

Best validation accuracy: **76.7%** — but the headline number is less important than the per-class breakdown:

| Class | Val accuracy |
|-------|-------------|
| w (forward) | 93% |
| a (left) | 97% |
| s (backward) | 97% |
| d (right) | 96% |
| stop | 74% |

All four steering commands are predicted at 93–97% accuracy. The `stop` class at 74% means the model occasionally predicts a steering command when the car should be idle — which is a safer failure mode than the opposite.

Training curves show healthy learning: val loss decreases monotonically across 30 epochs, and the val/train gap is moderate (no severe overfitting).

### Running Phase 3

**Step 1 — Collect training data** (Phase 2 telemetry app, press R to record):
```bash
source venv/bin/activate
python telemetry_app.py
```
Drive around. Record multiple sessions with deliberate turns. Aim for at least 1,000 frames of each steering command.

**Step 2 — Train SteerNet:**
```bash
python -m training.train --dataset dataset/ --epochs 30 --batch 32
```
Checkpoint saves automatically to `models/steer_net.pt` whenever validation accuracy improves.

```bash
# Resume an interrupted run:
python -m training.train --resume models/steer_net.pt --epochs 10
```

**Step 3 — Evaluate the model:**
```bash
python -m training.evaluate
```
Saves `models/eval/confusion_matrix.png` and `models/eval/curves.png`. Check the confusion matrix — every steering class should have a strong diagonal. If one command is only predicted as `stop`, collect more data for that command and retrain.

**Step 4 — Run the autonomous app:**
```bash
python autonomous_app.py
```

**Controls:**

| Key | Action |
|-----|--------|
| `TAB` | Toggle AI / MANUAL mode |
| `W/A/S/D` | Manual drive (hold combos for diagonal) |
| `SPACE` | Emergency stop (stays in current mode) |
| `X` or `Q` | Quit |

**Flags:**
```bash
python autonomous_app.py --model models/steer_net.pt   # default
python autonomous_app.py --threshold 0.4               # lower confidence cutoff (less cautious)
python autonomous_app.py --rtmp rtmp://x/live/car      # custom RTMP URL
```

The `--threshold` flag controls how confident the model must be before sending a command. Below the threshold it sends `stop` instead. Default is 0.55. Lower it if the car stops too often in AI mode; raise it if it makes erratic moves.

### HUD in AI mode

When `TAB` switches to AI mode, the HUD shows:

```
 ┌─────────────────────────────────────────────────┐
 │  MODE: AI                                       │  ← top left (green)
 │  Infer: 8.3ms                                   │
 │                                                 │
 │  AI cmd: W  ████████████████░░░░  82%           │  ← confidence bar
 │              [ live camera feed ]               │
 │                                                 │
 │  ┌───┐                       FPS:  29.8         │
 │  │ W │                       BLE:  OK           │
 │  ┌───┬───┬───┐               RTMP: ~2000ms      │
 │  │ A │ S │ D │                                  │
 │  └───┴───┴───┘                                  │
 └─────────────────────────────────────────────────┘
```

The D-pad highlights whichever command the model is currently sending. The confidence bar shows the softmax probability for the predicted class.

### Known limitations and next steps

- **Track dependency** — the model learns from one specific environment. It will generalise poorly to a different floor, lighting, or track layout. Collect data in multiple environments for better generalisation.
- **No temporal context** — SteerNet sees only the current frame. It has no memory of where the car was a moment ago. A recurrent model (LSTM + CNN) or frame stacking would help with smooth steering.
- **RTMP latency** — the DJI Mimo RTMP stream has ~2 seconds of latency. The model is trained on frames that were captured ~2s before the command was logged, so the visual scene and the label are roughly aligned — but fast manoeuvres can still be misaligned.
- **More data always helps** — especially right turns (`d`), which are typically under-collected. Drive deliberate figure-8 and slalom patterns when recording.

---

## Phase 2 — FPV Telemetry & Data Collection

### `telemetry_app.py` — Main FPV app

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
python telemetry_app.py                               # normal mode
python telemetry_app.py --rtmp rtmp://x/live/car      # custom RTMP URL
python telemetry_app.py --no-ble                      # video-only (no car needed)
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
    └─ V4L2Source(device)   ← HDMI capture card (bench testing)
         • device=0 for macOS, /dev/videoN for Linux
```

---

### `video/hud.py` — On-screen display overlay

API: `draw_hud(frame: np.ndarray, state: dict) -> np.ndarray`

State dict keys used by Phase 2: `command`, `recording`, `frame_count`, `fps`, `ble_status`, `latency_ms`

Additional keys used by Phase 3: `mode`, `ai_command`, `confidence`, `infer_ms`

---

### `control/ble.py` — Bluetooth controller

```
BLEController
    │
    ├─ set_command(key)    ← replaces active command (thread-safe)
    │   'w' | 's' | 'a' | 'd' | 'stop'
    │
    ├─ press(key)          ← add a key to active set (for combo support)
    ├─ release(key)        ← remove a key from active set
    ├─ release_all()       ← emergency stop
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

### `tools/replay_session.py` — Dataset viewer

Plays back a recorded session frame-by-frame with the HUD overlay, so you can visually review what the car saw and what command was being sent.

```bash
python tools/replay_session.py dataset/20260605T115827
```

| Key | Action |
|-----|--------|
| `SPACE` | Pause / resume |
| `←` / `→` | Step one frame (when paused) |
| `Q` | Quit |

---

## Phase 1 — BLE Protocol Reverse Engineering

These are standalone tools for reverse-engineering and testing BLE devices. They do not depend on any Phase 2 or Phase 3 modules.

| Script | What it does |
|--------|-------------|
| `ble_controller.py` | Original standalone WASD driver. No video. Use if you only want to drive without the camera. |
| `ble_scanner.py` | Scans for all nearby BLE devices and prints their name + UUID. |
| `ble_inspector.py` | Connects to a specific device and lists all its GATT services and characteristics. |
| `ble_fuzzer.py` | Sends every possible 1-byte and 2-byte command to find which ones the car responds to. |
| `ble_smart_fuzzer.py` | Tests common 3- and 4-byte manufacturer command patterns. Faster than brute force. |
| `ble_brute_fuzzer.py` | Exhaustively tries all 65,536 possible 2-byte combinations. Last resort. |

---

## Setup & Installation

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

### Running the RTMP server

```bash
bash infra/run_mediamtx.sh
```

This detects your LAN IP, starts a MediaMTX Docker container on port 1935, and prints the URL to paste into DJI Mimo:

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

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). We are looking for contributions to:
- Phase 3 improvements (data augmentation, temporal models, lane detection)
- BLE payloads for other toy car models
- Hardware mount designs for the DJI Action 2

## License

Apache 2.0 — see [LICENSE](./LICENSE).
