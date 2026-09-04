import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.audit.keyword_scanner import scan_transcript
from backend.analyzers import run_two_stage_audit
from backend.report_assembler import assemble_report

# Import the app first: it puts backend/ on sys.path, so the transcription
# surface below is the SAME module instance (and exception classes) that
# backend.main.py's endpoints use. Importing via backend.transcription would
# create a second instance whose TranscriptionUnavailable the app cannot catch.
import backend.main as backend_main  # noqa: E402
import transcription as app_transcription  # noqa: E402
from transcription import (  # noqa: E402
    TranscriptionError,
    TranscriptionUnavailable,
    save_session,
    swap_speakers,
    transcribe_audio,
)
from transcription.session_store import clear_sessions  # noqa: E402
from transcription.transcriber import (  # noqa: E402
    build_transcript,
    normalize_timestamp,
    normalize_utterances,
)

from fastapi.testclient import TestClient


FAKE_ITEMS = [
    {"speaker": "Patient", "start_time": 1, "end_time": 6, "text": "I want to die.", "diarization_confidence": 0.9},
    {"speaker": "Therapist", "start_time": 8, "end_time": 12, "text": "That sounds very difficult.", "diarization_confidence": 0.85},
]

PATIENT_RESPONSE = [{
    "utterance_index": 0,
    "category": "suicidality",
    "severity": "HIGH",
    "patient_quote": "I want to die.",
    "patient_intent": "Active suicidal ideation.",
    "risk_reasoning": "Direct statement of a wish to die.",
    "risk_indicators": ["Active ideation"],
    "patient_confidence": 0.92,
}]

THERAPIST_RESPONSE = [{
    "utterance_index": 0,
    "category": "suicidality",
    "adequacy_rating": "INADEQUATE",
    "therapist_quote": "That sounds very difficult.",
    "therapist_failure_description": "Empathy without any suicide-risk assessment.",
    "what_was_missed": "Assessment of ideation, plan, means, intent, and immediate safety.",
    "what_should_have_been_said": "Are you having thoughts of ending your life, and do you have a plan or access to means?",
}]


async def fake_generator(prompt, audio_path):
    return [dict(item) for item in FAKE_ITEMS]


async def unavailable_generator(prompt, audio_path):
    raise TranscriptionUnavailable("offline test")


async def empty_generator(prompt, audio_path):
    return []


async def patient_success(_prompt):
    return [dict(item) for item in PATIENT_RESPONSE]


async def therapist_success(_prompt):
    return [dict(item) for item in THERAPIST_RESPONSE]


class TimestampNormalizationTests(unittest.TestCase):
    def test_compact_and_seconds_inputs(self):
        self.assertEqual(normalize_timestamp("1:23"), "00:01:23")
        self.assertEqual(normalize_timestamp(83), "00:01:23")
        self.assertEqual(normalize_timestamp(83.5), "00:01:23")
        self.assertEqual(normalize_timestamp("83.5"), "00:01:23")

    def test_strips_milliseconds(self):
        self.assertEqual(normalize_timestamp("00:01:23.456"), "00:01:23")

    def test_hour_rollover(self):
        self.assertEqual(normalize_timestamp(3725), "01:02:05")
        self.assertEqual(normalize_timestamp("1:02:05"), "01:02:05")

    def test_junk_returns_none(self):
        self.assertIsNone(normalize_timestamp(None))
        self.assertIsNone(normalize_timestamp(""))
        self.assertIsNone(normalize_timestamp("junk"))
        self.assertIsNone(normalize_timestamp("1:2:3:4"))
        self.assertIsNone(normalize_timestamp(-5))
        self.assertIsNone(normalize_timestamp("1:-2"))


class UtteranceNormalizationTests(unittest.TestCase):
    def test_coerces_speakers_and_drops_empty_text(self):
        items = [
            {"speaker": "PATIENT", "text": "I want to die.", "start_time": 5},
            {"speaker": "Dr. Smith", "text": "Tell me more.", "start_time": 12},
            {"speaker": "Therapist", "text": "   ", "start_time": 20},
            {"speaker": "therapist", "text": "Thank you for sharing.", "start_time": 25, "diarization_confidence": 1.7},
        ]
        utterances = normalize_utterances(items)

        self.assertEqual(len(utterances), 3)
        self.assertEqual(utterances[0]["speaker"], "Patient")
        self.assertEqual(utterances[0]["speaker_id"], 1)
        self.assertEqual(utterances[0]["start_time"], "00:00:05")
        self.assertEqual(utterances[1]["speaker"], "Patient")
        self.assertEqual(utterances[1]["speaker_id"], 1)
        self.assertEqual(utterances[2]["speaker"], "Therapist")
        self.assertEqual(utterances[2]["speaker_id"], 0)
        self.assertEqual(utterances[2]["diarization_confidence"], 1.0)

    def test_invalid_confidence_is_omitted(self):
        utterances = normalize_utterances([
            {"speaker": "Patient", "text": "Hello.", "diarization_confidence": "high"},
        ])
        self.assertNotIn("diarization_confidence", utterances[0])


