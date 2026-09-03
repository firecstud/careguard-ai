# CareGuard AI — Implementation Plan
### Therapy Session Liability Auditing | 5-Day Hackathon Build

---

## What We're Building

A two-stage AI pipeline that protects healthcare organizations from liability claims by automatically auditing clinical conversations.

**Stage 1 — Transcription:** Takes a recorded therapy session (uploaded as an audio file or captured live via microphone) and produces a structured, speaker-labeled transcript (Therapist vs. Patient). For the hackathon demo, **file upload is the primary path** — DashScope's file-based transcription has more reliable speaker diarization than real-time streaming. Live streaming via WebSocket is supported as a stretch goal.

**Stage 2 — Liability Analysis:** Takes that transcript and flags every place the therapist *should have* said something they didn't — based on what the patient disclosed, cross-referenced against a therapy-specific liability checklist grounded in real clinical and legal standards.

---

## Why Therapy Sessions First

### The Strategic Rationale

CareGuard AI is designed to eventually cover all clinical specialties — general practitioners, surgeons, psychiatrists, and more. However, for this hackathon build we are deliberately scoping to **psychotherapy and counseling sessions**. This is not a limitation — it is a deliberate strategic choice, and here's why:

### 1. Therapy Has the Clearest, Most Legally Defined Liability Rules
In most clinical specialties, liability guidelines are broad and context-dependent. But in therapy, there are a handful of *extremely specific, legally established* duties that a therapist must fulfill when certain things are said. These are not soft recommendations — they are legal obligations with case law and licensing board standards behind them:

- **The Tarasoff Duty to Warn** (from *Tarasoff v. Regents of UC Berkeley*, 1976): If a patient makes a credible threat against an identifiable person, the therapist has a legal obligation to warn that person and/or law enforcement. This is one of the most well-known liability triggers in all of mental health law.
- **Mandatory Reporting Laws**: Therapists are mandated reporters. If a patient discloses abuse of a child, elder, or vulnerable adult, the therapist is *legally required* to report it — regardless of the therapeutic relationship or patient confidentiality.
- **Suicide Risk Assessment Protocol**: When a patient expresses suicidal ideation, there is a recognized standard of care that requires a formal risk assessment (asking about ideation, plan, means, intent, and timeline). Simply acknowledging the statement and moving on is a liability failure.
- **Informed Consent Requirements**: A therapist must explain the limits of confidentiality, what triggers a mandatory report, and how to reach crisis services — particularly at intake and at the start of sensitive topics.

Because these rules are well-defined and unambiguous, we can build a **precise, reliable checklist** that the LLM checks against. This means fewer false positives, cleaner output, and a more compelling demo.

### 2. Therapy Sessions Are Conversational and Structured
A therapy session follows a predictable conversational pattern — therapist asks open-ended questions, patient responds with disclosures, therapist responds clinically. This makes speaker diarization more accurate (two speakers, clear turn-taking) and makes the LLM's job of identifying disclosure vs. response cleaner than, say, a fast-paced surgical consultation with multiple staff members.

### 3. The Stakes Are High and Relatable
Judges and audiences immediately understand why a therapist missing a patient's suicidal statement is dangerous. The *human stakes* of the problem are obvious without needing clinical background knowledge. This makes for a powerful demo moment.

### 4. It's a Scalable Proof of Concept
By building a clean, well-structured system for one specialty first, we prove the architecture works. Adding a new specialty later is a matter of swapping in a different liability checklist — the transcription engine, the LLM pipeline, and the frontend are all reusable. We pitch this to judges as a **platform**, not a single-use tool.

---

## Team Structure (5 People, 3 Sub-Teams)

| Sub-Team | People | Responsibility |
|---|---|---|
| **Stage 1 — Audio Pipeline** | 2 | DashScope ASR + diarization, transcript formatting, backend endpoints |
| **Stage 2 — Analysis Engine** | 2 | Qwen LLM prompting, liability checklist logic, report generation |
| **Frontend** | 1 | Upload UI, transcript viewer, liability report display, risk score |

> [!IMPORTANT]
> Stage 2 begins **Day 1** using pre-generated synthetic transcripts. The two backend teams are decoupled by a shared JSON contract and integrate on **Day 4**. This protects the timeline from audio pipeline delays blocking the analysis work.

