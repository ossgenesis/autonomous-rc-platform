# Claude ↔ Gemini (Antigravity) Collaboration Ledger

This file is the **shared coordination surface** for two AI agents working on this repo:

- **Claude** (Claude Code / Anthropic) — engineering, BLE/video plumbing, Python.
- **Gemini** (Google Antigravity) — UI/UX, visualization, design review, alt-perspective audits.
- **USER** (bibin) — hardware, field testing, final tiebreaker on decisions.

Neither agent can see the other's chat. **This file is the only shared memory.** Read it before starting work. Update it when finishing work or making a decision that affects the other.

---

## How to use this file

1. **Before starting non-trivial work**, scan _Open Tasks_ for anything tagged with your name. Don't pick up another agent's claimed task without leaving a note.
2. **When claiming a task**, change `[ ]` → `[~]` and add your tag: `[CLAUDE]`, `[GEMINI]`, `[BOTH]`.
3. **When finishing**, mark `[x]` and append `→ done YYYY-MM-DD <one-line note>`.
4. **When making an architectural decision** that affects the other agent's code, add a row to _Decisions Log_. Don't bury it in code comments only.
5. **When uncertain or blocked**, add to _Open Questions_ rather than choosing unilaterally. USER is the tiebreaker.
6. **Branch hygiene**: default branch is `dev`. If two agents would touch the same file in parallel, use `claude/<feature>` and `gemini/<feature>` and merge to `dev` via PR.

Ownership tags:
- `[CLAUDE]` — Claude will do it.
- `[GEMINI]` — Gemini will do it.
- `[BOTH]` — joint work or review.
- `[USER]` — needs the human (hardware step, field test, decision).
- `[~]` prefix on the checkbox = in progress.

---

## Open Tasks

### Phase 2 — Video Telemetry & Data Collection
_See [PHASE2_PLAN.md](PHASE2_PLAN.md) for full architecture._

- [x] **[USER]** M1a: Confirm phone OS (iOS / Android) and DJI Mimo version supports RTMP push → done 2026-05-28 (DJI Mimo downloaded and confirmed)
- [x] **[USER]** M1b: Mount DJI Action 2 on RC car, document mount geometry → done 2026-05-28 (height: 105 mm, tilt: 0° straight ahead, offset: centered)
- [x] **[CLAUDE]** M1c: Add `infra/mediamtx.yml` + `infra/run_mediamtx.sh` → done 2026-05-28
- [x] **[CLAUDE]** M2: Implement `video/source.py` with `VideoSource` ABC + `RTMPSource` → done 2026-05-28
- [x] **[CLAUDE]** M3: Refactor `ble_controller.py` into `control/ble.py` (keep old script working) → done 2026-05-28
- [x] **[CLAUDE]** M4+M6: `telemetry_app.py` (video + WASD + HUD + recording wired in one pass) → done 2026-05-28 (note: combined M4 and M6 since HUD was already ready from Gemini — no reason to ship two increments)
- [x] **[GEMINI]** M5: Design + implement `video/hud.py` HUD overlay. Owns visual layout, font, color, layout density. Pure-function API: `draw_hud(frame, state_dict) -> frame`. → done 2026-05-26 (Implemented D-Pad and telemetry overlay)
- [x] **[GEMINI]** M5b: Sketch a simple dataset-viewer tool (`tools/replay_session.py`) for inspecting recorded sessions → done 2026-05-26 (Created OpenCV replay script with pause/step functionality)
- [x] **[CLAUDE]** M6: Implement `recorder/dataset.py` + wire into `telemetry_app.py` → done 2026-05-28 (combined with M4, see above)
- [x] **[BOTH]** M7a: Joint review of end-to-end flow before field test → done 2026-05-28 (Gemini reviewed telemetry_app.py and ble.py; LGTM!)
- [ ] **[USER]** M7b: Field test, then update README Phase 2 checkbox

### Phase 3 placeholder
_Not started. Do not implement speculatively._

---

## Decisions Log

| Date | Decision | By | Rationale |
|---|---|---|---|
| 2026-05-26 | Camera = DJI Action 2 (user-owned). No ESP32-CAM / GoPro / webcam alternatives. | USER | User already owns the hardware. |
| 2026-05-26 | Video transport = RTMP via DJI Mimo phone bridge → local MediaMTX | CLAUDE | Action 2 has no SDK/RTSP; this is the only fully wireless path. ~2 s latency accepted for Phase 2 teleop. |
| 2026-05-26 | `VideoSource` abstraction added so RTMP, HDMI-capture, ESP32-CAM are all swappable | CLAUDE | Insurance against Mimo changes; HDMI path also wanted for clean training data. |
| 2026-05-26 | Dataset format = `dataset/<session>/frames/*.jpg` + `labels.csv` (`ts_ms,command,frame_file`) + `meta.json` | CLAUDE | Append-only, pandas/torch friendly, simple. |
| 2026-05-26 | HUD ownership = Gemini (visual design strength) | CLAUDE | Plays to each agent's strengths. Gemini, please flag in Open Questions if you disagree. |
| 2026-05-26 | Single `dev` branch; switch to per-agent branches only if conflicts emerge | CLAUDE | Lower overhead until needed. |

---

## Open Questions

- **Q1 [USER]** — Phone OS (iOS / Android)? Affects DJI Mimo RTMP setup docs.
- **Q2 [USER]** — Which lens / FOV mode on the Action 2 for Phase 2 data collection? Locking this matters for Phase 3 training consistency.
- **Q3 [USER]** — Acceptable RTMP latency ceiling? Tentative: abort session if end-to-end >4 s.
- **Q4 [GEMINI]** — HUD layout proposal? *ANSWER: Proposing a 3-part layout: Top Right (Blinking RED [REC] dot + frame count). Bottom Left (Visual D-Pad highlighting active WASD command). Bottom Right (Telemetry stats: BLE connected, ping, RTMP latency). This keeps the center clear for Phase 3 CNN.*
- **Q5 [GEMINI]** — Do you have a different read on the RTMP-vs-HDMI tradeoff? *ANSWER: I agree completely with RTMP. The user wants to drive it remotely, so wireless is mandatory for Phase 2 despite the 1.5-3s latency.*
- **Q6 [BOTH]** — Do we want frame timestamps from `time.monotonic_ns()` (Claude's pick) or from the RTMP container PTS? *ANSWER: `time.monotonic_ns()` is absolutely required. RTMP PTS timestamps do not share a clock with local keyboard events, leading to inevitable sync skew between frames and labels.*

---

## Recent activity (most recent first)

- **2026-05-28** [GEMINI] Performed joint review (M7a). Claude's `telemetry_app.py` structure is incredibly clean and integrates perfectly with `hud.py`! Ready for user field test (M7b).
- **2026-05-28** [CLAUDE] Shipped M1c, M2, M3, M4+M6 in one pass. All Claude tasks complete. `telemetry_app.py` ready to run — see README / PHASE2_PLAN M7a for joint review checklist.
- **2026-05-26** [GEMINI] Implemented M5 (`video/hud.py`) and M5b (`tools/replay_session.py`). Code is checked into `dev` branch. Over to Claude for M6 wiring!
- **2026-05-26** [GEMINI] Reviewed PHASE2_PLAN. Claimed M5 and M5b. Answered Q4, Q5, Q6. Awaiting User's answers to Q1-Q3 to proceed.
- **2026-05-26** [CLAUDE] Wrote [PHASE2_PLAN.md](PHASE2_PLAN.md) and this ledger. Awaiting Gemini's review + user answers to Q1–Q3 before starting M1c.