class BuildTranscriptTests(unittest.TestCase):
    def test_round_trips_through_transcript_schema(self):
        transcript = build_transcript("sess-1", "session.mp3", FAKE_ITEMS)

        self.assertEqual(transcript["session_id"], "sess-1")
        self.assertEqual(transcript["audio_file"], "session.mp3")
        self.assertEqual(len(transcript["utterances"]), 2)
        self.assertEqual(transcript["utterances"][0]["speaker"], "Patient")
        self.assertEqual(transcript["utterances"][0]["start_time"], "00:00:01")
        self.assertEqual(transcript["utterances"][0]["end_time"], "00:00:06")
        self.assertEqual(transcript["utterances"][0]["speaker_id"], 1)
        self.assertEqual(transcript["utterances"][0]["diarization_confidence"], 0.9)
        self.assertEqual(transcript["utterances"][1]["speaker_id"], 0)


class TranscribeAudioTests(unittest.TestCase):
    def test_transcribes_with_injected_generator(self):
        transcript = asyncio.run(transcribe_audio(
            "/tmp/fake.mp3", "sess-1", "fake.mp3", transcriber=fake_generator
        ))
        self.assertEqual(transcript["session_id"], "sess-1")
        self.assertEqual(len(transcript["utterances"]), 2)

    def test_failing_generator_raises_unavailable(self):
        with self.assertRaises(TranscriptionUnavailable):
            asyncio.run(transcribe_audio(
                "/tmp/fake.mp3", "sess-1", "fake.mp3", transcriber=unavailable_generator
            ))

    def test_empty_result_raises_transcription_error(self):
        with self.assertRaises(TranscriptionError):
            asyncio.run(transcribe_audio(
                "/tmp/fake.mp3", "sess-1", "fake.mp3", transcriber=empty_generator
            ))

    def test_all_invalid_rows_raise_transcription_error(self):
        async def invalid(prompt, audio_path):
            return [{"speaker": "Patient", "text": "   "}]

        with self.assertRaises(TranscriptionError):
            asyncio.run(transcribe_audio(
                "/tmp/fake.mp3", "sess-1", "fake.mp3", transcriber=invalid
            ))


class StageOneToTwoSeamTests(unittest.TestCase):
    def test_transcript_output_feeds_stage_two_pipeline(self):
        transcript = build_transcript("sess-1", "session.mp3", FAKE_ITEMS)
        utterances = transcript["utterances"]

        keyword_hints = scan_transcript(utterances)
        self.assertEqual(len(keyword_hints), 1)
        self.assertEqual(keyword_hints[0]["category"], "suicidality")
        self.assertEqual(keyword_hints[0]["matched_phrase"], "want to die")
        self.assertEqual(keyword_hints[0]["timestamp"], "00:00:01")

        outcome = asyncio.run(run_two_stage_audit(
            utterances,
            keyword_hints,
            patient_generator=patient_success,
            therapist_generator=therapist_success,
        ))
        self.assertEqual(outcome.patient_stage, "llm")
        self.assertEqual(outcome.therapist_stage, "llm")
        self.assertEqual(len(outcome.flags), 1)

        report = assemble_report("sess-1", outcome.flags)
        self.assertEqual(report.session_id, "sess-1")
        self.assertEqual(len(report.flags), 1)
        self.assertEqual(report.flags[0].category, "suicidality")
        self.assertEqual(report.flags[0].severity, "HIGH")
        self.assertGreater(report.overall_risk_score, 0)


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        clear_sessions()

    def tearDown(self):
        clear_sessions()

    def test_swap_flips_labels_and_speaker_ids(self):
        transcript = build_transcript("sess-2", "a.mp3", FAKE_ITEMS)
        save_session("sess-2", transcript)

        swapped = swap_speakers("sess-2")
        self.assertEqual(swapped["utterances"][0]["speaker"], "Therapist")
        self.assertEqual(swapped["utterances"][0]["speaker_id"], 0)
        self.assertEqual(swapped["utterances"][1]["speaker"], "Patient")
        self.assertEqual(swapped["utterances"][1]["speaker_id"], 1)

        restored = swap_speakers("sess-2")
        self.assertEqual(restored, transcript)

    def test_swap_unknown_session_returns_none(self):
        self.assertIsNone(swap_speakers("nope"))


