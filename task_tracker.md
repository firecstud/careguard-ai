# CareGuard AI — Task Tracker
### 5-Day Hackathon Build | 3 Sub-Teams

**Legend:** `[ ]` Not started · `[/]` In progress · `[x]` Done · `[!]` Blocked

---

## Repo & Branching Strategy

```
main          ← stable, demo-ready only. Push here Day 4 and 5 only.
  └── develop ← integration branch. All teams merge here.
        ├── feature/stage1-audio    ← Stage 1 team
        ├── feature/stage2-audit    ← Stage 2 team
        └── feature/frontend        ← Frontend
```

**Rules:**
- Never commit directly to `main` or `develop`
- Each team pushes to their own feature branch daily
- All teams merge into `develop` on **Day 4**
- Push to `main` only when something is fully working

**Shared files — coordinate before editing:**
- `shared/transcript_schema.py` — the JSON contract between Stage 1 and Stage 2. Lock on Day 1, no changes without team agreement.
- `.env.example` — list all required environment variables here.

---

## Daily Stand-Up (15 min, every morning)
Each person answers three questions:
1. What did I finish yesterday?
2. What am I doing today?
3. Is anything blocking me?

Blockers get resolved after stand-up, not during.

---

## Day 1 — Setup & Foundation
**Goal:** Everyone has working API calls, locked JSON contract, and validated diarization approach by end of day.

### All Teams
- [ ] Create GitHub repo, set up branch structure
- [ ] Add `.env.example` with `DASHSCOPE_API_KEY` placeholder
- [ ] Each person clones repo and sets up local environment
- [ ] **Unify the JSON contract** — confirm `"utterances"` as the array key name. Lock `shared/transcript_schema.py` and do not change after today without team agreement
- [ ] Set up FastAPI skeleton with `/health`, `/analyze`, and `/transcribe` routes

### Stage 1 — Audio Pipeline
> **Provider change:** DashScope was replaced by Google Gemini — one audio `generate_content` call handles ASR + diarization (reuses `GEMINI_API_KEY`). Live mic streaming is out of scope for the prototype.

- N/A — DashScope diarization validation spike: provider changed to Gemini; speaker roles come from the transcription prompt, not a `speaker_id` API field
- N/A — Qwen-max test call: provider changed to Gemini; the key was already verified in Stage 2
- [x] Build the file upload endpoint (`POST /transcribe`) and transcription client using Gemini audio input — this is the **primary demo path**
- N/A — real-time ASR WebSocket / Web Audio capture and first-to-speak heuristic: live streaming out of scope
- [ ] **End-of-day check:** Upload an audio file → get back a speaker-labeled transcript JSON

### Stage 2 — Audit Engine
- [ ] Install dependencies: `pip install dashscope python-dotenv rapidfuzz`
- [ ] Make a test Qwen-max call to verify API key works
- [ ] Build `audit/trigger_phrases.py` — full `TRIGGER_PHRASES` dict for all 6 liability categories
- [ ] Build `audit/required_responses.py` — full `REQUIRED_RESPONSES` dict
- [ ] Generate 5 synthetic test transcripts using Qwen (Scenarios A–E)
- [ ] Save to `tests/transcripts/scenario_a.json` through `scenario_e.json`
- [ ] Write keyword scanner — loops through patient utterances, checks trigger phrases
- [ ] **End-of-day check:** Scenario A fires HIGH flag. Scenario D fires nothing.

### Frontend
- [ ] Set up React + Vite: `npm create vite@latest frontend -- --template react`
- [ ] Build `FileUpload` component: drag-and-drop audio file upload (primary demo path)
- [ ] Build `SessionControls` component: Start button, Stop button, status indicator (stretch — live streaming)
- [ ] Build `TranscriptView` component: color-coded utterances (Therapist = blue, Patient = teal)
- [ ] Wire `TranscriptView` to a hardcoded test transcript JSON
- [ ] **End-of-day check:** Hardcoded Scenario A renders with correct speaker colors. File upload component accepts a file.

