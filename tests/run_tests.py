"""
Offline test runner: runs the audit engine on the 5 synthetic scenarios
without needing the FastAPI server or the DashScope API key.
Uses static fallback recommendations for LLM output.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.shared.transcript_schema import Transcript
from backend.audit.keyword_scanner import scan_transcript
from backend.audit.response_checker import check_response_window
from backend.audit.trigger_phrases import SEVERITY_MAP
from backend.llm_client import FALLBACK_RECOMMENDATIONS
from backend.report_assembler import assemble_report


EXPECTED = {
    "scenario_a": {"min_high": 1, "categories": {"suicidality"}},
    "scenario_b": {"min_high": 1, "categories": {"duty_to_warn"}},
    "scenario_c": {"min_high": 1, "categories": {"mandatory_reporting"}},
    "scenario_d": {"max_high": 0},
    "scenario_e": {"min_total": 1},
}


def run_scenario(path: Path):
    with open(path) as f:
        data = json.load(f)

    transcript = Transcript(**data)
    utterances = [u.model_dump() for u in transcript.utterances]

    raw_flags = scan_transcript(utterances)
    print(f"\n{'=' * 60}")
    print(f"SCENARIO: {transcript.session_id}")
    print(f"  Raw keyword matches: {len(raw_flags)}")

    confirmed = []
    for flag in raw_flags:
        cat = flag["category"]
        if cat in ("informed_consent", "treatment_plan"):
            confirmed.append(flag)
            continue
        check = check_response_window(utterances, flag["utterance_index"], cat)
        status = "RESPONDED" if check["responded"] else "MISSED"
        print(f"  [{status}] idx={flag['utterance_index']} cat={cat} "
              f"quote=\"{flag['patient_quote'][:60]}...\"")
        if not check["responded"]:
            confirmed.append(flag)

    recs = [
        FALLBACK_RECOMMENDATIONS.get(f["category"], "Appropriate response required.")
        for f in confirmed
    ]
    report = assemble_report(transcript.session_id, confirmed, recs)

    print(f"\n  REPORT:")
    print(f"    Flags confirmed: {len(report.flags)}")
    print(f"    Risk score: {report.overall_risk_score} ({report.risk_level})")
    for f in report.flags:
        print(f"    [{f.severity}] {f.category} — \"{f.patient_quote[:50]}...\"")

    return report, transcript.session_id


def main():
    transcript_dir = Path(__file__).resolve().parent / "transcripts"
    passed, failed = 0, 0

    for scenario_file in sorted(transcript_dir.glob("scenario_*.json")):
        report, sid = run_scenario(scenario_file)
        exp = EXPECTED.get(sid, {})

        high_count = sum(1 for f in report.flags if f.severity == "HIGH")
        categories = {f.category for f in report.flags}

        ok = True
        if "min_high" in exp and high_count < exp["min_high"]:
            print(f"  FAIL: expected at least {exp['min_high']} HIGH flag(s), got {high_count}")
            ok = False
        if "max_high" in exp and high_count > exp["max_high"]:
            print(f"  FAIL: expected at most {exp['max_high']} HIGH flag(s), got {high_count}")
            ok = False
        if "categories" in exp and not exp["categories"].issubset(categories):
            missing = exp["categories"] - categories
            print(f"  FAIL: missing expected categories: {missing}")
            ok = False
        if "min_total" in exp and len(report.flags) < exp["min_total"]:
            print(f"  FAIL: expected at least {exp['min_total']} total flag(s), got {len(report.flags)}")
            ok = False

        if ok:
            print(f"  PASS")
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