---

## Full Tech Stack (Alibaba AI)

| Layer | Tool | Purpose |
|---|---|---|
| **File Upload (primary)** | FastAPI `UploadFile` + DashScope File ASR | Accepts MP3/WAV/M4A upload, transcribes with reliable diarization |
| **Live Audio (stretch)** | Browser Web Audio API + WebSocket | Captures live microphone audio and streams to server |
| **Speech-to-Text + Diarization** | DashScope ASR (file-based + real-time) | Transcribes audio and labels speakers — file API for upload, WebSocket for live |
| **LLM (limited use)** | `qwen-max` via DashScope | Generates corrective recommendation text + semantic second-pass detection |
| **Audit Engine** | Python — rule-based keyword matching | Core gap detection logic — deterministic, explainable, no AI needed |
| **Backend** | Python + FastAPI + WebSocket | Orchestrates file upload, audio stream, transcript accumulation, audit pipeline |
| **Frontend** | React (Vite) | File upload / session control (start/stop), live transcript, report display, risk score |

### Stage 1 — Audio Architecture

**Primary path — File Upload (recommended for demo):**
```
[Audio File Upload] ──POST /transcribe──► [FastAPI Server] ──► [DashScope File ASR]
                                                  │                      │
                                                  │◄── speaker-labeled ──┘
                                                  │     transcript
                                                  ▼
                                       [Stage 2 Audit Engine]
```

**Stretch goal — Live Streaming:**
```
[Browser Mic] ──WebSocket──► [FastAPI Server] ──► [DashScope Real-Time ASR]
                                    │                         │
                                    │◄────── speaker-labeled ─┘
                                    │        transcript chunks
                                    ▼
                          [Transcript Accumulator]
                                    │
                          [Stage 2 Audit Engine]
```

> [!WARNING]
> **Day 1 spike (blocking):** Validate that DashScope's real-time ASR returns `speaker_id` in streaming mode. If it does not (common — diarization is primarily a file-based feature), use file upload as the primary path and fall back to an alternating-turn heuristic for live streaming. The file-based API has reliable diarization and is the recommended demo path.

- The browser captures microphone audio in chunks using the **Web Audio API**
- Chunks are streamed to the FastAPI backend via **WebSocket**
- The backend pipes audio to **DashScope's real-time ASR** (also WebSocket-based)
- DashScope returns transcript segments with `speaker_id` in near real-time
- The server maps `speaker_id` → Therapist / Patient and accumulates the transcript
- Stage 2 can process utterances as they arrive (streaming audit) or at session end

### Future Hardware Vision (Phase 2)
The browser app is replaced by a **standalone recorder device** (e.g., Raspberry Pi + microphone):
- Single on/off button — press to start session, press to end
- Streams audio to the same server endpoint over WiFi
- No phone, no laptop required in the clinical room
- The server-side pipeline is identical — only the audio source changes
- Single API key covers both ASR and Qwen LLM calls

---

## Shared Data Contract (JSON Handoff Between Stages)

Both sub-teams build against this spec from Day 1. Stage 1 produces it; Stage 2 consumes it.

```json
{
  "session_id": "abc123",
  "audio_file": "session_01.mp3",
  "utterances": [
    {
      "speaker": "Therapist",
      "start_time": "00:00:04",
      "end_time": "00:00:09",
      "text": "What brings you in today? How have you been feeling?"
    },
    {
      "speaker": "Patient",
      "start_time": "00:00:10",
      "end_time": "00:00:22",
      "text": "I've been really low lately. I haven't been sleeping. Sometimes I think everyone would be better off without me."
    },
    {
      "speaker": "Therapist",
      "start_time": "00:00:23",
      "end_time": "00:00:28",
      "text": "I'm sorry to hear that. Let's talk about your sleep schedule."
    }
  ]
}
```

---

## Stage 2: Therapy Liability Checklist

When the patient says X, the therapist *must* respond with Y. Below is the full checklist the LLM checks against.

### 🔴 Category 1 — Suicidality & Self-Harm (CRITICAL)
| Patient Signal | Required Therapist Response |
|---|---|
| Expresses hopelessness, "everyone better off without me," passive death wish | Must conduct formal **suicide risk assessment** — ask about ideation, plan, means, intent, timeline |
| Expresses active plan or intent to self-harm | Must discuss **safety plan**, emergency contacts, and assess hospitalization need |
| Reports recent self-harm behavior | Must assess lethality, document, discuss safety planning |