**End-of-day bonus: throwaway E2E skeleton** — wire file upload → hardcoded utterance → hardcoded flag → UI display. This makes Day 4 integration incremental instead of a big-bang.

---

## Day 2 — Core Features
**Goal:** Each team's main feature working in isolation.

### Stage 1 — Audio Pipeline
- [x] Implement speaker mapping from diarization output (Gemini assigns Therapist/Patient roles by conversational function; labels normalized case-insensitively)
- N/A — streaming session accumulation and first-to-speak heuristic: live streaming out of scope; roles are assigned by conversational function, not speaking order
- [x] Add `POST /session/{id}/swap-speakers` endpoint for manual label correction
- [x] Test file upload → transcription → speaker labeling end-to-end with a patched transcriber (deterministic unit + endpoint tests)
- [ ] **End-of-day check:** Upload a 2-minute conversation → get correctly labeled Therapist/Patient transcript

### Stage 2 — Audit Engine
- [ ] Implement response window checker: scan next N=5 therapist utterances for required phrases
- [ ] Add fuzzy matching secondary layer via `rapidfuzz` using `fuzz.partial_ratio` (not `fuzz.ratio` — short phrases against long utterances need partial matching), 80% similarity threshold
- [ ] Wire Qwen-max for recommendation generation with try/except and static fallback per category (see `FALLBACK_RECOMMENDATIONS` in `llm_client.py`)
- [ ] Build `generate_recommendations_batch` for concurrent LLM calls via `asyncio.gather` (5 flags × 3s each = 15s serial vs ~3s parallel)
- [ ] Build report assembler: collects flags, calculates risk score, returns JSON
- [ ] Risk score formula (saturating curve):
  ```python
  import math
  raw_score = HIGH_count * 40 + MEDIUM_count * 20 + LOW_count * 10
  risk_score = min(100, int(100 * (1 - math.exp(-raw_score / 50))))
  ```
  This produces ~87 for the demo scenario (1 HIGH + 1 MEDIUM) and differentiates severity better than a linear clamp
- [ ] Create `POST /analyze` endpoint — accepts transcript JSON, returns report JSON
- [ ] **End-of-day check:** `/analyze` returns correct flags and risk scores for all 5 scenarios

### Frontend
- [ ] Build `LiabilityReport` component: risk score + list of flag cards
- [ ] Flag cards show: category, severity badge, patient quote, what was missed, recommendation
- [ ] Build loading state component with spinner and status text
- [ ] Connect `FileUpload` to call `POST /transcribe` and display transcript
- [ ] Connect analysis button to call `/analyze` after transcription completes
- [ ] Wire `TranscriptView` to display transcript from API response
- [ ] **End-of-day check:** Upload file → transcript appears → click analyze → report renders correctly

---

## Day 3 — Depth & Reliability
**Goal:** No crashes on edge cases. UI is polished. All scenarios produce correct output.

### Stage 1 — Audio Pipeline
- [x] Handle file upload edge cases: unsupported formats (400), oversize >100MB (413, streamed in 1MB chunks), no usable audio (422)
- [x] Add session metadata to transcript output: `session_id`, `audio_file`, per-utterance `start_time`/`end_time` (top-level `duration_seconds` not implemented)
- [x] Add error recovery: if the Gemini audio call fails, return a clear error to the frontend (503 no key / 502 call failed — no fallback exists for audio)
- N/A — streaming silence gaps / session cleanup / reconnection: live streaming out of scope
- [ ] Test with 3 different audio files of varying quality
- [ ] **End-of-day check:** Upload a 10-minute file → completes without crashes

