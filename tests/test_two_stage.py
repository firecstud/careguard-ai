import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.analyzers.gemini_runtime import LLMUnavailable, parse_json_array
from backend.analyzers.merge import merge_findings, run_two_stage_audit


UTTERANCES = [
    {"speaker": "Patient", "text": "I do not want to wake up tomorrow.", "start_time": "00:00:01"},
    {"speaker": "Therapist", "text": "That sounds very difficult.", "start_time": "00:00:08"},
]

KEYWORD_HINTS = [
    {
        "utterance_index": 0,
        "patient_quote": UTTERANCES[0]["text"],
        "category": "suicidality",
        "matched_phrase": "don't want to wake up",
        "severity": "HIGH",
    }
]

PATIENT_RESPONSE = [
    {
        "utterance_index": 0,
        "category": "suicidality",
        "severity": "HIGH",
        "patient_quote": "I do not want to wake up tomorrow.",
        "patient_intent": "A passive death wish requiring suicide-risk assessment.",
        "risk_reasoning": "The patient expresses a desire not to continue living, without plan details.",
        "risk_indicators": ["Passive death wish"],
        "patient_confidence": 0.91,
    }
]

THERAPIST_RESPONSE = [
    {
        "utterance_index": 0,
        "category": "suicidality",
        "adequacy_rating": "INADEQUATE",
        "therapist_quote": "That sounds very difficult.",
        "therapist_failure_description": "The therapist offered empathy without suicide-risk assessment.",
        "what_was_missed": "Assessment of ideation, plan, means, intent, and immediate safety.",
        "what_should_have_been_said": "Are you having thoughts of ending your life, and do you have a plan or access to means?",
    }
]


async def patient_success(_):
    return PATIENT_RESPONSE


async def therapist_success(_):
    return THERAPIST_RESPONSE


async def unavailable(_):
    raise LLMUnavailable("offline test")


class TwoStageAuditTests(unittest.TestCase):
    def test_parse_json_array_accepts_fenced_json(self):
        parsed = parse_json_array('```json\n[{"category": "suicidality"}]\n```')
        self.assertEqual(parsed, [{"category": "suicidality"}])

    def test_parse_json_array_rejects_non_array(self):
        with self.assertRaises(ValueError):
            parse_json_array('{"category": "suicidality"}')

    def test_merge_keeps_matched_two_stage_evidence_only(self):
        patient_findings = [{
            "utterance_index": 0,
            "timestamp": "00:00:01",
            "patient_quote": UTTERANCES[0]["text"],
            "category": "suicidality",
            "severity": "HIGH",
            "patient_intent": "Passive death wish.",
            "risk_reasoning": "Safety assessment is indicated.",
            "risk_indicators": ["Passive death wish"],
            "patient_confidence": 0.9,
        }]
        therapist_findings = [
            {
                **THERAPIST_RESPONSE[0],
                "detection_method": "semantic_therapist_llm",
            },
            {
                **THERAPIST_RESPONSE[0],
                "utterance_index": 1,
                "category": "treatment_plan",
            },
        ]

        flags = merge_findings(patient_findings, therapist_findings, "llm", "llm")

        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["patient_intent"], "Passive death wish.")
        self.assertEqual(flags[0]["therapist_quote"], "That sounds very difficult.")
        self.assertEqual(flags[0]["detection_method"], "llm_patient+llm_therapist")

    def test_patient_fallback_does_not_disable_therapist_semantic_stage(self):
        outcome = asyncio.run(run_two_stage_audit(
            UTTERANCES,
            KEYWORD_HINTS,
            patient_generator=unavailable,
            therapist_generator=therapist_success,
        ))

        self.assertEqual(outcome.patient_stage, "fallback")
        self.assertEqual(outcome.therapist_stage, "llm")
        self.assertEqual(len(outcome.flags), 1)
        self.assertEqual(outcome.flags[0]["detection_method"], "fallback_patient+llm_therapist")
        self.assertEqual(len(outcome.warnings), 1)

    def test_therapist_fallback_does_not_disable_patient_semantic_stage(self):
        outcome = asyncio.run(run_two_stage_audit(
            UTTERANCES,
            KEYWORD_HINTS,
            patient_generator=patient_success,
            therapist_generator=unavailable,
        ))

        self.assertEqual(outcome.patient_stage, "llm")
        self.assertEqual(outcome.therapist_stage, "fallback")
        self.assertEqual(len(outcome.flags), 1)
        self.assertEqual(outcome.flags[0]["detection_method"], "llm_patient+fallback_therapist")
        self.assertEqual(len(outcome.warnings), 1)


if __name__ == "__main__":
    unittest.main()
