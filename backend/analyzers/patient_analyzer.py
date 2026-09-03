import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

try:
    from backend.audit.trigger_phrases import CATEGORY_DISPLAY_NAMES, SEVERITY_MAP
except ImportError:
    from audit.trigger_phrases import CATEGORY_DISPLAY_NAMES, SEVERITY_MAP

from .gemini_runtime import generate_json_array


JsonGenerator = Callable[[str], Awaitable[List[Dict[str, Any]]]]

PATIENT_ANALYSIS_PROMPT = """You are the patient-risk stage of CareGuard AI, a clinical quality-assurance tool.

Review ONLY the patient's utterances below. Identify patient disclosures that warrant clinical or compliance follow-up. This is triage support, not a diagnosis, emergency service, or jurisdiction-specific legal decision.

Apply these review criteria:
- Suicidality: direct ideation, passive death wishes, plan, means, intent, timing, prior behavior, protective factors, or indirect behavioral warning signs such as farewells, giving possessions away, or arranging affairs. Distinguish denial, historical discussion, third-party reports, and ordinary figurative language.
- Threats to others: credible concern rises with an identifiable target, stated intent, means or access, planning, location or schedule knowledge, timeframe, and immediacy. Describe a potential duty-to-protect concern without claiming a universal legal obligation.
- Abuse or neglect: child, elder, vulnerable-adult, or intimate-partner disclosures that may require safety assessment or reporting under applicable policy and law.
- Medication or treatment changes: new, stopped, changed, adverse, or destabilizing treatment issues that require clarification and coordination with the treating prescriber; do not recommend prescribing.
- Crisis resources and informed consent: include only when the patient disclosure specifically makes crisis support or clarification of confidentiality exceptions clinically relevant.

Use the full patient narrative for meaning and do not treat keyword hints as authoritative. Return every supported disclosure and no others.

Return ONLY a JSON array. Each object must contain:
{
  "utterance_index": 0,
  "category": "suicidality | duty_to_warn | mandatory_reporting | informed_consent | crisis_resources | treatment_plan",
  "severity": "HIGH | MEDIUM | LOW",
  "patient_quote": "exact triggering patient words",
  "patient_intent": "concise clinical interpretation of the disclosure",
  "risk_reasoning": "why this warrants follow-up and what uncertainty remains",
  "risk_indicators": ["specific transcript-grounded indicators"],
  "patient_confidence": 0.0
}

patient_confidence must be between 0 and 1. Return [] when no disclosure warrants follow-up."""


@dataclass
class PatientAnalysis:
    findings: List[Dict[str, Any]]
    source: str
    warning: Optional[str] = None


def _format_patient_utterances(utterances: List[Dict[str, Any]]) -> str:
    lines = []
    for index, utterance in enumerate(utterances):
        if utterance.get("speaker", "").lower() != "patient":
            continue
        timestamp = utterance.get("start_time")
        prefix = f"[{timestamp}] " if timestamp else ""
        lines.append(f"{index}. {prefix}{utterance.get('text', '')}")
    return "\n".join(lines) or "No patient utterances were provided."


def _normalize_patient_findings(
    items: List[Dict[str, Any]],
    utterances: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    findings = []
    seen = set()

    for item in items:
        try:
            utterance_index = int(item.get("utterance_index"))
        except (TypeError, ValueError):
            continue

        if not 0 <= utterance_index < len(utterances):
            continue
        utterance = utterances[utterance_index]
        if utterance.get("speaker", "").lower() != "patient":
            continue

        category = str(item.get("category", "")).strip()
        if category not in CATEGORY_DISPLAY_NAMES:
            continue

        key = (utterance_index, category)
        if key in seen:
            continue
        seen.add(key)

        severity = str(item.get("severity", SEVERITY_MAP.get(category, "LOW"))).upper()
        if severity not in {"HIGH", "MEDIUM", "LOW"}:
            severity = SEVERITY_MAP.get(category, "LOW")

        indicators = item.get("risk_indicators", [])
        if isinstance(indicators, str):
            indicators = [indicators]
        if not isinstance(indicators, list):
            indicators = []

        try:
            confidence = float(item.get("patient_confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0

        findings.append({
            "utterance_index": utterance_index,
            "timestamp": utterance.get("start_time"),
            "patient_quote": utterance.get("text", ""),
            "category": category,
            "severity": severity,
            "patient_intent": str(item.get("patient_intent", "Potential clinical risk disclosure requiring review.")).strip(),
            "risk_reasoning": str(item.get("risk_reasoning", "The disclosure warrants clinical follow-up.")).strip(),
            "risk_indicators": [str(indicator).strip() for indicator in indicators if str(indicator).strip()],
            "patient_confidence": min(1.0, max(0.0, confidence)),
            "detection_method": "semantic_patient_llm",
        })

    return findings


def fallback_patient_analysis(
    utterances: List[Dict[str, Any]],
    keyword_hints: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    findings = []
    seen = set()

    for hint in keyword_hints:
        category = hint.get("category")
        utterance_index = hint.get("utterance_index")
        if category not in CATEGORY_DISPLAY_NAMES or not isinstance(utterance_index, int):
            continue
        if not 0 <= utterance_index < len(utterances):
            continue
        if utterances[utterance_index].get("speaker", "").lower() != "patient":
            continue

        key = (utterance_index, category)
        if key in seen:
            continue
        seen.add(key)

        utterance = utterances[utterance_index]
        phrase = str(hint.get("matched_phrase", "keyword indicator"))
        findings.append({
            "utterance_index": utterance_index,
            "timestamp": utterance.get("start_time"),
            "patient_quote": utterance.get("text", ""),
            "category": category,
            "severity": hint.get("severity", SEVERITY_MAP.get(category, "LOW")),
            "patient_intent": "Keyword-detected disclosure requiring contextual clinical review.",
            "risk_reasoning": f'The patient utterance matched the risk indicator "{phrase}".',
            "risk_indicators": [phrase],
            "patient_confidence": 1.0,
            "detection_method": "keyword_fallback",
        })

    return findings


async def analyze_patient_disclosures(
    utterances: List[Dict[str, Any]],
    keyword_hints: List[Dict[str, Any]],
    generator: JsonGenerator = generate_json_array,
) -> PatientAnalysis:
    prompt = (
        PATIENT_ANALYSIS_PROMPT
        + "\n\nPATIENT UTTERANCES:\n"
        + _format_patient_utterances(utterances)
        + "\n\nNON-AUTHORITATIVE KEYWORD HINTS:\n"
        + json.dumps(keyword_hints, ensure_ascii=False)
    )

    try:
        findings = _normalize_patient_findings(await generator(prompt), utterances)
        return PatientAnalysis(findings=findings, source="llm")
    except Exception:
        return PatientAnalysis(
            findings=fallback_patient_analysis(utterances, keyword_hints),
            source="fallback",
            warning="Patient semantic analysis was unavailable; keyword fallback was used.",
        )