### Stage 2 — Audit Engine
- [ ] Expand `TRIGGER_PHRASES` with paraphrasing variants ("I don't want to be here", "what's the point", "thinking about it")
- [ ] Add `detection_method` field to every flag: e.g. `"keyword_match: 'better off without me'"` or `"fuzzy_match: 'better off gone' (87%)"`
- [ ] Implement hybrid detection: send unmatched patient utterances to qwen-max in a single batch prompt asking if any contain liability-relevant disclosures the keyword list missed. Label matches as `detection_method: "semantic_match"`. Optional but makes the system more robust
- [ ] Validate **zero false positives** on Scenario D — tune if needed
- [ ] Add informed consent detection: if session is short (< 5 exchanges) and therapist never says "confidential" → MEDIUM flag
- [ ] **End-of-day check:** All 5 scenarios produce exactly the expected output, no exceptions

### Frontend
- [ ] Add risk score gauge (CSS arc or `react-circular-progressbar`)
- [ ] Make flag cards clickable — highlights the triggering line in `TranscriptView`
- [ ] Severity colors: HIGH = red border, MEDIUM = amber, LOW = grey
- [x] Add speaker swap button in UI (calls `POST /session/{id}/swap-speakers`, visible only for audio-derived reports)
- [ ] Polish: dark theme (`#0f172a` bg), clean typography (Inter font), consistent spacing
- [ ] Layout works on 1920×1080 (demo screen size)
- [ ] **End-of-day check:** Show the UI to a team member unfamiliar with it — can they read the report without help?

---

## Day 4 — Integration Day
**Goal:** Full end-to-end pipeline running with file upload.

### Morning — Backend Integration (Stage 1 + Stage 2)
- [ ] Stage 1 merges `feature/stage1-audio` → `develop`
- [ ] Stage 2 merges `feature/stage2-audit` → `develop`
- [ ] Joint integration test: upload audio file → Stage 1 transcription → Stage 2 `/analyze` → report JSON
- [ ] Fix any JSON schema mismatches between Stage 1 output and Stage 2 expected input

### Afternoon — Frontend Joins
- [ ] Frontend merges `feature/frontend` → `develop`
- [ ] Wire frontend file upload to live Stage 1 backend
- [ ] Wire frontend report display to live Stage 2 `/analyze` response
- [ ] **Full E2E test #1:** Upload Scenario A audio → HIGH suicidality flag appears in UI
- [ ] **Full E2E test #2:** Upload clean session (Scenario D) → no HIGH flags
- [ ] **Full E2E test #3:** Upload the planned demo audio → confirms it produces the right report
- [ ] Fix integration bugs (allocate 4–6 hours, this is expected)
- [ ] Merge `develop` → `main` once E2E is confirmed working

### Stretch (if time permits)
- [ ] Wire live streaming WebSocket path end-to-end
- [ ] Test browser mic → live transcript → real-time flags

---

## Day 5 — Polish & Demo Prep
**Goal:** A demo you can run confidently in front of judges with zero panic.

### Morning — Hardening
- [ ] Fix remaining bugs from Day 4
- [ ] **Record the demo audio:** Record a 2–3 minute scripted therapy session (therapist misses suicidal statement) — save as `demo/demo_session.mp3`
- [ ] Pre-run the full demo with the recorded audio and cache the result as static fallback: `demo/cached_report.json`
- [ ] Add a hidden "demo mode" button in frontend — loads cached report instantly (emergency fallback only)
- [ ] Pre-run the full demo script end-to-end — time it (target: 90 seconds)

### Afternoon — Rehearsal
- [ ] Full pitch rehearsal × 2 — presenter + demo operator together, timed
- [ ] Verify everything works on the **exact laptop** being used for presentation
- [ ] Test on presentation room WiFi — API calls need internet
- [ ] Assign Q&A roles: who answers technical questions, who handles business/market questions

### Demo Day Morning Checklist
- [ ] Laptop charged + charger packed
- [ ] `.env` file with `DASHSCOPE_API_KEY` on demo laptop
- [ ] `demo/demo_session.mp3` file ready
- [ ] Static fallback report tested and working
- [ ] Browser tab open on upload page before entering the room
- [ ] Pitch slides open on the right starting slide
- [ ] Everyone knows their role
