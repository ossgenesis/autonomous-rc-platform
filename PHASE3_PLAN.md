# Phase 3: Computer Vision & AI Self-Driving

**Status:** Planning · **Owner:** Claude + Gemini (Antigravity) · **Started:** 2026-05-31

---

## 1. Goal

Replace the human keyboard loop with a trained CNN that watches the live DJI Action 2 feed and predicts steering commands in real time — so the car drives itself using the same BLE abstraction built in Phase 1.

```
Phase 2 (manual):    Camera ──▶ Human eyes ──▶ Keyboard ──▶ BLEController ──▶ Car
Phase 3 (autonomous): Camera ──▶ CNN model  ──▶ Command  ──▶ BLEController ──▶ Car
```

Everything below the BLEController stays the same. Phase 3 only replaces what's above it.

---

## 2. Architecture

```
                    ┌──────────────────────────────────────────────────────┐
                    │                  Training pipeline                   │
                    │                                                      │
                    │  dataset/<sessions>/                                 │
                    │  frames/*.jpg + labels.csv                           │
                    │         │                                            │
                    │         ▼                                            │
                    │  training/dataset_loader.py                          │
                    │  • resize to 160×120                                 │
                    │  • normalize pixels                                  │
                    │  • class-balance via weighted sampler                │
                    │  • 80/20 train/val split                             │
                    │         │                                            │
                    │         ▼                                            │
                    │  training/model.py  (SteerNet)                       │
                    │  • Input:  160×120×3 frame                           │
                    │  • Output: 5-class softmax                           │
                    │           (w / a / s / d / stop)                    │
                    │         │                                            │
                    │         ▼                                            │
                    │  training/train.py                                   │
                    │  • AdamW, CrossEntropyLoss, LR scheduler             │
                    │  • saves best checkpoint → models/steer_net.pt       │
                    │         │                                            │
                    │         ▼                                            │
                    │  training/evaluate.py  [GEMINI]                      │
                    │  • accuracy, confusion matrix, per-class recall      │
                    │  • training curves plot                               │
                    └──────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────────────┐
                    │               Autonomous driving loop                │
                    │                                                      │
                    │  DJI Action 2 ──▶ RTMPSource ──▶ frame              │
                    │                                     │                │
                    │                       inference/engine.py            │
                    │                       • loads steer_net.pt           │
                    │                       • preprocesses frame           │
                    │                       • returns command + confidence │
                    │                                     │                │
                    │                          autonomous_app.py           │
                    │                          • draws HUD (updated [GEMINI])│
                    │                          • safety: human override key │
                    │                          • sends to BLEController    │
                    │                                     │                │
                    │                               RC Car (BLE)           │
                    └──────────────────────────────────────────────────────┘
```

---

## 3. Model: SteerNet

A lightweight custom CNN. No pretrained weights — we train from scratch on the Phase 2 dataset. Simple enough to run at 30+ FPS on CPU (MacBook).

```
Input: 160×120×3 (RGB frame, normalized)
│
├─ Conv2d(3→16, 5×5)  + ReLU + MaxPool2×2
├─ Conv2d(16→32, 3×3) + ReLU + MaxPool2×2
├─ Conv2d(32→64, 3×3) + ReLU + MaxPool2×2
├─ Flatten
├─ Linear(64×17×12 → 256) + ReLU + Dropout(0.4)
├─ Linear(256 → 64)        + ReLU
└─ Linear(64 → 5)          + Softmax

Output classes: ['w', 'a', 's', 'd', 'stop']
```

If CPU inference is too slow (<15 FPS), we upgrade to MobileNetV2 with transfer learning. Noted as a risk.

---

## 4. Dataset requirements

| Class | Minimum frames needed | Notes |
|-------|----------------------|-------|
| `w` (forward) | 500 | Most common — should be over-represented in Phase 2 data |
| `a` (left) | 300 | Turn data is usually under-collected |
| `s` (backward) | 200 | Often rare in forward-driving sessions |
| `d` (right) | 300 | Same as left |
| `stop` | 200 | Captured at intersections / before turns |

**Total minimum: ~1,500 labelled frames.** One 3-minute driving session at 30 FPS yields ~5,400 frames — more than enough if the route has a variety of turns.

The dataset loader will print a class distribution table on startup so you can see if any class is dangerously underrepresented before wasting a training run.

---

## 5. Module breakdown