### 🔴 Category 2 — Duty to Warn / Tarasoff (CRITICAL)
| Patient Signal | Required Therapist Response |
|---|---|
| Makes specific threat toward an identifiable person | Must warn the potential victim and/or notify law enforcement |
| Expresses violent ideation | Must assess credibility, seriousness, and document reasoning |

### 🔴 Category 3 — Mandatory Reporting (CRITICAL)
| Patient Signal | Required Therapist Response |
|---|---|
| Discloses abuse of a child, elder, or vulnerable adult | Must acknowledge mandatory reporting obligation on record |
| Minor patient discloses self-harm | Parental notification obligation must be addressed |

### 🟡 Category 4 — Informed Consent (IMPORTANT)
| When | Required Therapist Action |
|---|---|
| First session / intake | Must explain confidentiality, its legal limits, and emergency procedures |
| Introducing a new treatment modality (e.g., EMDR, exposure therapy) | Must explain the approach and obtain verbal buy-in |
| Any telehealth session | Must confirm patient is in a private, safe location |

### 🟡 Category 5 — Crisis Resource Provision (IMPORTANT)
| Patient Signal | Required Therapist Response |
|---|---|
| Any expression of suicidality or severe distress | Must provide crisis hotline (988 Lifeline or local equivalent) |
| Safety plan discussion | Must confirm patient has an emergency contact person |

### 🟡 Category 6 — Treatment Plan & Documentation (MODERATE)
| When | Required Therapist Action |
|---|---|
| Patient reports a new symptom or significant life change | Therapist must acknowledge it and incorporate it into discussion |
| Patient mentions a medication change | Must acknowledge and flag for documentation |
| End of session | Should confirm next appointment and any between-session tasks |

---

## Stage 2: Audit Engine — Keyword-Based Detection

### Design Philosophy
The core audit logic uses **rule-based keyword and phrase matching**, not LLM inference. This is a deliberate choice:
- **Explainability:** Every flag can be traced to a specific patient phrase and a specific missing therapist response — this holds up in a compliance review
- **Reliability:** No hallucinations, no false positives from LLM reasoning errors
- **Speed:** No API latency for the detection step — runs instantly on each new utterance
- **Auditability:** The ruleset is a transparent Python dictionary — any clinician or legal team can review and verify the logic

The LLM (`qwen-max`) is used **only** to generate the corrective recommendation text — the "what the therapist should have said" field — where natural language quality matters.

---

### Step 1 — Patient Keyword Detection

For each patient utterance, scan for trigger phrases grouped by liability category:

```python
TRIGGER_PHRASES = {
    "suicidality": [
        "better off without me", "want to die", "end it all",
        "not worth living", "hurt myself", "kill myself",
        "no reason to live", "tired of living", "can't go on",
        "wish I was dead", "thinking about suicide",
        "what's the point", "don't want to be here",
        "everyone would be better off", "better off gone",
        "don't want to wake up", "just want it to stop",
        "thinking about it", "make it all stop"
    ],
    "duty_to_warn": [
        "going to hurt", "going to kill", "want to kill",
        "make them pay", "they deserve to die", "I'll hurt",
        "I'll make them", "going to get them", "they won't see it coming",
        "I know where they live", "they're going to regret"
    ],
    "mandatory_reporting": [
        "hitting me", "abusing me", "hurt my child",
        "someone is abusing", "they beat me", "being abused",
        "my kid is being hurt", "elder abuse",
        "my parent hits me", "someone touched me",
        "they don't feed me", "locked in my room"
    ],
    "informed_consent": [
        # Not triggered by patient phrases.
        # Detected via session-length heuristic: if this is a short session
        # (< 5 exchanges) and the therapist never mentions "confidential",
        # "limits", or "exceptions" → MEDIUM flag for missing consent.
    ],
    "crisis_resources": [
        # Not a standalone trigger. This is a SUB-CHECK of suicidality.
        # When a suicidality flag fires, also check that the therapist
        # provided crisis resources (988, hotline, emergency contact).
        # If they did assess suicidality but skipped resources → MEDIUM flag.
    ]
}
```

