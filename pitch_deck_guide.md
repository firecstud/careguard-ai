# CareGuard AI — Pitch Deck Guide
### Slide-by-Slide Breakdown | 5–8 Minute Hackathon Pitch

---

## Slide 1 — Hook / Cover

### What's On The Slide
- Product name: **CareGuard AI**
- Tagline: *"Every word matters. We make sure none are missed."*
- Dark, minimal background — silhouette of therapist and patient in session

### Talking Points
- Do NOT read the tagline. Open with a scenario instead:
  > *"A patient tells their therapist 'I think everyone would be better off without me.' The therapist nods and says 'Let's talk about your sleep.' Three weeks later that patient is hospitalized — and that therapist faces a malpractice claim. Not because they were a bad clinician. Because they missed four words."*
- That story IS your hook. The slide just frames it.

### Critical / Optional / Avoid
- ✅ **Critical:** The verbal opening story — this sets the emotional stakes
- ❌ **Avoid:** Introducing the team, explaining the product, or reading the tagline on Slide 1

> [!WARNING]
> One slide, one job: make the audience feel the problem before they know the solution exists.

---

## Slide 2 — The Problem

### What's On The Slide
Three large stat blocks:
- **$4.6B** — Annual medical liability claim costs (US)
- **70%** — Of malpractice cases involve a communication or documentation failure, not a clinical error
- **0** — Existing tools that automatically audit what was said in a session

Bottom line: *"The gap between what was said and what should have been said is where liability lives."*

### Talking Points
- The key reframe: most liability isn't about *doing the wrong thing* — it's about *not saying the right thing*
- Therapists are the clearest example: they have *legally defined verbal obligations* (suicide risk assessment, Tarasoff duty to warn, mandatory reporting) that are hard to remember under emotional pressure
- Today audits happen after a lawsuit — CareGuard moves them to before

### Critical / Optional / Avoid
- ✅ **Critical:** The "communication failure, not clinical error" reframe
- ✅ **Critical:** Establish that no current solution does what you're doing
- ❌ **Avoid:** Spending more than 90 seconds here — don't over-educate on a problem judges understand

---

## Slide 3 — The Solution

### What's On The Slide
Simple horizontal flow diagram:
```
[📁 Audio File Upload]  →  [Stage 1: Transcribe + Label Speakers]  →  [Stage 2: Liability Audit]  →  [📋 Risk Report]
```
One sentence per stage beneath the diagram. Note: "Live microphone capture is supported as a stretch goal."

### Talking Points
- Keep this to 45 seconds — it's a transition slide, not the main event
- *"Stage 1 is ears. Stage 2 is judgment."*
- *"Upload a session recording, get a liability report in under 3 minutes."*
- Plant the hardware vision: *"In the future, Stage 1 becomes a standalone device — press one button, session captured, audited automatically. No phone, no laptop."*

### Critical / Optional / Avoid
- ✅ **Critical:** The flow diagram — one visual beats three paragraphs
- ✅ **Critical:** Mention the future hardware briefly — it's a differentiator
- ❌ **Avoid:** Explaining HOW it works here — that's Slide 4's job

---

## Slide 4 — How It Works (Technical)

### What's On The Slide
Two columns:

| Stage 1 — Audio Capture | Stage 2 — Audit Engine |
|---|---|
| 📁 **Primary:** Audio file upload (MP3/WAV/M4A) | 🔍 Rule-based keyword scanner on patient speech |
| 🎙️ **Stretch:** Real-time browser mic capture | 📋 Checks therapist response window for required phrases |
| 🗣️ DashScope ASR labels Therapist vs. Patient | ⚠️ Flags gaps with severity + exact patient quote |
| 📝 Transcript feeds Stage 2 | 📊 Generates corrective guidance via LLM |

Bottom note: *"The audit core is rule-based — every flag is explainable, not a black box."*

### Talking Points
- The keyword-based approach is a **feature**, not a limitation:
  > *"In a compliance context, a therapist can't contest a black-box flag. They can contest a flag that says: the patient said X, and within the next five exchanges you did not say Y. That's auditable. That stands up in a review."*
- LLM is still used — but only for generating the corrective recommendation ("what you should have said"), which benefits from natural language. The detection logic is deterministic.
- Mention: File upload works for post-session audits. Live streaming (stretch) enables real-time monitoring in the future.

### Critical / Optional / Avoid
- ✅ **Critical:** The explainability argument — healthcare compliance judges will love this
- ✅ **Critical:** Distinguishing rule-based detection from LLM-generated recommendations
- ❌ **Avoid:** Code, API names, or deep technical specs — this is a pitch not a code review

> [!WARNING]
> This is the slide most teams over-explain. One architectural insight, delivered confidently, beats a full system diagram that takes 3 minutes to walk through.

---

## Slide 5 — Live Demo

### What's On The Slide
Just: **"Live Demo"** in large text with the product logo. Optionally a QR code linking to a hosted version or backup video.

