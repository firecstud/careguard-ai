import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

try:
    from backend.audit.required_responses import REQUIRED_RESPONSES
    from backend.audit.response_checker import RESPONSE_WINDOW, check_response_window
    from backend.audit.trigger_phrases import CATEGORY_DISPLAY_NAMES
    from backend.llm_client import FALLBACK_RECOMMENDATIONS
except ImportError:
    from audit.required_responses import REQUIRED_RESPONSES
    from audit.response_checker import RESPONSE_WINDOW, check_response_window
    from audit.trigger_phrases import CATEGORY_DISPLAY_NAMES
    from llm_client import FALLBACK_RECOMMENDATIONS

from .gemini_runtime import generate_json_array


JsonGenerator = Callable[[str], Awaitable[List[Dict[str, Any]]]]

THERAPIST_ANALYSIS_PROMPT = """You are the therapist-response stage of CareGuard AI, a clinical quality-assurance tool.

Review the complete dialogue only to judge each supplied patient-risk finding. Do not identify new patient disclosures. Judge the therapist's response after each listed disclosure using clinical quality and applicable organizational policy; do not make jurisdiction-specific legal conclusions.

An adequate response is specific to the disclosure and proportionate to its acuity:
- Suicidality: clarify ideation, plan, means/access, intent, timing, prior behavior, and protective factors as indicated; take or arrange an appropriate safety action, collaborative safety plan, emergency pathway, and crisis resources when warranted. Generic empathy or coping advice alone is inadequate for an unassessed safety disclosure.
- Threats to others: assess target, intent, means/access, planning, timeframe, imminence, and credibility; follow applicable duty-to-protect policy and escalation procedures where indicated. Generic anger reflection alone is inadequate for a credible, specific threat.
- Abuse or neglect: clarify immediate safety, explain confidentiality limits as appropriate, and follow the applicable reporting and safeguarding pathway. Empathy alone is inadequate when safety or reporting follow-up is indicated.
- Medication or treatment change: clarify the change and symptoms, document and coordinate with the treating prescriber or appropriate urgent support. Do not require the therapist to prescribe or alter medication.
- Crisis resources or informed consent: clearly communicate available crisis pathways or relevant confidentiality exceptions when the patient disclosure calls for them.

Return ONLY a JSON array with one object for every supplied patient-risk finding. Each object must contain:
{
  "utterance_index": 0,
  "category": "same category as the supplied finding",
  "adequacy_rating": "ADEQUATE | INADEQUATE",
  "therapist_quote": "exact relevant therapist words, or an empty string if none",
  "therapist_failure_description": "specific description; required when INADEQUATE",
  "what_was_missed": "specific assessment or action missing; required when INADEQUATE",
  "what_should_have_been_said": "brief clinically appropriate response; required when INADEQUATE"
}

Return [] only when there are no supplied patient-risk findings."""


@dataclass
class TherapistAnalysis:
    findings: List[Dict[str, Any]]
    source: str
    warning: Optional[str] = None


def _format_transcript(utterances: List[Dict[str, Any]]) -> str:
    lines = []
    for index, utterance in enumerate(utterances):
        timestamp = utterance.get("start_time")
        prefix = f"[{timestamp}] " if timestamp else ""
        lines.append(
            f"{index}. {utterance.get('speaker', 'Unknown')}: {prefix}{utterance.get('text', '')}"
        )
    return "\n".join(lines)


def _risk_context(patient_findings: List[Dict[str, Any]]) -> str:
    context = []
    for finding in patient_findings:
        context.append({
            "utterance_index": finding["utterance_index"],
            "category": finding["category"],
            "severity": finding["severity"],
            "patient_quote": finding["patient_quote"],
            "patient_intent": finding.get("patient_intent", ""),
            "risk_reasoning": finding.get("risk_reasoning", ""),
            "risk_indicators": finding.get("risk_indicators", []),
        })
    return json.dumps(context, ensure_ascii=False)


