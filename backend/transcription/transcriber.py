import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

try:
    from backend.shared.transcript_schema import Transcript
except ImportError:
    from shared.transcript_schema import Transcript

from .gemini_audio import generate_json_array_from_audio


AudioTranscriber = Callable[[str, str], Awaitable[List[Dict[str, Any]]]]


class TranscriptionError(ValueError):
    pass


TRANSCRIBE_PROMPT = """You are the transcription and diarization stage of CareGuard AI, a clinical quality-assurance tool.

Transcribe the attached therapy-session audio verbatim and label every utterance by speaker role.

Assume exactly TWO speakers: one Therapist and one Patient. Assign roles by conversational function, not by who speaks first:
- The Therapist opens and closes the session, asks open-ended and clarifying questions, reflects and summarizes what the other speaker says, offers clinical framing, assigns homework, and manages time and logistics.
- The Patient narrates their own lived experience in the first person, reports symptoms, feelings, relationships, and events, and answers questions.
Decide each role once for the whole session and stay consistent. If a third voice appears briefly, attribute it to whichever of the two roles fits best.

Transcribe verbatim. Preserve the speaker's own words, including hedges and self-corrections. Do not summarize, paraphrase, censor, sanitize, or omit any content, including distressing statements about self-harm, violence, or abuse — omissions defeat the safety purpose of this tool. Do not add commentary. Merge consecutive same-speaker sentences into one utterance; start a new utterance whenever the speaker changes.

Return ONLY a JSON array, ordered by start_time. Each object must contain:
{
  "speaker": "Therapist" | "Patient",
  "start_time": "HH:MM:SS",
  "end_time": "HH:MM:SS",
  "text": "verbatim words spoken",
  "diarization_confidence": 0.0
}

diarization_confidence is your 0-to-1 confidence in the speaker label for that utterance. Timestamps are elapsed time from the start of the recording in HH:MM:SS. Output no markdown fences, no code blocks, and no text before or after the JSON array. Return [] only if the audio contains no intelligible speech."""


def normalize_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None

    total: Optional[float] = None
    if isinstance(value, (int, float)):
        total = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d+(\.\d+)?", text):
            total = float(text)
        else:
            parts = text.split(":")
            if 2 <= len(parts) <= 3:
                try:
                    numbers = [float(part) for part in parts]
                except ValueError:
                    numbers = None
                if numbers is not None and all(n >= 0 for n in numbers):
                    total = 0.0
                    for number in numbers:
                        total = total * 60 + number

    if total is None or total < 0:
        return None

    total_seconds = int(total)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _normalize_confidence(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return None


def normalize_utterances(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    utterances = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        speaker_raw = str(item.get("speaker", "")).strip().lower()
        if speaker_raw == "therapist":
            speaker, speaker_id = "Therapist", 0
        else:
            speaker, speaker_id = "Patient", 1

        confidence = _normalize_confidence(item.get("diarization_confidence"))
        utterance = {
            "speaker": speaker,
            "text": text,
            "start_time": normalize_timestamp(item.get("start_time")),
            "end_time": normalize_timestamp(item.get("end_time")),
            "speaker_id": speaker_id,
        }
        if confidence is not None:
            utterance["diarization_confidence"] = confidence
        utterances.append(utterance)
    return utterances


def build_transcript(
    session_id: str,
    audio_file: str,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    data = {
        "session_id": session_id,
        "audio_file": audio_file,
        "utterances": normalize_utterances(items),
    }
    return Transcript(**data).model_dump()


async def transcribe_audio(
    audio_path: str,
    session_id: str,
    audio_file: str,
    transcriber: Optional[AudioTranscriber] = None,
) -> Dict[str, Any]:
    generator = transcriber or generate_json_array_from_audio
    items = await generator(TRANSCRIBE_PROMPT, str(audio_path))
    transcript = build_transcript(session_id, audio_file, items)
    if not transcript["utterances"]:
        raise TranscriptionError("Transcription produced no usable utterances")
    return transcript