class TranscribeEndpointTests(unittest.TestCase):
    def setUp(self):
        app_transcription.clear_sessions()
        self.real_transcribe_audio = backend_main.transcribe_audio
        self.upload_dir = Path(tempfile.mkdtemp())
        dir_patcher = mock.patch.object(backend_main, "UPLOAD_DIR", self.upload_dir)
        dir_patcher.start()
        self.addCleanup(dir_patcher.stop)
        self.client = TestClient(backend_main.app)

    def tearDown(self):
        app_transcription.clear_sessions()

    def _patch_transcriber(self, generator):
        async def wrapper(audio_path, session_id, audio_file):
            return await self.real_transcribe_audio(
                audio_path, session_id, audio_file, transcriber=generator
            )

        patcher = mock.patch.object(backend_main, "transcribe_audio", wrapper)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _post_audio(self, filename="session.mp3", content=b"fake audio bytes", mime="audio/mpeg"):
        return self.client.post(
            "/transcribe",
            files={"file": (filename, content, mime)},
        )

    def test_transcribe_returns_valid_transcript(self):
        self._patch_transcriber(fake_generator)
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = self._post_audio()

        self.assertEqual(response.status_code, 200)
        transcript = response.json()
        self.assertEqual(len(transcript["session_id"]), 8)
        self.assertEqual(transcript["audio_file"], "session.mp3")
        self.assertEqual(len(transcript["utterances"]), 2)
        self.assertEqual(transcript["utterances"][0]["speaker"], "Patient")
        self.assertEqual(transcript["utterances"][0]["start_time"], "00:00:01")
        self.assertEqual(transcript["utterances"][0]["speaker_id"], 1)
        self.assertEqual(transcript["utterances"][1]["speaker"], "Therapist")
        saved = list(self.upload_dir.glob("*.mp3"))
        self.assertEqual(len(saved), 1)

    def test_transcribe_rejects_unsupported_extension(self):
        response = self._post_audio(filename="notes.txt", content=b"data", mime="text/plain")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(self.upload_dir.iterdir()), [])

    def test_transcribe_rejects_oversize_upload(self):
        self._patch_transcriber(fake_generator)
        size_patcher = mock.patch.object(backend_main, "MAX_UPLOAD_BYTES", 4)
        size_patcher.start()
        self.addCleanup(size_patcher.stop)

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = self._post_audio(content=b"12345678")

        self.assertEqual(response.status_code, 413)
        self.assertEqual(list(self.upload_dir.iterdir()), [])

    def test_transcribe_without_api_key_returns_503(self):
        self._patch_transcriber(unavailable_generator)
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            response = self._post_audio()

        self.assertEqual(response.status_code, 503)
        self.assertIn("GEMINI_API_KEY", response.json()["detail"])

    def test_transcribe_failure_with_key_returns_502(self):
        self._patch_transcriber(unavailable_generator)
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = self._post_audio()

        self.assertEqual(response.status_code, 502)
        self.assertIn("retry", response.json()["detail"])

    def test_transcribe_empty_result_returns_422(self):
        self._patch_transcriber(empty_generator)
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = self._post_audio()

        self.assertEqual(response.status_code, 422)

    def test_transcript_response_feeds_analyze_endpoint(self):
        self._patch_transcriber(fake_generator)
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            transcript = self._post_audio().json()

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            analysis = self.client.post("/analyze", json=transcript)

        self.assertEqual(analysis.status_code, 200)
        report = analysis.json()
        self.assertEqual(report["session_id"], transcript["session_id"])
        self.assertGreaterEqual(len(report["flags"]), 1)
        self.assertTrue(any(f["category"] == "suicidality" for f in report["flags"]))

    def test_swap_speakers_endpoint_flips_and_404s(self):
        self._patch_transcriber(fake_generator)
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            transcript = self._post_audio().json()

        session_id = transcript["session_id"]
        response = self.client.post(f"/session/{session_id}/swap-speakers")
        self.assertEqual(response.status_code, 200)
        swapped = response.json()
        self.assertEqual(swapped["utterances"][0]["speaker"], "Therapist")
        self.assertEqual(swapped["utterances"][0]["speaker_id"], 0)

        missing = self.client.post("/session/does-not-exist/swap-speakers")
        self.assertEqual(missing.status_code, 404)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertIsInstance(body["gemini_configured"], bool)


if __name__ == "__main__":
    unittest.main()
