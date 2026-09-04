import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import google.genai as genai
from google.genai import types

try:
    from backend.analyzers.gemini_runtime import parse_json_array
except ImportError:
    from analyzers.gemini_runtime import parse_json_array


class TranscriptionUnavailable(RuntimeError):
    pass


INLINE_LIMIT_BYTES = 18 * 1024 * 1024

MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}

FILE_POLL_INTERVAL_SECONDS = 2


def _resolve_mime(audio_path: Path) -> str:
    return MIME_TYPES.get(audio_path.suffix.lower(), "application/octet-stream")


async def _upload_audio_file(
    loop: asyncio.AbstractEventLoop,
    client: genai.Client,
    audio_path: Path,
    mime_type: str,
) -> types.File:
    poll_timeout = float(os.getenv("GEMINI_FILES_POLL_TIMEOUT_SECONDS", "120"))
    uploaded = await loop.run_in_executor(
        None,
        lambda: client.files.upload(
            file=str(audio_path),
            config={"mime_type": mime_type, "display_name": audio_path.name},
        ),
    )
    deadline = loop.time() + poll_timeout
    while True:
        file = await loop.run_in_executor(None, lambda: client.files.get(name=uploaded.name))
        if file.state == types.FileState.ACTIVE:
            return file
        if file.state == types.FileState.FAILED:
            raise TranscriptionUnavailable("Gemini file processing failed")
        if loop.time() >= deadline:
            raise TranscriptionUnavailable("Gemini file processing timed out")
        await asyncio.sleep(FILE_POLL_INTERVAL_SECONDS)


async def _audio_part(
    loop: asyncio.AbstractEventLoop,
    client: genai.Client,
    audio_path: Path,
    mime_type: str,
) -> Tuple[types.Part, Optional[str]]:
    if audio_path.stat().st_size < INLINE_LIMIT_BYTES:
        data = await loop.run_in_executor(None, lambda: audio_path.read_bytes())
        return types.Part.from_bytes(data=data, mime_type=mime_type), None
    uploaded = await _upload_audio_file(loop, client, audio_path, mime_type)
    part = types.Part.from_uri(
        file_uri=uploaded.uri,
        mime_type=uploaded.mime_type or mime_type,
    )
    return part, uploaded.name


async def _delete_file_quietly(
    loop: asyncio.AbstractEventLoop,
    client: genai.Client,
    file_name: str,
) -> None:
    try:
        await loop.run_in_executor(None, lambda: client.files.delete(name=file_name))
    except Exception:
        pass


async def generate_json_array_from_audio(
    prompt: str,
    audio_path: str | Path,
) -> List[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise TranscriptionUnavailable("Gemini API key is unavailable")

    client = genai.Client(api_key=api_key)
    model = (
        os.getenv("GEMINI_TRANSCRIBE_MODEL")
        or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    )
    timeout_seconds = float(os.getenv("GEMINI_TRANSCRIBE_TIMEOUT_SECONDS", "300"))
    # Two attempts: transient capacity 503s fail in seconds (not the full call), so
    # one retry costs little worst-case latency but recovers most flaky failures.
    attempts = max(1, int(os.getenv("GEMINI_TRANSCRIBE_MAX_ATTEMPTS", "2")))
    path = Path(audio_path)
    mime_type = _resolve_mime(path)
    error: Exception | None = None

    for _ in range(attempts):
        uploaded_name: Optional[str] = None
        try:
            loop = asyncio.get_running_loop()
            part, uploaded_name = await _audio_part(loop, client, path, mime_type)
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=model,
                        contents=[part, prompt],
                    ),
                ),
                timeout=timeout_seconds,
            )
            return parse_json_array(response.text)
        except Exception as exc:
            error = exc
        finally:
            if uploaded_name is not None:
                await _delete_file_quietly(loop, client, uploaded_name)

    raise TranscriptionUnavailable("Gemini audio transcription was unavailable") from error