| Path | Purpose | Owner |
|------|---------|-------|
| `training/dataset_loader.py` | `RCDataset` (PyTorch Dataset), class-balanced `DataLoader`, train/val split | CLAUDE |
| `training/model.py` | `SteerNet` nn.Module definition | CLAUDE |
| `training/train.py` | Training loop, AdamW, LR scheduler, checkpoint saving | CLAUDE |
| `training/evaluate.py` | Confusion matrix, per-class accuracy, training curve plots | GEMINI |
| `inference/engine.py` | `InferenceEngine` — loads `.pt`, preprocesses frame, returns `(command, confidence)` | CLAUDE |
| `autonomous_app.py` | Top-level autonomous driver — wires RTMPSource + InferenceEngine + BLEController | CLAUDE |
| `video/hud.py` (update) | Add autonomous mode HUD: confidence bar, AI vs manual mode indicator | GEMINI |
| `requirements.txt` (update) | Add `torch`, `torchvision`, `matplotlib` | CLAUDE |

---

## 6. Milestones

| # | Milestone | Owner | Done when |
|---|-----------|-------|-----------|
| M1 | `training/dataset_loader.py` — loads Phase 2 data, prints class distribution | CLAUDE | unit test loads a session, prints 5-class counts |
| M2 | `training/model.py` — SteerNet definition | CLAUDE | `model(torch.randn(1,3,120,160))` returns shape `(1,5)` |
| M3 | `training/train.py` — full training loop | CLAUDE | runs on user's dataset, saves `models/steer_net.pt` |
| M4 | First training run on Phase 2 data | USER | val accuracy >60% (baseline; will improve with more data) |
| M5 | `training/evaluate.py` — confusion matrix + curves | GEMINI | PNG plots saved to `models/eval/` |
| M6 | `inference/engine.py` — real-time inference | CLAUDE | processes 640×480 frame in <50ms on MacBook CPU |
| M7 | `autonomous_app.py` — first autonomous drive (slow, short track) | CLAUDE | car completes a straight without human input |
| M8 | HUD update for autonomous mode | GEMINI | shows AI confidence + manual-override indicator |
| M9 | Field test + README update | USER | video of autonomous lap |

---

## 7. Safety design

The car is small and slow, but we still need a kill switch:

```
autonomous_app.py safety rules:
  1. SPACE key = immediate stop + drop back to MANUAL mode
  2. Any WASD key = instant manual override (AI off until 'A' pressed again)
  3. confidence < threshold (default 0.55) → send 'stop' instead of predicted command
  4. BLE link_state != 'OK' → stop all commands immediately
```

Mode switch: press `TAB` to toggle between `MANUAL` and `AI` modes. The HUD will show the current mode prominently.

---

## 8. Open questions

- **Q1 [USER]** — How many frames did you collect in Phase 2? Run `python tools/replay_session.py --count` to get a class breakdown before we start.
- **Q2 [USER]** — GPU available? (check with `python -c "import torch; print(torch.backends.mps.is_available())"` — Apple Silicon Macs have MPS). Affects training time: CPU ~30min, MPS ~5min for the target dataset size.
- **Q3 [GEMINI]** — Evaluation plots: static PNGs saved to `models/eval/`, or a live TensorBoard dashboard? Propose in this file before M5 starts.
- **Q4 [BOTH]** — Confidence threshold for the stop-on-low-confidence safety rule: 0.55 proposed. Too conservative = car stops constantly. Too loose = unpredictable. Gemini to weigh in after seeing M5 confusion matrix.
- **Q5 [USER]** — Test environment for autonomous driving? (straight hallway, oval track, figure-8?) Determines what class balance we need most.

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Insufficient training data | Medium | Drive more Phase 2 sessions; dataset_loader warns on low class counts |
| Model too slow for real-time on CPU | Low | SteerNet is tiny; fallback = reduce input to 80×60 |
| RTMP latency makes autonomous control unstable | Medium | Start with slow speed, short track; long-term fix = HDMI capture for Phase 3 |
| Class imbalance (too much 'w', not enough turns) | High | Weighted sampler in DataLoader; record dedicated turning sessions |
| Car overshoots turns (control lag) | Medium | Add a `command_hold_ms` delay to smooth out rapid switching |

---

## 10. References

- Phase 2 dataset: `dataset/` (git-ignored)
- BLE abstraction: [control/ble.py](control/ble.py)
- Video abstraction: [video/source.py](video/source.py)
- Collaboration ledger: [COLLAB.md](COLLAB.md)
- PyTorch docs: https://pytorch.org/docs/stable/
