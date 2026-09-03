# Product Requirements Document (PRD)
## CareGuard AI — Clinical Conversation Liability Auditing

**Version:** 1.0
**Date:** August 2026
**Status:** Hackathon MVP
**Authors:** CareGuard AI Team

---

## 1. Problem Statement

Healthcare organizations — clinics, therapy practices, hospitals — face significant financial and reputational risk from medical liability claims. A substantial portion of these claims do not arise from clinical errors but from **failures in communication**: a doctor who didn't warn a patient about a risk, a therapist who didn't follow up on a suicidal statement, a clinician who failed to document what the patient said.

Currently, there is no scalable way to audit what was *actually said* in a clinical session. Notes are written after the fact, are subject to human memory and bias, and rarely capture the full conversation. Liability gaps are discovered only when a lawsuit has already been filed — far too late to correct.

**CareGuard AI makes clinical conversation auditing automatic, continuous, and proactive.**

---

## 2. Target Users

### Primary Users
| User | Role | How They Use CareGuard AI |
|---|---|---|
| **Compliance Officers** | Healthcare organization | Reviews session reports, tracks risk trends across practitioners |
| **Practice Managers** | Clinic / therapy group | Monitors therapist performance and flags recurring gap patterns |
| **Risk & Legal Teams** | Hospital / insurance | Uses audit trails as evidence of due diligence |

### Secondary Users
| User | Role | How They Use CareGuard AI |
|---|---|---|
| **Therapists / Clinicians** | Individual practitioner | Reviews their own session reports for self-correction and training |
| **Clinical Supervisors** | Training programs | Reviews trainee sessions to ensure compliance with standards |

---

## 3. Goals

### Business Goals
- Reduce the number of successful liability claims against healthcare organizations
- Provide organizations with a documented audit trail of clinical conversations
- Create a scalable platform that can expand across clinical specialties

### Product Goals (Hackathon MVP)
- Successfully transcribe a therapy session audio file with correct speaker identification
- Correctly flag HIGH-severity liability gaps (suicidality, Tarasoff, mandatory reporting) in test transcripts
- Present findings in a clear, actionable report that a non-clinical compliance officer can understand

---

## 4. Non-Goals (Out of Scope for MVP)

- ❌ Real-time in-session alerts (flagging gaps *during* a live session — stretch goal, not MVP)
- ❌ HIPAA-compliant data storage or BAA agreements with vendors
- ❌ Integration with any EHR or clinical records system
- ❌ Support for specialties other than psychotherapy / counseling
- ❌ Mobile application
- ❌ Multi-language support (English only for MVP)
- ❌ Automated legal reporting or filing

> [!NOTE]
> **File upload for post-session analysis** is the primary MVP input method. This is distinct from real-time monitoring — the session has already ended, and the audio is uploaded for retrospective auditing. Live microphone streaming is implemented as a stretch goal but is not required for the demo.

---

## 5. User Stories

### Stage 1 — Transcription
| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-01 | Compliance officer | Upload an audio file of a therapy session (MP3/WAV/M4A) | I can get a readable, speaker-labeled transcript without manual transcription |
| US-01b | Compliance officer | Optionally capture a live session via microphone | I can transcribe sessions as they happen (stretch goal) |
| US-02 | Compliance officer | See the transcript labeled by speaker | I can clearly follow who said what |
| US-03 | System admin | Upload MP3, WAV, or M4A files | I'm not restricted to one audio format |

### Stage 2 — Liability Analysis
| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-04 | Compliance officer | See a list of liability gaps from the session | I know exactly what the therapist missed |
| US-05 | Compliance officer | See the severity of each flag (High/Medium/Low) | I can prioritize which sessions need immediate follow-up |
| US-06 | Compliance officer | See the exact patient quote that triggered each flag | I understand the context of the gap |
| US-07 | Compliance officer | See what the therapist *should* have said | I can use this for coaching and corrective action |
| US-08 | Practice manager | See an overall risk score per session | I can quickly triage which sessions are most concerning |
| US-09 | Therapist | Review my own session report | I can identify areas for self-improvement |

---

## 6. Functional Requirements

### Stage 1 — Audio Transcription & Speaker Diarization

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | System shall accept audio files in MP3, WAV, and M4A formats | Must Have |
| FR-02 | System shall transcribe audio to text using Alibaba DashScope ASR | Must Have |
| FR-03 | System shall perform speaker diarization to label each utterance as Therapist or Patient | Must Have |
| FR-04 | System shall include timestamps for each utterance in the transcript | Must Have |
| FR-05 | System shall return transcript in a structured JSON format | Must Have |
| FR-06 | System shall handle audio files up to 60 minutes in length | Should Have |
| FR-07 | System shall indicate confidence level of speaker diarization | Nice to Have |

