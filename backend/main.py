"""
CareGuard AI — FastAPI Backend
POST /transcribe — accepts an audio file (MP3/WAV/M4A), returns a speaker-labeled transcript JSON.
POST /analyze — accepts a transcript JSON, returns a liability report.
POST /session/{id}/swap-speakers — flips Therapist/Patient labels on a stored transcript.
Serves static frontend from /static for drag-and-drop GUI.
"""

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyzers import run_two_stage_audit
from audit.keyword_scanner import scan_transcript
from report_assembler import assemble_report
from shared.transcript_schema import LiabilityReport, Transcript
from transcription import (
    TranscriptionError,
    TranscriptionUnavailable,
    save_session,
    swap_speakers,
    transcribe_audio,
)

app = FastAPI(title="CareGuard AI", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


@app.on_event("startup")
async def check_api_key():
    if not os.getenv("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY not set. Audio transcription is disabled (no fallback exists).")
        print("         Semantic analysis falls back to keyword and response-window checks.")
        print("         This tool requires clinician and legal review; it is not safe for clinical use alone.")


@app.post("/analyze", response_model=LiabilityReport)
async def analyze_transcript(transcript: Transcript):
    utterances = [utterance.model_dump() for utterance in transcript.utterances]
    keyword_hints = scan_transcript(utterances)
    outcome = await run_two_stage_audit(utterances, keyword_hints)
    return assemble_report(
        transcript.session_id,
        outcome.flags,
        analysis_metadata={
            "patient_stage": outcome.patient_stage,
            "therapist_stage": outcome.therapist_stage,
            "warnings": outcome.warnings,
        },
    )


@app.post("/transcribe", response_model=Transcript)
async def transcribe_session(file: UploadFile = File(...)):
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if not filename or extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio file. Allowed extensions: {sorted(ALLOWED_AUDIO_EXTENSIONS)}.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    session_id = uuid.uuid4().hex[:8]
    audio_path = UPLOAD_DIR / f"{session_id}{extension}"

    written = 0
    try:
        with audio_path.open("wb") as destination:
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Audio file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.",
                    )
                destination.write(chunk)
    except HTTPException:
        audio_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    try:
        transcript = await transcribe_audio(str(audio_path), session_id, filename)
    except TranscriptionUnavailable:
        audio_path.unlink(missing_ok=True)
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail="Transcription unavailable: GEMINI_API_KEY is not configured. No fallback exists for audio transcription.",
            )
        raise HTTPException(
            status_code=502,
            detail="Transcription failed at the Gemini API. No fallback exists; please retry the upload.",
        )
    except TranscriptionError as error:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(error))

    save_session(session_id, transcript)
    return transcript


@app.post("/session/{session_id}/swap-speakers", response_model=Transcript)
async def swap_session_speakers(session_id: str):
    transcript = swap_speakers(session_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail=f"Unknown session_id: {session_id}. Transcripts are stored in memory and cleared on restart.")
    return transcript


@app.get("/health")
async def health_check():
    return {"status": "ok", "gemini_configured": bool(os.getenv("GEMINI_API_KEY"))}


STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_index():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"status": "ok", "message": "CareGuard AI backend running. Frontend not found in /static."}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