Matching strategy:
- **Exact phrase match** as the primary method (fast, zero false positives on direct phrases)
- **Fuzzy / stemmed match** as secondary (catches paraphrasing like "I'd be better off gone")
- When a phrase matches → store: `{ category, severity, patient_quote, utterance_index }`

---

### Step 2 — Therapist Response Window Check

For each flagged patient utterance, scan the **next N therapist utterances** (default N=5) for required response phrases:

```python
REQUIRED_RESPONSES = {
    "suicidality": [
        "are you thinking about", "do you have a plan", "have you thought about how",
        "safety plan", "988", "crisis line", "thoughts of suicide",
        "hurting yourself", "risk assessment"
    ],
    "duty_to_warn": [
        "I have to take that seriously", "I'm obligated", "I may need to",
        "contact authorities", "warn", "law enforcement"
    ],
    "mandatory_reporting": [
        "I'm required to report", "mandated reporter", "I need to make a report",
        "child protective", "adult protective"
    ],
    "crisis_resources": [
        "988", "crisis line", "hotline", "emergency contact",
        "someone you can call", "crisis center"
    ]
}
```

If NONE of the required response phrases appear in the response window → **flag generated**.

---

### Step 3 — LLM Recommendation Generation (qwen-max)

Only called when a gap is confirmed. Generates the human-readable "what should have been said" field:

```
A therapy patient said: "{patient_quote}"
The therapist did not conduct a {category} response.

Write one example of what the therapist should have said at that moment,
in a natural, clinical tone. Keep it to 2–3 sentences.
```

One call per flag, not per transcript. Run calls concurrently via `asyncio.gather` to avoid serial latency (5 flags × 3s each = 15s serial vs ~3s parallel).

**Static fallback:** If the LLM call fails (timeout, quota, content filter), use a pre-written fallback recommendation per category. The fallback text is stored in `llm_client.py` — see the `FALLBACK_RECOMMENDATIONS` dict in `api_quickstart.md`.

### Step 4 — Semantic Second Pass (qwen-max, optional)

The rule-based scanner can miss paraphrases and produce false positives on the response window check (a therapist may conduct a good risk assessment without using any of our exact 9 phrases). As an optional enhancement:

After the keyword scanner runs, send **unmatched patient utterances** to qwen-max with a prompt asking whether the utterance contains a liability-relevant disclosure the keyword list missed. Label any LLM-found items with `detection_method: "semantic_match"` to distinguish them from rule-based detections.

This step costs one additional LLM call per session (not per utterance — batch the unmatched utterances into a single prompt). It is optional for the hackathon but makes the system more robust to natural speech variation.

---

### Stage 2 Output — Liability Report

```json
{
  "session_id": "abc123",
  "overall_risk_score": 87,
  "risk_level": "HIGH",
  "flags": [
    {
      "category": "Suicidality Assessment",
      "severity": "HIGH",
      "patient_quote": "Sometimes I think everyone would be better off without me.",
      "detection_method": "keyword_match: 'better off without me'",
      "what_was_missed": "No suicide risk assessment phrases detected in next 5 therapist utterances.",
      "what_should_have_been_said": "When you say that, I want to make sure I understand — are you having thoughts of ending your life? I'd like us to talk through that together and make sure you're safe.",
      "utterance_index": 1,
      "timestamp": "00:00:10"
    }
  ]
}
```

Note the `detection_method` field — this makes every flag fully explainable and contestable.

---

## 5-Day Build Plan

### Day 1 — Setup & Foundation
**All Teams:**
- Clone repo, configure DashScope API keys
- Lock the JSON contract — confirm `"utterances"` as the array key name across all files. Both teams sign off on the schema in `shared/transcript_schema.py` before writing any code
- Set up FastAPI skeleton with `/health`, `/analyze`, and `/transcribe` routes

**Stage 1 Team:**
- **⚡ FIRST (blocking): Diarization validation spike** — run one WAV file through DashScope's real-time ASR and print the raw `words` array. Confirm whether `speaker_id` appears. If it does not (likely), switch primary path to file-based transcription (`paraformer-v2` file API). This is the single most important validation on Day 1 — do not proceed to other audio work until it's confirmed
- Build the file upload endpoint (`POST /transcribe`) and file-based transcription client — this is the **primary demo path** and has reliable diarization
- If time permits: set up browser-side Web Audio API capture for live streaming (stretch goal)
- Output: uploading an audio file returns a speaker-labeled transcript