> [!NOTE]
> **Architecture:** File-based transcription (DashScope `paraformer-v2` file API) is the primary path for the MVP because it provides reliable speaker diarization. Live streaming via WebSocket (DashScope `paraformer-realtime-v2`) is implemented as a stretch goal but may not support diarization — in that case, a first-to-speak heuristic is used as fallback.

### Stage 2 — Liability Gap Analysis

| ID | Requirement | Priority |
|---|---|---|
| FR-08 | System shall extract all patient-reported symptoms and disclosures from the transcript | Must Have |
| FR-09 | System shall extract all therapist clinical responses and actions from the transcript | Must Have |
| FR-10 | System shall check for suicidality assessment gaps when patient expresses ideation | Must Have |
| FR-11 | System shall check for duty-to-warn gaps when patient threatens an identifiable person | Must Have |
| FR-12 | System shall check for mandatory reporting gaps when patient discloses abuse | Must Have |
| FR-13 | System shall check for informed consent gaps in intake or new-procedure contexts | Should Have |
| FR-14 | System shall check for crisis resource provision gaps | Should Have |
| FR-15 | System shall assign severity (HIGH / MEDIUM / LOW) to each flag | Must Have |
| FR-16 | System shall provide the exact patient quote that triggered each flag | Must Have |
| FR-17 | System shall provide a specific example of what the therapist should have said | Must Have |
| FR-18 | System shall calculate an overall session risk score (0–100) | Should Have |
| FR-19 | System shall return analysis results in structured JSON | Must Have |

### Frontend / UI

| ID | Requirement | Priority |
|---|---|---|
| FR-20 | UI shall allow drag-and-drop audio file upload | Must Have |
| FR-21 | UI shall display the transcript with color-coded speaker labels | Must Have |
| FR-22 | UI shall display the liability report with flags, severities, quotes, and recommendations | Must Have |
| FR-23 | UI shall show loading/progress state during transcription and analysis | Must Have |
| FR-24 | UI shall allow clicking a flag to highlight the relevant line in the transcript | Should Have |
| FR-25 | UI shall display an overall risk score with a visual gauge | Should Have |

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Transcription of a 10-minute audio file should complete within 3 minutes |
| **Accuracy** | HIGH-severity gaps (suicidality, Tarasoff, mandatory reporting) must not produce false negatives on test scenarios |
| **Usability** | A non-technical compliance officer should be able to use the system without training |
| **Reliability** | System must handle audio files with background noise and natural pauses without crashing |
| **Scalability** | Architecture must support adding new clinical specialty checklists without rewriting core components |

---

## 8. Success Metrics (Hackathon Demo)

| Metric | Target |
|---|---|
| End-to-end pipeline works (upload → report) | ✅ Demonstrated live |
| Suicidality flag fires correctly on test transcript | ✅ Verified in demo |
| False positive rate on clean session (Scenario D) | 0 HIGH flags |
| Judge comprehension of report without explanation | Compliance officer role-play test |
| Judges can articulate the business value in their own words | Qualitative |

---

## 9. Assumptions & Constraints

### Assumptions
- Audio recordings are made with patient consent (legal/ethical requirement in production)
- Sessions are conducted in English
- There are two speakers per session (one therapist, one patient)
- The hackathon environment provides access to Alibaba DashScope API with sufficient quota

### Constraints
- **No PHI storage:** For the hackathon, all demo audio must use synthetic or volunteer recordings — no real patient data
- **API dependency:** Both ASR and LLM functionality depend on DashScope availability and latency
- **Checklist scope:** The MVP checklist covers therapy-specific obligations only; other specialties require separate checklists

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DashScope API quota limits during demo | Medium | High | Pre-run demo and cache results; have static fallback |
| Speaker diarization misidentifies speakers | Medium | Medium | Add manual speaker-swap correction in UI |
| Streaming ASR does not support speaker diarization | High | Medium | Use file-based transcription as primary path; streaming falls back to first-to-speak heuristic |
| LLM produces hallucinated flags | Low-Medium | High | Validate all output against known test cases before demo; tune prompts |
| Audio quality of demo recording is poor | Low | High | Record demo audio in a controlled environment; test at least 24 hours before presentation |
| Stage 1 delays block Stage 2 | Medium | Medium | Stage 2 begins with generated transcripts; integration only on Day 4 |

---

## 11. Open Questions

> [!NOTE]
> These don't need to be resolved for the hackathon but should be addressed in a post-hackathon pitch or production roadmap.

1. **Jurisdiction:** Therapy liability rules (especially Tarasoff and mandatory reporting) vary significantly by country and state. How will the system handle jurisdiction-specific rules?
2. **Consent workflow:** How will the system verify that patient recording consent was obtained before a file is processed?
3. **HIPAA compliance:** Production deployment requires HIPAA-compliant infrastructure, BAAs with all vendors (including Alibaba), and data anonymization. What is the path to compliance?
4. **Appeals / Disputes:** If a therapist believes a flag is incorrect, what is the process for contesting it?
5. **Integration:** Which EHR systems are the highest-priority integration targets for the first paying customers?
