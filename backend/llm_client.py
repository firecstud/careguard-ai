"""
LLM client for CareGuard AI.
Uses Gemini via google-genai as a specialized medical compliance auditor.

full_dialogue_audit: single call with full transcript (patient + therapist),
  returns all flags with context-aware detection and therapist adequacy analysis.
Falls back to keyword-only pipeline if the API call fails or key is missing.
"""

import os
import json
import asyncio
from typing import List, Dict, Optional

import google.genai as genai

try:
    from backend.audit.trigger_phrases import CATEGORY_DISPLAY_NAMES, SEVERITY_MAP
except ImportError:
    from audit.trigger_phrases import CATEGORY_DISPLAY_NAMES, SEVERITY_MAP

MEDICAL_AUDITOR_SYSTEM_PROMPT = """You are CareGuard AI, a clinical conversation compliance auditor.

Your specialty is psychotherapy liability auditing. You have deep expertise in:
- Suicide risk assessment protocols (ideation, plan, means, intent, timeline)
- Tarasoff duty-to-warn obligations (credible, specific threats toward an identifiable person)
- Mandatory reporting laws (child, elder, vulnerable adult abuse)
- Informed consent requirements (confidentiality limits, emergency procedures)
- Crisis resource provision (988 Lifeline, safety planning)

You review COMPLETE therapy transcripts — both patient and therapist speech — to identify:
1. Patient disclosures that trigger a legal or clinical obligation
2. Whether the therapist's response to each disclosure was adequate

You are precise, evidence-based, and context-aware. You never invent flags not supported
by the transcript. You understand that the same words can mean different things depending
on context — "my medication is working well" is not a treatment plan gap; "I stopped
taking my medication" is. You evaluate patterns across the full conversation, not
individual phrases in isolation.
"""

FULL_DIALOGUE_AUDIT_PROMPT = """\
Below is a complete therapy session transcript. Review the ENTIRE dialogue — both patient \
and therapist speech — and identify every liability gap.

TRANSCRIPT:
{transcript_text}

---

A keyword scanner has pre-identified these potential matches as hints. You MAY confirm, \
reject, or add to them. Do NOT be constrained by the hints — use the full context of \
the dialogue to decide what is actually a concern:
{keyword_hints_summary}

---

YOUR TASK:

Step 1 — Patient disclosures: Identify every moment where a patient disclosed something \
that triggers a legal or clinical obligation, evaluated in full context:
- Suicidal ideation, passive death wishes, or behavioral warning signs (giving away \
  possessions, farewell letters, planning, acquiring means) — even if expressed indirectly
- Credible, specific threats toward an identifiable person (Tarasoff duty-to-warn) — \
  look for specificity: named target, stated means, known location/schedule, stated intent
- Abuse disclosures — child, elder, or vulnerable adult (mandatory reporting)
- Severe distress without crisis resources provided
- Medication/treatment changes not addressed in the treatment plan

Step 2 — Therapist adequacy: For each disclosure you identify, evaluate whether the \
therapist's actual response was clinically and legally adequate. A response is INADEQUATE if:
- The therapist redirected to generic therapy talk (breathing, career steps, relationship \
  processing) instead of addressing the safety concern
- The therapist used reflective listening language WITHOUT acknowledging the legal obligation
- The therapist failed to assess risk (e.g. never asked about plan, means, timeline for \
  suicidality; never invoked Tarasoff for a specific threat)
- The therapist treated a safety disclosure as emotional content to be explored rather \
  than a legal obligation to be acted on

A response is ADEQUATE if the therapist clearly acknowledged the concern, assessed risk, \
and/or took appropriate action (safety planning, Tarasoff warning, mandatory report). If \
adequate, do NOT include it as a flag.

IMPORTANT: If the full context shows a patient disclosure is NOT a liability concern \
(e.g. reporting that medication is working well, discussing someone else's situation \
with no personal threat), do NOT flag it even if a keyword matched.

You MUST respond in EXACTLY this JSON format (an array, even if empty). Every field must be present and non-empty except the array itself:
[
  {{
    "utterance_index": <integer, 0-based index of the triggering patient utterance>,
    "patient_quote": "<exact patient words that triggered the flag>",
    "category": "<one of: suicidality, duty_to_warn, mandatory_reporting, crisis_resources, treatment_plan>",
    "severity": "<HIGH, MEDIUM, or LOW>",
    "what_was_missed": "<one sentence: what legal/clinical obligation the therapist failed to meet>",
    "therapist_failure_description": "<one sentence: quote or summarize what the therapist actually said or did that was inadequate>",
    "what_should_have_been_said": "<2-3 sentence natural clinical response the therapist should have given at that moment>"
  }}
]

The therapist_failure_description field is REQUIRED. It must describe the specific inadequate therapist response that followed the patient disclosure (e.g., 'The therapist pivoted to discussing decluttering as liberating without assessing suicide risk.').

Severity guide:
- HIGH: suicidality with plan/means/intent, Tarasoff threat with specific target and means, active abuse disclosure
- MEDIUM: passive ideation, vague threats, indirect disclosures, crisis resources not provided
- LOW: treatment plan gaps, medication changes not followed up

If you find no liability gaps, respond with an empty array: []

Respond ONLY with the JSON array. No preamble, no explanation, no markdown fences."""