**Stage 2 Team:**
- Build the `TRIGGER_PHRASES` and `REQUIRED_RESPONSES` dictionaries for all 6 liability categories
- Generate 5 synthetic test transcripts (Scenarios A–E) using Qwen
- Write the keyword scanner — run it against all test transcripts and verify HIGH flags fire on A, B, C and not on D

**Frontend:**
- Set up React/Vite project
- Build file upload UI with drag-and-drop (primary demo path)
- Build session control UI: Start Session button, Stop Session button, live status indicator (stretch)
- Build transcript display with color-coded Therapist (blue) / Patient (green) utterances

**End-of-day bonus: throwaway E2E skeleton** — wire file upload → hardcoded utterance → hardcoded flag → UI display. This makes Day 4 integration incremental instead of a big-bang.

---

### Day 2 — Core Features
**Stage 1 Team:**
- Implement therapist/patient speaker mapping from file-based diarization output
- Add speaker-swap correction endpoint in case labels are reversed
- If real-time ASR has `speaker_id`: implement browser-side streaming with the `call_soon_threadsafe` + queue pattern (see `api_quickstart.md` section 4)
- Test file upload → transcription → speaker labeling end-to-end

**Stage 2 Team:**
- Implement the response window checker (scan next N therapist utterances for required phrases)
- Add fuzzy matching as secondary layer via `rapidfuzz` using `fuzz.partial_ratio` (not `fuzz.ratio` — short phrases against long utterances need partial matching)
- Wire in the Qwen LLM call for recommendation generation with try/except and static fallback per category
- Build `generate_recommendations_batch` for concurrent LLM calls via `asyncio.gather`
- Validate full pipeline on all 5 test scenarios — tune response window size N

**Frontend:**
- Build Liability Report display: flag cards with severity badges, patient quote, what_was_missed, recommendation
- Add loading/processing state animations
- Make the UI polished — dark theme, clean typography

---

### Day 3 — Depth & Reliability
**Stage 1 Team:**
- Handle file upload edge cases: large files (>60 min), unsupported formats, corrupt audio
- Add session metadata to transcript output (session_id, start_time, end_time, duration_seconds, audio_file)
- Add error recovery: if DashScope file API fails, return a clear error to the frontend
- If live streaming is working: handle silence gaps, session end cleanup, DashScope reconnection
- Test with 3 different audio files of varying quality

**Stage 2 Team:**
- Expand trigger phrase lists with paraphrasing variants based on test failures
- Add `detection_method` field to all flags: e.g. `"keyword_match: 'better off without me'"` or `"fuzzy_match: 'better off gone' (87%)"`
- Implement risk score calculation using a saturating curve:
  ```python
  import math
  raw_score = HIGH_count * 40 + MEDIUM_count * 20 + LOW_count * 10
  risk_score = min(100, int(100 * (1 - math.exp(-raw_score / 50))))
  ```
  This produces ~87 for the demo scenario (1 HIGH + 1 MEDIUM) and differentiates severity better than a linear clamp (where 3 HIGHs max out at 100)
- Implement hybrid detection: send unmatched patient utterances to qwen-max in a single batch prompt asking if any contain liability-relevant disclosures the keyword list missed. Label matches as `detection_method: "semantic_match"`. Optional but makes the system more robust
- Validate **zero false positives** on Scenario D — tune thresholds if needed
- Add informed consent detection: short session (<5 exchanges) + therapist never says "confidential" → MEDIUM flag

**Frontend:**
- Add risk score gauge (CSS arc or `react-circular-progressbar`)
- Make flag cards clickable — clicking a flag highlights the triggering line in `TranscriptView`
- Severity colors: HIGH = red border, MEDIUM = amber, LOW = grey
- Add speaker swap button in UI (calls `POST /session/{id}/swap-speakers`)
- Polish: dark theme (`#0f172a` bg), Inter font, consistent spacing
- Layout works on 1920x1080 (demo screen size)
- **End-of-day check:** Show the UI to someone unfamiliar — can they read the report without help?

