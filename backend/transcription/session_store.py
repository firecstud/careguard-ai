from collections import OrderedDict
from typing import Any, Dict, Optional


MAX_SESSIONS = 50

# Prototype-only: process-local storage, lost on restart, not multi-worker safe.
_SESSIONS: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()


def save_session(session_id: str, transcript: Dict[str, Any]) -> None:
    _SESSIONS[session_id] = transcript
    _SESSIONS.move_to_end(session_id)
    while len(_SESSIONS) > MAX_SESSIONS:
        _SESSIONS.popitem(last=False)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return _SESSIONS.get(session_id)


def _flip_utterance(utterance: Dict[str, Any]) -> Dict[str, Any]:
    swapped = dict(utterance)
    if utterance.get("speaker") == "Therapist":
        swapped["speaker"] = "Patient"
        swapped["speaker_id"] = 1
    else:
        swapped["speaker"] = "Therapist"
        swapped["speaker_id"] = 0
    return swapped


def swap_speakers(session_id: str) -> Optional[Dict[str, Any]]:
    transcript = _SESSIONS.get(session_id)
    if transcript is None:
        return None
    flipped = {
        **transcript,
        "utterances": [_flip_utterance(u) for u in transcript.get("utterances", [])],
    }
    _SESSIONS[session_id] = flipped
    return flipped


def clear_sessions() -> None:
    _SESSIONS.clear()