def _format_transcript(utterances: List[Dict]) -> str:
    lines = []
    for i, utt in enumerate(utterances):
        speaker = utt.get("speaker", "Unknown")
        text = utt.get("text", "")
        ts = utt.get("start_time", "")
        prefix = f"[{ts}] " if ts else ""
        lines.append(f"{i}. {speaker}: {prefix}{text}")
    return "\n".join(lines)


def _extract_therapist_failure(utterances: List[Dict], flag_index: int, category: str) -> str:
    """Build a fallback therapist_failure_description from the next therapist utterance(s)."""
    therapist_texts = []
    for utt in utterances[flag_index + 1:]:
        if utt.get("speaker", "").lower() == "therapist":
            therapist_texts.append(utt.get("text", "").strip())
        elif utt.get("speaker", "").lower() == "patient":
            break
    if therapist_texts:
        combined = " ".join(therapist_texts)
        snippet = combined[:160] + ("..." if len(combined) > 160 else "")
        return f"The therapist responded: '{snippet}' without adequately addressing the {category} concern."
    return f"The therapist did not adequately address the {category} disclosure."


def _format_keyword_hints(hints: List[Dict]) -> str:
    if not hints:
        return "None"
    lines = []
    for h in hints:
        cat = CATEGORY_DISPLAY_NAMES.get(h["category"], h["category"])
        method = h.get("detection_method", "")
        phrase = h.get("matched_phrase", "")
        quote = h.get("patient_quote", "")[:80]
        lines.append(f'  - [{cat}] matched "{phrase}" ({method}) in: "{quote}..."')
    return "\n".join(lines)


def _fallback_keyword_flags(utterances: List[Dict], keyword_hints: List[Dict]) -> List[Dict]:
    """
    Old-style keyword+response_checker pipeline used when no API key is set.
    Filters out hints where the therapist already responded adequately.
    """
    try:
        from audit.response_checker import check_response_window
    except ImportError:
        from backend.audit.response_checker import check_response_window

    results = []
    for h in keyword_hints:
        cat = h["category"]
        idx = h["utterance_index"]
        check = check_response_window(utterances, idx, cat)
        if check["responded"]:
            continue
        results.append({
            "utterance_index": idx,
            "patient_quote": h["patient_quote"],
            "category": cat,
            "severity": SEVERITY_MAP.get(cat, "LOW"),
            "what_was_missed": f"Therapist did not perform {cat} response",
            "therapist_failure_description": None,
            "what_should_have_been_said": FALLBACK_RECOMMENDATIONS.get(cat, FALLBACK_RECOMMENDATIONS["treatment_plan"]),
            "detection_method": "keyword_match",
        })
    return results