def _normalize_therapist_findings(
    items: List[Dict[str, Any]],
    patient_findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    expected = {
        (finding["utterance_index"], finding["category"])
        for finding in patient_findings
    }
    findings = []
    seen = set()

    for item in items:
        try:
            utterance_index = int(item.get("utterance_index"))
        except (TypeError, ValueError):
            continue
        category = str(item.get("category", "")).strip()
        key = (utterance_index, category)
        if key not in expected or key in seen:
            continue
        if str(item.get("adequacy_rating", "")).upper() != "INADEQUATE":
            continue
        seen.add(key)

        findings.append({
            "utterance_index": utterance_index,
            "category": category,
            "adequacy_rating": "INADEQUATE",
            "therapist_quote": str(item.get("therapist_quote", "")).strip(),
            "therapist_failure_description": str(
                item.get(
                    "therapist_failure_description",
                    f"The therapist did not adequately address the {category} disclosure.",
                )
            ).strip(),
            "what_was_missed": str(
                item.get("what_was_missed", f"Therapist did not adequately assess the {category} concern.")
            ).strip(),
            "what_should_have_been_said": str(
                item.get(
                    "what_should_have_been_said",
                    FALLBACK_RECOMMENDATIONS.get(category, FALLBACK_RECOMMENDATIONS["treatment_plan"]),
                )
            ).strip(),
            "detection_method": "semantic_therapist_llm",
        })

    return findings


def _therapist_excerpt(utterances: List[Dict[str, Any]], trigger_index: int) -> str:
    excerpts = []
    window_end = min(trigger_index + RESPONSE_WINDOW + 1, len(utterances))
    for utterance in utterances[trigger_index + 1:window_end]:
        if utterance.get("speaker", "").lower() == "therapist":
            excerpts.append(utterance.get("text", "").strip())
    return " ".join(excerpts)


def fallback_therapist_analysis(
    utterances: List[Dict[str, Any]],
    patient_findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    findings = []

    for patient_finding in patient_findings:
        category = patient_finding["category"]
        trigger_index = patient_finding["utterance_index"]
        if category not in REQUIRED_RESPONSES:
            continue

        check = check_response_window(utterances, trigger_index, category)
        if check["responded"]:
            continue

        therapist_quote = _therapist_excerpt(utterances, trigger_index)
        missing = ", ".join(check["missing_phrases"][:2]) or "an appropriate safety response"
        findings.append({
            "utterance_index": trigger_index,
            "category": category,
            "adequacy_rating": "INADEQUATE",
            "therapist_quote": therapist_quote,
            "therapist_failure_description": (
                f"The therapist responded with '{therapist_quote[:160]}' without adequately addressing "
                f"the {category} concern."
                if therapist_quote
                else f"No therapist response was documented within the review window for the {category} concern."
            ),
            "what_was_missed": f"The therapist did not demonstrate the required follow-up for {missing}.",
            "what_should_have_been_said": FALLBACK_RECOMMENDATIONS.get(
                category, FALLBACK_RECOMMENDATIONS["treatment_plan"]
            ),
            "detection_method": "response_window_fallback",
        })

    return findings


async def analyze_therapist_responses(
    utterances: List[Dict[str, Any]],
    patient_findings: List[Dict[str, Any]],
    generator: JsonGenerator = generate_json_array,
) -> TherapistAnalysis:
    if not patient_findings:
        return TherapistAnalysis(findings=[], source="not_run")

    prompt = (
        THERAPIST_ANALYSIS_PROMPT
        + "\n\nSUPPLIED PATIENT-RISK FINDINGS:\n"
        + _risk_context(patient_findings)
        + "\n\nCOMPLETE TRANSCRIPT:\n"
        + _format_transcript(utterances)
    )

    try:
        findings = _normalize_therapist_findings(await generator(prompt), patient_findings)
        return TherapistAnalysis(findings=findings, source="llm")
    except Exception:
        return TherapistAnalysis(
            findings=fallback_therapist_analysis(utterances, patient_findings),
            source="fallback",
            warning="Therapist semantic analysis was unavailable; response-window fallback was used.",
        )