### Demo Flow (90–120 seconds)
1. Open CareGuard AI in browser — show a clean, professional upload UI
2. Drag and drop the pre-recorded `demo_session.mp3` file (2–3 minute scripted therapy dialogue)
3. Transcript appears — color-coded Therapist (blue) vs. Patient (green)
4. Click "Analyze" → Liability Report generates
5. Point to the HIGH flag: *"The patient said 'everyone would be better off without me.' The therapist talked about sleep. In a malpractice case, this silence is the liability."*
6. Show the risk score: *"87/100. This goes to the compliance officer tonight — not after the lawsuit is filed."*
7. Point to the recommendation: *"CareGuard tells the therapist exactly what they should have said."*
8. Close with: *"CareGuard AI catches this automatically — every session, every time, before a claim is ever filed."*

### Critical / Optional / Avoid
- ✅ **Critical:** The demo must work — have a pre-recorded video backup ready
- ✅ **Critical:** The emotional moment when the HIGH flag appears — let it land before speaking
- ❌ **Avoid:** Showing every feature. One clean flow beats a rushed tour of every screen
- ❌ **Avoid:** Live microphone demo unless file upload is rock solid — file upload is more reliable and repeatable

> [!CAUTION]
> Never apologize during a demo. If something breaks, pivot to backup video without comment. Practice the demo at least 10 times before the day.

---

## Slide 6 — Market Opportunity

### What's On The Slide
- 180,000+ licensed therapists in the US | 1M+ globally
- Proposed model: ~$60/therapist/month (SaaS)
- 10% US penetration → **$130M ARR**
- One line: *"Therapists are the beachhead. GPs, psychiatrists, and surgeons are the platform."*

### Talking Points
- Don't linger on numbers — one sentence on size, then pivot to the platform story
- *"We start with therapists because their liability rules are the clearest and most legally defined. But the architecture supports any specialty — you swap the checklist, not the engine."*
- This is the language of a platform company, not a single-use tool

### Critical / Optional / Avoid
- ✅ **Critical:** The platform / expandable specialty framing
- ✅ **Critical:** One concrete market number
- ❌ **Avoid:** Detailed revenue projections or funding asks — keep it high level at a hackathon

> [!WARNING]
> Market slides are filler in most hackathon pitches. Make yours punchy: one number, one insight, move on in under 60 seconds.

---

## Slide 7 — Roadmap

### What's On The Slide

| Phase 1 — Now | Phase 2 — 6 Months | Phase 3 — 12 Months |
|---|---|---|
| Therapy session auditing | Standalone hardware recorder | Real-time in-session alerts |
| File upload (post-session) | Expand to GPs + psychiatrists | EHR integration (Epic, Cerner) |
| Rule-based audit engine | Multi-language support | Jurisdiction-aware rule engine |

### Talking Points
- Phase 1 is live today — the demo proved it
- *"Upload a session recording, get a liability report in under 3 minutes. That's what we built in 5 days."*
- The hardware device is the Phase 2 product story: *"A single device with one button. Press to start, press to stop. Every session captured and audited automatically. No tech literacy required from the clinician."*
- EHR integration in Phase 3 is what turns this into infrastructure — compliance reports feed directly into clinical notes, creating a full audit trail

### Critical / Optional / Avoid
- ✅ **Critical:** Hardware device mention — tangible, imaginable, and differentiating
- ✅ **Critical:** EHR as the enterprise moat
- ❌ **Avoid:** Specific dates or funding milestones

---

## Slide 8 — Team

### What's On The Slide
- Photos, names, one-line role (Audio Pipeline × 2, Audit Engine × 2, Frontend × 1)

### Talking Points
- 30 seconds maximum
- Mention any relevant background briefly
- Close the entire pitch — not with "thank you" — with:
  > *"Every clinical session produces liability risk. Right now, that risk is invisible. CareGuard AI makes it visible — automatically, in real time, before a claim is ever filed."*
- Then pause. Then invite questions.

### Critical / Optional / Avoid
- ✅ **Critical:** The closing line — it's the last thing judges hear
- ❌ **Avoid:** Ending with "any questions?" alone — it's a weak close

> [!WARNING]
> Do not end with "Thank you." End with your closing statement, pause confidently, then open the floor. The last 10 seconds of a pitch are remembered more than the first 7 minutes.

---

## Timing Guide

| Slide | Time |
|---|---|
| 1 — Hook | 30 sec |
| 2 — Problem | 75 sec |
| 3 — Solution | 45 sec |
| 4 — How It Works | 90 sec |
| 5 — Demo | 2–3 min |
| 6 — Market | 45 sec |
| 7 — Roadmap | 30 sec |
| 8 — Team | 30 sec |
| **Total** | **~7–8 min** |

---

## Common Hackathon Pitch Mistakes

1. **Too long on the problem** — you solved it, get to the demo fast
2. **Demo breaks and team apologizes** — always have a video backup, never apologize
3. **All 5 team members present** — pick 1–2 strong speakers, others manage demo
4. **Reading slides word for word** — slides are visual backup, you are the speaker
5. **Weak ending** — never close on "any questions?" alone
6. **Over-technical Slide 4** — one insight delivered well beats a full architecture diagram

## Design Notes
- **Colors:** Deep navy background, white text, red accent for HIGH flags, green for clean sessions
- **Font:** Inter or DM Sans — clean, clinical, modern
- **Layout:** Max 3 bullet points per slide, large whitespace, one dominant visual per slide
- **Data stats:** Make the number the largest element on the slide — let it breathe
