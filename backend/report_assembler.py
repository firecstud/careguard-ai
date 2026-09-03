"""
Report assembler: collects flags, calculates risk score, generates final report.
"""

import math
from typing import Dict, List, Optional

try:
    from backend.audit.trigger_phrases import SEVERITY_MAP
    from backend.shared.transcript_schema import LiabilityFlag, LiabilityReport
except ImportError:
    from audit.trigger_phrases import SEVERITY_MAP
    from shared.transcript_schema import LiabilityFlag, LiabilityReport


def calculate_risk_score(flags: List[LiabilityFlag]) -> int:
    if not flags:
        return 0

    high_count = sum(1 for f in flags if f.severity == "HIGH")
    medium_count = sum(1 for f in flags if f.severity == "MEDIUM")
    low_count = sum(1 for f in flags if f.severity == "LOW")

    raw_score = high_count * 40 + medium_count * 20 + low_count * 10
    return min(100, int(100 * (1 - math.exp(-raw_score / 50))))


def get_risk_level(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MODERATE"
    if score >= 20:
        return "LOW"
    return "MINIMAL"


def assemble_report(
    session_id: str,
    raw_flags: List[Dict],
    recommendations: Optional[List[str]] = None,
    analysis_metadata: Optional[Dict] = None,
) -> LiabilityReport:
    flags = []
    recommendations = recommendations or []

    for index, raw in enumerate(raw_flags):
        category = raw["category"]
        recommendation = (
            raw.get("what_should_have_been_said")
            or (recommendations[index] if index < len(recommendations) else None)
            or f"Provide an appropriate {category} response."
        )
        flags.append(LiabilityFlag(
            category=category,
            severity=raw.get("severity", SEVERITY_MAP.get(category, "LOW")),
            patient_quote=raw["patient_quote"],
            detection_method=raw.get("detection_method", "keyword_match"),
            what_was_missed=raw.get("what_was_missed") or f"Therapist did not perform {category} response",
            what_should_have_been_said=recommendation,
            therapist_failure_description=raw.get("therapist_failure_description"),
            utterance_index=raw["utterance_index"],
            timestamp=raw.get("timestamp"),
            patient_intent=raw.get("patient_intent"),
            risk_reasoning=raw.get("risk_reasoning"),
            risk_indicators=raw.get("risk_indicators") or [],
            patient_confidence=raw.get("patient_confidence"),
            adequacy_rating=raw.get("adequacy_rating"),
            therapist_quote=raw.get("therapist_quote"),
        ))

    risk_score = calculate_risk_score(flags)
    return LiabilityReport(
        session_id=session_id,
        overall_risk_score=risk_score,
        risk_level=get_risk_level(risk_score),
        flags=flags,
        analysis_metadata=analysis_metadata,
    )