---

### Day 4 — Integration Day
**Goal:** Full end-to-end pipeline running with file upload.

**Morning — Backend Integration (Stage 1 + Stage 2):**
- Stage 1 merges `feature/stage1-audio` → `develop`
- Stage 2 merges `feature/stage2-audit` → `develop`
- Integration test: upload audio file → Stage 1 transcription → Stage 2 `/analyze` → report JSON
- Fix any JSON schema mismatches between Stage 1 output and Stage 2 expected input

**Afternoon — Frontend Joins:**
- Frontend merges `feature/frontend` → `develop`
- Wire frontend file upload to live Stage 1 backend
- Wire frontend report display to live Stage 2 `/analyze` response
- **Full E2E test #1:** Upload Scenario A audio → HIGH suicidality flag appears in UI
- **Full E2E test #2:** Upload clean session (Scenario D) → no HIGH flags
- **Full E2E test #3:** Upload the planned demo audio → confirms it produces the right report
- Fix integration bugs (allocate 4–6 hours, this is expected)
- Merge `develop` → `main` once E2E is confirmed working

**Stretch (if time permits):**
- Wire live streaming WebSocket path end-to-end
- Test browser mic → live transcript → real-time flags

---

### Day 5 — Polish & Demo Prep
**Goal:** A demo you can run confidently in front of judges with zero panic.

**Morning — Hardening:**
- Fix remaining bugs from Day 4
- **Record the demo audio:** Record a 2–3 minute scripted therapy session (therapist misses suicidal statement) — save as `demo/demo_session.mp3`
- Pre-run the full demo with the recorded audio and cache the result as static fallback: `demo/cached_report.json`
- Add a hidden "demo mode" button in frontend — loads cached report instantly (emergency fallback only)
- Pre-run the full demo script end-to-end — time it (target: 90 seconds)

**Afternoon — Rehearsal:**
- Full pitch rehearsal × 2 — presenter + demo operator together, timed
- Verify everything works on the **exact laptop** being used for presentation
- Test on presentation room WiFi — API calls need internet
- Assign Q&A roles: who answers technical questions, who handles business/market questions

**Demo Day Morning Checklist:**
- [ ] Laptop charged + charger packed
- [ ] `.env` file with `DASHSCOPE_API_KEY` on demo laptop
- [ ] `demo/demo_session.mp3` file ready
- [ ] Static fallback report tested and working
- [ ] Browser tab open on upload page before entering the room
- [ ] Pitch slides open on the right starting slide
- [ ] Everyone knows their role

#### Demo Script (File Upload Path)
1. Open CareGuard AI in browser — show clean, professional upload UI
2. Drag and drop the pre-recorded `demo_session.mp3` file
3. Show transcript appearing with color-coded Therapist (blue) / Patient (green) labels
4. Analysis completes → Liability Report loads
5. Point to the HIGH flag: *"The patient said 'everyone would be better off without me.' The therapist talked about sleep. In a malpractice case, this silence is the liability."*
6. Show the risk score: *"87/100. This goes to the compliance officer tonight — not after the lawsuit is filed."*
7. *"CareGuard AI catches this automatically — every session, every time, before a claim is ever filed."*
8. Show the roadmap: therapists → GPs → surgeons — one platform, swappable checklists

**Optional encore (if time and confidence allow):**
- Live microphone demo — record 30 seconds live and show real-time transcript
- Only attempt this if the file upload demo is rock solid

---

## Future Roadmap (Post-Hackathon Pitch)

| Phase | Feature |
|---|---|
| Phase 2 | Standalone hardware recorder (Raspberry Pi + mic) — one button, no laptop needed |
| Phase 3 | Add GP / physician checklist (informed consent for procedures, referral obligations, medication warnings) |
| Phase 4 | Add psychiatrist checklist (medication management, capacity assessment) |
| Phase 5 | Real-time in-session alerts via WebSocket streaming ASR |
| Phase 6 | EHR integration (Epic, Cerner) — push flags directly to clinical notes |
| Phase 7 | Multi-language support |
| Phase 8 | Jurisdiction-aware rules engine (laws differ by country/state) |
| Phase 9 | Anonymization pipeline for HIPAA/GDPR compliance |
