# CareGuard AI

A therapy-session liability auditor. Upload an audio recording of a therapy session (or a pre-made transcript JSON) and get back a structured risk report flagging suicidality, harm disclosures, missed therapist responses, and other clinical liability gaps.

Runs locally on your machine at `http://localhost:8000`. No data leaves your network except the API calls to Google Gemini for transcription and analysis.

## Prerequisites

- **Python 3.12+**
- **uv** (fast Python package manager — [install](https://docs.astral.sh/uv/getting-started/installation/))
- **A Google Gemini API key** — free tier works. Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

## Setup

```bash
# Clone the repo
git clone https://github.com/firecstud/careguard-ai.git
cd careguard-ai

# Create a virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and replace "your_api_key_here" with your actual Gemini API key
```

## Running the server

```bash
uv run python -m uvicorn backend.main:app --reload
```

The app will be live at **http://localhost:8000**. Open that URL in a browser.

> To run without a Gemini key (e.g. for testing the UI or the deterministic fallback), start with `GEMINI_API_KEY= uv run python -m uvicorn backend.main:app --reload`. Audio transcription will be unavailable but JSON transcript uploads and the keyword-based fallback analysis will still work.

## Using the app

### Audio upload (full pipeline)

1. Drag and drop an **MP3, WAV, or M4A** file onto the drop zone, or click to browse.
2. The app transcribes the audio via Gemini, automatically identifying Therapist and Patient speakers with timestamps.
3. The transcript is then analyzed for liability gaps and a risk report is rendered.
4. If the speaker labels are wrong (Therapist/Patient swapped), click the **Swap Speakers** button that appears above the report to correct them. The analysis re-runs with the corrected labels.

### JSON transcript upload (analysis only)

Drop a transcript JSON file (with an `utterances` array) to skip transcription and go straight to analysis. Useful for re-running analysis on previously transcribed sessions.

### Expected output

The report shows:

- **Overall risk score** (0-100): MINIMAL / LOW / MODERATE / HIGH / CRITICAL
- **Flags** grouped by category: suicidality, harm-to-others, abuse disclosures, missed therapist acknowledgments, protocol violations
- **Per-utterance highlights** with speaker labels and timestamps
- **Analysis metadata**: which models ran, any degradation warnings

## Configuration

All optional — set in `.env` or as environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Your Gemini API key |
| `GEMINI_TRANSCRIBE_MODEL` | `gemini-3.6-flash` | Model for audio transcription |
| `GEMINI_TRANSCRIBE_TIMEOUT_SECONDS` | `300` | Per-call timeout for audio |
| `GEMINI_TRANSCRIBE_MAX_ATTEMPTS` | `2` | Retry count for audio calls |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Model for Stage 2 analysis |

## Running tests

```bash
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

Tests are fully offline — no API key or network needed. They cover timestamp normalization, speaker diarization logic, the Stage 1 to Stage 2 pipeline seam, swap-speakers behavior, and all HTTP endpoint paths.

## Project structure

```
backend/
  main.py                        FastAPI app, endpoints
  analyzers/                     Stage 2: two-stage LLM analysis
  audit/                         Deterministic keyword scanner + response checker
  transcription/                 Stage 1: Gemini audio transcription + diarization
  shared/transcript_schema.py    Pydantic Transcript model (shared contract)
  static/index.html              Single-page UI
  report_assembler.py            Builds the final risk report
  llm_client.py                  Gemini SDK wrapper
tests/
  test_two_stage.py              Stage 2 tests
  test_transcription.py          Stage 1 tests
```

## Limitations

- **Prototype, not clinical software.** This is a demo/audit tool, not a diagnostic device.
- **In-memory session store.** Transcripts are held in process memory and lost on restart. Uploaded audio files are kept in `uploads/` with no automatic cleanup.
- **LLM timestamps drift** on longer recordings. Stage 2 uses utterance order, not absolute time, so this affects readability rather than detection.
- **Free-tier Gemini quotas** are limited (~20 text requests/day, ~10 TTS requests/day on the flash models). Longer sessions may hit output-token limits and produce a 502.
- **Max upload size** is 100MB. Files over 18MB use the Gemini Files API (adds a polling step).