async def full_dialogue_audit(
    utterances: List[Dict],
    keyword_hints: List[Dict],
) -> List[Dict]:
    """
    Single LLM call that reviews the full transcript (patient + therapist) and returns
    context-aware flags. Each flag includes therapist_failure_description.
    Falls back to keyword_hints formatted as flags if the API call fails.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return _fallback_keyword_flags(utterances, keyword_hints)

    client = genai.Client(api_key=api_key)

    transcript_text = _format_transcript(utterances)
    hints_summary = _format_keyword_hints(keyword_hints)
    prompt = FULL_DIALOGUE_AUDIT_PROMPT.format(
        transcript_text=transcript_text,
        keyword_hints_summary=hints_summary,
    )

    full_prompt = MEDICAL_AUDITOR_SYSTEM_PROMPT + "\n\n" + prompt

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-3.6-flash",
                contents=full_prompt,
            ),
        )
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]

        data = json.loads(text)
        if not isinstance(data, list):
            return _fallback_keyword_flags(utterances, keyword_hints)

        results = []
        for item in data:
            if not isinstance(item, dict):
                continue
            category = item.get("category", "")
            if category not in CATEGORY_DISPLAY_NAMES:
                continue
            utterance_index = int(item.get("utterance_index", 0))
            results.append({
                "utterance_index": utterance_index,
                "patient_quote": item.get("patient_quote", ""),
                "category": category,
                "severity": item.get("severity", SEVERITY_MAP.get(category, "LOW")),
                "what_was_missed": item.get("what_was_missed", ""),
                "therapist_failure_description": item.get("therapist_failure_description") or _extract_therapist_failure(utterances, utterance_index, category),
                "what_should_have_been_said": item.get("what_should_have_been_said", ""),
                "detection_method": "semantic_llm",
            })
        return results

    except Exception as e:
        print(f"WARNING: Gemini API call failed ({e}), falling back to keyword pipeline.")
        return _fallback_keyword_flags(utterances, keyword_hints)


FALLBACK_RECOMMENDATIONS = {
    "suicidality": (
        "I want to make sure I understand what you're experiencing. "
        "Are you having thoughts of ending your life, and if so, do you have "
        "a plan or timeline for doing that? Your safety is my priority, "
        "and together we can make a plan to keep you safe."
    ),
    "duty_to_warn": (
        "I need to take what you're saying very seriously. Because you've "
        "described a plan to harm a specific person, I have a legal and "
        "ethical obligation to take steps to protect them, which may include "
        "contacting them or law enforcement. Can we talk more about what's "
        "driving this?"
    ),
    "mandatory_reporting": (
        "Thank you for telling me that. I want you to know that I'm a "
        "mandated reporter, which means I'm legally required to report "
        "situations where a vulnerable person may be in danger. I'd like "
        "to help you understand what that means and what the next steps "
        "would be."
    ),
    "informed_consent": (
        "Before we continue, I want to remind you about the limits of "
        "confidentiality. Everything we discuss is confidential with a "
        "few important exceptions — if you disclose intent to harm "
        "yourself or someone else, or if there is abuse of a minor or "
        "vulnerable adult, I am legally required to take action. Here "
        "is our crisis contact information."
    ),
    "crisis_resources": (
        "If you're in crisis between our sessions, please call or text "
        "988 to reach the Suicide & Crisis Lifeline. It's free, "
        "confidential, and available 24/7. Do you have someone you can "
        "reach out to tonight?"
    ),
    "treatment_plan": (
        "I appreciate you sharing that. Let's talk about how this fits "
        "into our treatment plan and what our next steps should be. "
        "I'd also like to confirm our next appointment before we wrap "
        "up today."
    ),
}


# Legacy function kept for offline tests (run_tests.py, edge_cases.py)
async def generate_recommendations_batch(flags: List[Dict]) -> List[str]:
    return [
        FALLBACK_RECOMMENDATIONS.get(f["category"], FALLBACK_RECOMMENDATIONS["treatment_plan"])
        for f in flags
    ]


# Legacy alias kept for any external callers
async def whole_transcript_audit(utterances: List[Dict], rule_flags: List[Dict]) -> List[Dict]:
    return await full_dialogue_audit(utterances, rule_flags)
