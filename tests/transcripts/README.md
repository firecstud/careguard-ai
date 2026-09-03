# CareGuard AI — Test Transcript Index

This directory contains **20 purpose-built test transcripts** organized by the capability they are designed to verify.

---

## 🔴 TRUE POSITIVES — Must Flag

Transcripts that contain real liability disclosures which the system **must** detect.

| File | Category Tested | Expected Flag(s) | Notes |
|---|---|---|---|
| `suicidality_explicit_no_response.json` | Suicidality | `suicidality` | Direct "kill myself", "want to die", discloses plan — therapist completely ignores |
| `suicidality_passive_ideation.json` | Suicidality | `suicidality` | "everyone better off without me", "wish I wasn't here", "tired of living" — subtle passive ideation |
| `suicidality_escalating_across_session.json` | Suicidality | `suicidality` | Escalates from existential emptiness → passive ideation → researching methods across session |
| `suicidality_with_self_harm_history.json` | Suicidality | `suicidality` | Active cutting + escalating ideation disclosed simultaneously |
| `duty_to_warn_explicit_named_target.json` | Duty to Warn | `duty_to_warn` | Named target (landlord), knowledge of location, stated means (baseball bat), stalking behavior |
| `mandatory_reporting_child_abuse.json` | Mandatory Reporting | `mandatory_reporting` | Physical abuse of patient and minor child, explicit bruise description |
| `mandatory_reporting_elder_abuse.json` | Mandatory Reporting | `mandatory_reporting` | Physical abuse and neglect of elderly parent in care facility |
| `mandatory_reporting_sexual_abuse_minor.json` | Mandatory Reporting | `mandatory_reporting` | Long-term sexual abuse starting in childhood, patient directly asks about reporting |
| `treatment_plan_medication_change_no_followup.json` | Treatment Plan | `treatment_plan` | Stopped medication unilaterally + started new supplements + new panic attack symptoms |
| `multi_flag_suicidality_and_duty_to_warn.json` | Multi-category | `suicidality`, `duty_to_warn` | Patient discloses stalking behavior + suicidal ideation in same session |
| `multi_flag_all_categories.json` | Multi-category | `suicidality`, `mandatory_reporting`, `treatment_plan` | Maximum stress test: elder abuse report + suicidal ideation + stopped medication |

---

## 🟢 TRUE NEGATIVES — Must NOT Flag

Transcripts that contain **no genuine liability concerns** and should produce zero flags.

| File | Why It Should Pass | Risk Expected |
|---|---|---|
| `clean_normal_session_no_flags.json` | Purely positive session — relationship goals, yoga, healthy progress | MINIMAL |
| `clean_violent_idioms_no_flags.json` | Loaded with common idioms: "kill it", "back is killing me", "dying to", "make them pay", "kill the boss", "die of embarrassment" | MINIMAL |
| `clean_grief_without_suicidal_ideation.json` | Anniversary grief — sad but explicitly non-dangerous, healthy coping | MINIMAL |
| `clean_relationship_breakup_no_ideation.json` | Painful breakup — distress without any suicidality markers, good support system | MINIMAL |
| `clean_work_stress_venting_no_flags.json` | Career frustration with professional threat language ("regret losing me") — career context not violence | MINIMAL |

---

## ✅ CORRECT THERAPIST RESPONSES — Should NOT Flag After Good Response

Transcripts where the therapist handles disclosures correctly. The system should recognize the response and **not** produce a flag.

| File | Category Tested | Correct Response Includes |
|---|---|---|
| `suicidality_therapist_responds_correctly.json` | Suicidality | Direct risk assessment, safety plan, 988 crisis line, follow-up scheduling |
| `duty_to_warn_therapist_responds_correctly.json` | Duty to Warn | Acknowledges obligation, challenges threat, documents, explains Tarasoff |
| `mandatory_reporting_therapist_responds_correctly.json` | Mandatory Reporting | Identifies mandated reporter role, explains CPS reporting process |
| `treatment_plan_therapist_follows_up_correctly.json` | Treatment Plan | Documents medication change, coordinates with prescriber, schedules follow-up |

---

## ⚠️ EDGE CASES — Tests System Precision

Transcripts that probe the boundary conditions and potential failure modes.

| File | What It Tests | Expected Behavior |
|---|---|---|
| `edge_fuzzy_match_paraphrased_suicidality.json` | **Fuzzy matching** — phrases written with typos/misspellings ("thorts about killing myslef", "hurtin mysef") | Should still flag via `rapidfuzz.partial_ratio` |
| `edge_therapist_partial_inadequate_response.json` | **Inadequate response** — therapist says the word "ideation" but completely fails to do a real risk assessment despite patient disclosing plan + date + means | This exposes a known weakness: one keyword match clears the flag |
| `edge_ambiguous_borderline_phrases.json` | **Ambiguous language** — uses "what's the point", "just want it to stop", "disappeared", "nothing matters" but patient explicitly contextualizes as career frustration and denies self-harm | Tests specificity; ideally NOT flagged, but may produce low-confidence flags |
| `edge_cultural_indirect_self_harm_expression.json` | **Semantic-only detection** — no keyword triggers, but describes passive self-harm (dangerous driving, alcohol poisoning intent, stopping medication, giving away money). Exclusively tests the LLM semantic pass. | Should be caught by semantic second pass only |
| `edge_high_distress_no_safety_concern.json` | **High distress, no danger** — overwhelmed patient, uses "hopeless" and "escape" language but explicitly denies self-harm and maintains future orientation | Should NOT be flagged; tests over-flagging of distress language |
| `edge_third_party_violence_not_tarasoff.json` | **Third-party violence attribution** — violent threat language appears, but it's a coworker's ex threatening the coworker, not the patient making threats | Should NOT trigger duty-to-warn; tests speaker attribution |
| `suicidality_subtle_semantic_only.json` | **Semantic-only suicidality** — no direct keyword phrases, but patient describes funeral fantasies, giving away possessions, writing goodbye letters, and sudden calm | Should be caught by LLM semantic pass exclusively |

---

## Running All Transcripts

```bash
# Offline (no API key needed) — runs original 5 scenarios:
cd /home/saad/Documents/careguard\ ai
python tests/run_tests.py

# To test any specific transcript against the live server:
# 1. Start the server:  python backend/main.py
# 2. POST via curl:
curl -s -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d @tests/transcripts/suicidality_explicit_no_response.json | python -m json.tool

# Or drag-and-drop any .json file into the web UI at http://localhost:8000
```

---

## Coverage Matrix

| Category | True Positive | True Negative | Correct Response | Edge Cases |
|---|---|---|---|---|
| Suicidality (Explicit) | ✅ | ✅ | ✅ | ✅ Fuzzy match |
| Suicidality (Passive) | ✅ | ✅ | — | ✅ Semantic only |
| Suicidality (Escalating) | ✅ | — | — | — |
| Suicidality (Self-harm) | ✅ | — | — | — |
| Duty to Warn | ✅ | ✅ | ✅ | ✅ Third-party attribution |
| Mandatory Reporting (Child) | ✅ | — | ✅ | — |
| Mandatory Reporting (Elder) | ✅ | — | — | — |
| Mandatory Reporting (Sexual) | ✅ | — | — | — |
| Treatment Plan | ✅ | — | ✅ | — |
| Multi-category | ✅ | — | — | — |
| Idiom false positives | — | ✅ | — | ✅ Borderline |
| High distress / no concern | — | ✅ | — | ✅ |
| Partial inadequate response | — | — | — | ✅ (Known weakness) |
| Cultural indirect expression | — | — | — | ✅ Semantic only |
