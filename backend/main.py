"""
CareGuard AI — FastAPI Backend
POST /analyze — accepts a transcript JSON, returns a liability report.
Serves static frontend from /static for drag-and-drop GUI.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyzers import run_two_stage_audit
from audit.keyword_scanner import scan_transcript
from report_assembler import assemble_report
from shared.transcript_schema import LiabilityReport, Transcript

app = FastAPI(title="CareGuard AI", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def check_api_key():
    if not os.getenv("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY not set. Semantic analysis is disabled.")
        print("         Keyword and response-window fallbacks will be used.")
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
