from dataclasses import dataclass
from typing import Any, Dict, List

from .patient_analyzer import JsonGenerator, analyze_patient_disclosures
from .therapist_analyzer import analyze_therapist_responses


@dataclass
class TwoStageAuditResult:
    flags: List[Dict[str, Any]]
    patient_stage: str
    therapist_stage: str
    warnings: List[str]


def merge_findings(
    patient_findings: List[Dict[str, Any]],
    therapist_findings: List[Dict[str, Any]],
    patient_source: str,
    therapist_source: str,
) -> List[Dict[str, Any]]:
    therapist_by_key = {
        (finding["utterance_index"], finding["category"]): finding
        for finding in therapist_findings
        if finding.get("adequacy_rating") == "INADEQUATE"
    }
    flags = []

    for patient_finding in patient_findings:
        key = (patient_finding["utterance_index"], patient_finding["category"])
        therapist_finding = therapist_by_key.get(key)
        if therapist_finding is None:
            continue

        flags.append({
            "utterance_index": patient_finding["utterance_index"],
            "timestamp": patient_finding.get("timestamp"),
            "patient_quote": patient_finding["patient_quote"],
            "category": patient_finding["category"],
            "severity": patient_finding["severity"],
            "patient_intent": patient_finding.get("patient_intent"),
            "risk_reasoning": patient_finding.get("risk_reasoning"),
            "risk_indicators": patient_finding.get("risk_indicators", []),
            "patient_confidence": patient_finding.get("patient_confidence"),
            "adequacy_rating": therapist_finding["adequacy_rating"],
            "therapist_quote": therapist_finding.get("therapist_quote"),
            "therapist_failure_description": therapist_finding["therapist_failure_description"],
            "what_was_missed": therapist_finding["what_was_missed"],
            "what_should_have_been_said": therapist_finding["what_should_have_been_said"],
            "detection_method": f"{patient_source}_patient+{therapist_source}_therapist",
        })

    return flags


async def run_two_stage_audit(
    utterances: List[Dict[str, Any]],
    keyword_hints: List[Dict[str, Any]],
    patient_generator: JsonGenerator | None = None,
    therapist_generator: JsonGenerator | None = None,
) -> TwoStageAuditResult:
    if patient_generator is None:
        patient_analysis = await analyze_patient_disclosures(utterances, keyword_hints)
    else:
        patient_analysis = await analyze_patient_disclosures(
            utterances, keyword_hints, patient_generator
        )

    if therapist_generator is None:
        therapist_analysis = await analyze_therapist_responses(
            utterances, patient_analysis.findings
        )
    else:
        therapist_analysis = await analyze_therapist_responses(
            utterances, patient_analysis.findings, therapist_generator
        )

    warnings = [
        warning
        for warning in (patient_analysis.warning, therapist_analysis.warning)
        if warning
    ]
    return TwoStageAuditResult(
        flags=merge_findings(
            patient_analysis.findings,
            therapist_analysis.findings,
            patient_analysis.source,
            therapist_analysis.source,
        ),
        patient_stage=patient_analysis.source,
        therapist_stage=therapist_analysis.source,
        warnings=warnings,
    )
