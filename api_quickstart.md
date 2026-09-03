# CareGuard AI — API Quickstart & Setup Guide
### DashScope: Real-Time ASR + Qwen-Max | Get Running on Day 1

---

## 1. Get Your DashScope API Key

1. Go to [https://dashscope.aliyuncs.com](https://dashscope.aliyuncs.com) and sign in
2. Navigate to **API Keys** (top-right menu or Model Studio console)
3. Click **Create API Key** — copy it immediately, it won't show again
4. One key covers both ASR and Qwen — no separate keys needed

> **One person on the team should create the key and share it securely (e.g. in a private message, not in the repo).** Everyone puts it in their local `.env` file.

---

## 2. Project Environment Setup

### Directory Structure
```
careguard-ai/
├── backend/
│   ├── main.py              ← FastAPI app
│   ├── stage1/
│   │   ├── audio_handler.py ← WebSocket audio ingestion (live streaming)
│   │   ├── asr_client.py    ← DashScope real-time ASR wrapper
│   │   └── file_transcriber.py ← DashScope file-based transcription (upload)
│   ├── stage2/
│   │   ├── audit_engine.py  ← Keyword scanner + report builder
│   │   ├── trigger_phrases.py
│   │   ├── required_responses.py
│   │   └── llm_client.py    ← Qwen recommendation generator
│   └── shared/
│       └── transcript_schema.py ← Shared JSON contract
├── frontend/                ← React/Vite app
├── tests/
│   └── transcripts/         ← Scenario A–E JSON files
├── demo/
│   └── cached_report.json   ← Static fallback for demo day
├── .env                     ← Your local secrets (git-ignored)
├── .env.example             ← Template committed to repo
└── requirements.txt
```

### .env file (each person creates this locally — never commit it)
```bash
DASHSCOPE_API_KEY=sk-your-key-here
```

### .env.example (commit this to repo)
```bash
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

### requirements.txt
```
dashscope>=1.14.0
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
websockets>=12.0
python-dotenv>=1.0.0
rapidfuzz>=3.9.0
pydantic>=2.0.0
python-multipart>=0.0.6
aiofiles>=23.0.0
```

### Install everything
```bash
pip install -r requirements.txt
```

---

## 3. Verify API Key Works — Test Qwen-Max (Do This First)

Run this before anything else. If this works, your key is good.

```python
# test_qwen.py
import os
from dotenv import load_dotenv
from dashscope import Generation

load_dotenv()

response = Generation.call(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    model="qwen-max",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in one sentence."}
    ],
    result_format="message"
)

print(response.output.choices[0].message.content)
# Expected: "Hello! How can I assist you today?" or similar
```

```bash
python test_qwen.py
```

**If you get an error:**
- `AuthenticationError` → API key is wrong or not loaded. Check `.env` file path.
- `QuotaExceeded` → Your account needs credits. Top up at the DashScope console.
- `ModuleNotFoundError` → Run `pip install dashscope python-dotenv`

---

## 4. Stage 1 — Real-Time ASR Setup

DashScope's real-time ASR uses a streaming API. Here is a working wrapper:

```python
# backend/stage1/asr_client.py
import os
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
from dotenv import load_dotenv

load_dotenv()

class TranscriptCallback(RecognitionCallback):
    def __init__(self, on_utterance):
        self.on_utterance = on_utterance  # callback function

    def on_complete(self):
        print("[ASR] Session complete")

    def on_error(self, result: RecognitionResult):
        print(f"[ASR] Error: {result}")

    def on_event(self, result: RecognitionResult):
        # Called for each transcript segment
        sentence = result.get_sentence()
        if sentence and Recognition.is_sentence_end(sentence):
            # A complete utterance has arrived
            text = sentence.get("text", "")
            speaker_id = sentence.get("words", [{}])[0].get("speaker_id", 0) if sentence.get("words") else 0
            self.on_utterance(text, speaker_id)


def create_recognition_session(on_utterance_callback):
    """Create and return a DashScope Recognition session."""
    callback = TranscriptCallback(on_utterance=on_utterance_callback)
    recognition = Recognition(
        model="paraformer-realtime-v2",   # DashScope real-time ASR model
        format="pcm",                      # raw PCM audio from Web Audio API
        sample_rate=16000,
        language_hints=["en"],
        disfluency_removal_enabled=True,   # removes filler words like "um", "uh"
        callback=callback
    )
    recognition.start()
    return recognition
```

### FastAPI WebSocket Endpoint
```python
# backend/stage1/audio_handler.py
import asyncio
from fastapi import WebSocket
from .asr_client import create_recognition_session

# In-memory session store (replace with Redis for production)
sessions = {}

async def handle_audio_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    transcript = []
    speaker_map = {}  # maps speaker_id int → "Therapist" / "Patient"

    # Thread-safe queue: DashScope callbacks run on a non-asyncio thread,
    # so we use call_soon_threadsafe to bridge into the event loop.
    loop = asyncio.get_running_loop()
    utterance_queue = asyncio.Queue()

    def on_utterance(text: str, speaker_id: int):
        if speaker_id not in speaker_map:
            speaker_map[speaker_id] = "Therapist" if len(speaker_map) == 0 else "Patient"

        label = speaker_map[speaker_id]
        utterance = {"speaker": label, "text": text, "speaker_id": speaker_id}
        transcript.append(utterance)
        loop.call_soon_threadsafe(utterance_queue.put_nowait, utterance)

    recognition = create_recognition_session(on_utterance)
    started = True
    sessions[session_id] = {"recognition": recognition, "transcript": transcript}

    async def drain_queue():
        while True:
            utterance = await utterance_queue.get()
            try:
                await websocket.send_json(utterance)
            except Exception:
                break

    drain_task = asyncio.create_task(drain_queue())

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            recognition.send_audio_frame(audio_chunk)
    except Exception:
        pass
    finally:
        drain_task.cancel()
        if started:
            try:
                recognition.stop()
            except Exception:
                pass
        sessions[session_id]["complete"] = True
```

### Browser-Side Audio Capture (JavaScript)
```javascript
// frontend/src/hooks/useAudioStream.js

// Resample audio from sourceRate to targetRate (16000 Hz for DashScope)
function resampleAudio(float32Data, sourceRate, targetRate) {
  if (sourceRate === targetRate) return float32Data;
  const ratio = sourceRate / targetRate;
  const newLength = Math.round(float32Data.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio;
    const srcIndexFloor = Math.floor(srcIndex);
    const srcIndexCeil = Math.min(srcIndexFloor + 1, float32Data.length - 1);
    const frac = srcIndex - srcIndexFloor;
    result[i] = float32Data[srcIndexFloor] * (1 - frac) + float32Data[srcIndexCeil] * frac;
  }
  return result;
}

const TARGET_SAMPLE_RATE = 16000;

export function useAudioStream(sessionId, onUtterance) {
  let mediaStream, audioContext, processor, ws;

  async function startSession() {
    // 1. Open WebSocket to backend
    ws = new WebSocket(`ws://localhost:8000/audio-stream/${sessionId}`);
    ws.onmessage = (event) => {
      const utterance = JSON.parse(event.data);
      onUtterance(utterance); // { speaker, text }
    };

    // 2. Capture microphone audio
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
    const actualRate = audioContext.sampleRate; // browsers may ignore the requested rate

    const source = audioContext.createMediaStreamSource(mediaStream);

    // 3. Process audio into PCM chunks and stream to server
    processor = audioContext.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (event) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      const float32 = event.inputBuffer.getChannelData(0);

      // Resample if browser gave us a different sample rate
      const resampled = resampleAudio(float32, actualRate, TARGET_SAMPLE_RATE);

      // Convert Float32 to Int16 PCM (DashScope expects PCM)
      const int16 = new Int16Array(resampled.length);
      for (let i = 0; i < resampled.length; i++) {
        int16[i] = Math.max(-0x7FFF, Math.min(0x7FFF, resampled[i] * 0x7FFF));
      }
      ws.send(int16.buffer);
    };

    source.connect(processor);
    processor.connect(audioContext.destination);
  }

  function stopSession() {
    processor?.disconnect();
    audioContext?.close();
    mediaStream?.getTracks().forEach(t => t.stop());
    ws?.close();
  }

  return { startSession, stopSession };
}
```

---

## 4b. Stage 1 — File-Based Transcription (Upload)

> [!IMPORTANT]
> **Use file upload as the primary demo path.** DashScope's file-based transcription has more reliable speaker diarization than the real-time streaming API. For the hackathon demo, uploading a pre-recorded audio file is also more deterministic and repeatable than live microphone capture.

```python
# backend/stage1/file_transcriber.py
import os
import json
import time
import dashscope
from dashscope.audio.asr import Transcription
from dotenv import load_dotenv

load_dotenv()

def transcribe_audio_file(file_path: str) -> dict:
    """
    Transcribe an uploaded audio file using DashScope's file-based API.
    Returns a transcript with speaker-labeled utterances.
    
    File-based transcription supports speaker diarization more reliably
    than the real-time streaming API.
    """
    # Submit transcription task
    task_response = Transcription.async_call(
        model="paraformer-v2",
        file_urls=[file_path],
        language_hints=["en"],
        diarization_enabled=True,
    )

    # Poll for completion (file transcription is async)
    result = Transcription.wait(task_response.output.task_id)

    if result.status_code != 200:
        raise RuntimeError(f"Transcription failed: {result.message}")

    # Parse the transcription result
    transcription_url = result.output.get("results", [{}])[0].get("transcription_url")
    # Fetch and parse the JSON result from the URL
    # (DashScope returns a URL pointing to the transcription output)
    import urllib.request
    with urllib.request.urlopen(transcription_url) as resp:
        transcription_data = json.loads(resp.read())

    return _format_transcript(transcription_data)


def _format_transcript(raw_data: dict) -> dict:
    """Convert DashScope file transcription output to our shared Transcript schema."""
    utterances = []
    paragraphs = raw_data.get("transcripts", [{}])[0].get("paragraphs", [])

    for para in paragraphs:
        speaker_id = para.get("speaker_id", 0)
        text = "".join(w.get("text", "") for w in para.get("words", []))
        words = para.get("words", [])
        start_time = _ms_to_timestamp(words[0].get("start_time", 0)) if words else None
        end_time = _ms_to_timestamp(words[-1].get("end_time", 0)) if words else None

        utterances.append({
            "speaker_id": speaker_id,
            "text": text.strip(),
            "start_time": start_time,
            "end_time": end_time,
        })

    return {"utterances": utterances}


def _ms_to_timestamp(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS format."""
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
```

---

## 5. Stage 2 — Qwen Recommendation Generator

Only call Qwen when a gap has already been confirmed by the keyword scanner.

```python
# backend/stage2/llm_client.py
import os
from dashscope import Generation
from dotenv import load_dotenv

load_dotenv()

# Static fallback recommendations — used when LLM call fails or times out.
FALLBACK_RECOMMENDATIONS = {
    "suicidality": (
        "I want to make sure I understand what you're going through. "
        "Are you having thoughts of ending your life? I'd like us to talk "
        "through that together and make sure you're safe."
    ),
    "duty_to_warn": (
        "I take what you're saying very seriously. I have a legal obligation "
        "to ensure everyone's safety, and I may need to take steps to protect "
        "the person you mentioned. Can you tell me more about what you're planning?"
    ),
    "mandatory_reporting": (
        "Thank you for trusting me with this. I want you to know that as a "
        "mandated reporter, I'm required to report this to the appropriate "
        "authorities to ensure your safety. I'll walk you through what that means."
    ),
    "crisis_resources": (
        "I want to make sure you have support available right now. "
        "The 988 Suicide and Crisis Lifeline is available 24/7 — you can "
        "call or text 988. Do you have someone you trust that you could reach out to?"
    ),
    "informed_consent": (
        "Before we continue, I want to make sure you understand how "
        "confidentiality works here. Everything we discuss is private, with "
        "a few legal exceptions — like if there's risk of harm to yourself or "
        "others. Let me explain those in full."
    ),
}

def generate_recommendation(category: str, patient_quote: str) -> str:
    """
    Given a confirmed liability gap, generate what the therapist should have said.
    This is the ONLY place Qwen is called in Stage 2.
    Falls back to a static recommendation if the LLM call fails.
    """
    prompt = f"""A therapy patient said: "{patient_quote}"

The therapist failed to respond appropriately for: {category}.

Write a specific example of what the therapist should have said at that moment.
Use a natural, empathetic, clinical tone. Maximum 3 sentences.
Do not explain why — just write the example response."""

    try:
        response = Generation.call(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            model="qwen-max",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in clinical therapy practice and therapist liability standards."
                },
                {"role": "user", "content": prompt}
            ],
            result_format="message",
            max_tokens=200,
            timeout=15,
        )
        return response.output.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM] Recommendation generation failed ({e}), using fallback.")
        return FALLBACK_RECOMMENDATIONS.get(category, FALLBACK_RECOMMENDATIONS["suicidality"])


async def generate_recommendations_batch(flags: list) -> list:
    """
    Generate recommendations for multiple flags concurrently.
    Call this from the audit engine instead of looping sequentially.
    """
    import asyncio

    async def gen_one(flag):
        loop = asyncio.get_event_loop()
        rec = await loop.run_in_executor(
            None, generate_recommendation, flag["category"], flag["patient_quote"]
        )
        flag["what_should_have_been_said"] = rec
        return flag

    return await asyncio.gather(*[gen_one(f) for f in flags])
```

---

## 6. Shared Transcript Schema

Both Stage 1 and Stage 2 import this. **Lock it on Day 1.**

```python
# backend/shared/transcript_schema.py
from pydantic import BaseModel
from typing import List, Optional

class Utterance(BaseModel):
    speaker: str          # "Therapist" or "Patient"
    text: str
    start_time: Optional[str] = None   # "00:01:23" format
    end_time: Optional[str] = None     # "00:01:28" format
    speaker_id: Optional[int] = None   # raw DashScope speaker_id

class Transcript(BaseModel):
    session_id: str
    audio_file: Optional[str] = None
    utterances: List[Utterance]

class LiabilityFlag(BaseModel):
    category: str
    severity: str         # "HIGH", "MEDIUM", "LOW"
    patient_quote: str
    detection_method: str # e.g. "keyword_match: 'better off without me'"
    what_was_missed: str
    what_should_have_been_said: str
    utterance_index: int  # index in transcript.utterances
    timestamp: Optional[str] = None  # start_time of the triggering utterance

class LiabilityReport(BaseModel):
    session_id: str
    overall_risk_score: int   # 0-100
    risk_level: str           # "HIGH", "MEDIUM", "LOW", "NONE"
    flags: List[LiabilityFlag]
```

---

## 7. FastAPI Main App

```python
# backend/main.py
import os
import uuid
import shutil
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from stage1.audio_handler import handle_audio_stream
from stage1.file_transcriber import transcribe_audio_file
from stage2.audit_engine import analyze_transcript
from shared.transcript_schema import Transcript

app = FastAPI(title="CareGuard AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a"}
UPLOAD_DIR = "uploads"

@app.websocket("/audio-stream/{session_id}")
async def audio_stream(websocket: WebSocket, session_id: str):
    await handle_audio_stream(websocket, session_id)

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Upload an audio file for transcription. Primary path for the hackathon demo."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"error": f"Unsupported format: {ext}. Use MP3, WAV, or M4A."}

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    session_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}{ext}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    transcript_data = transcribe_audio_file(file_path)
    transcript_data["session_id"] = session_id
    transcript_data["audio_file"] = file.filename
    return transcript_data

@app.post("/analyze")
async def analyze(transcript: Transcript):
    report = analyze_transcript(transcript)
    return report

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Run with:
```bash
uvicorn backend.main:app --reload --port 8000
```

---

## 8. Quick Reference — Common Errors

| Error | Cause | Fix |
|---|---|---|
| `AuthenticationError` | Bad API key | Check `.env` file, re-paste key |
| `ModuleNotFoundError: dashscope` | Not installed | `pip install dashscope` |
| `ConnectionRefusedError` on WebSocket | FastAPI not running | Run `uvicorn backend.main:app --reload` |
| `CORS error` in browser | CORS not configured or Vite on unexpected port | Check `allow_origins` in `main.py` matches your frontend port. If Vite falls back to 5174 when 5173 is busy, update CORS or kill the process holding 5173 |
| ASR returns no `speaker_id` in streaming mode | Real-time ASR may not support diarization | **Spike this Day 1.** Use file-based transcription (`/transcribe`) instead, which has reliable diarization. If streaming is required, fall back to alternating-turn heuristic |
| Transcript is garbled / chipmunk speed | Browser sample rate mismatch | Check `audioContext.sampleRate` in browser console — if it's 44100 or 48000, the resampler in `useAudioStream.js` handles it. If not resampling, verify the updated hook is deployed |
| Qwen returns empty response | Token limit hit or content filter | Reduce `max_tokens` or shorten prompt. Check DashScope console for content filter violations |
| Browser mic not working | Permissions blocked | Check browser mic permissions — must be on `localhost` or HTTPS |
| `RuntimeError: no running event loop` | ASR callback on non-asyncio thread | Use the `call_soon_threadsafe` + `asyncio.Queue` pattern in `audio_handler.py` (see section 4) |
| `422 Unprocessable Entity` on `/transcribe` | Unsupported audio format or missing `python-multipart` | Ensure file is MP3, WAV, or M4A. Run `pip install python-multipart` |

---

## 9. Useful Links
- DashScope console & API key: [https://dashscope.aliyuncs.com](https://dashscope.aliyuncs.com)
- DashScope Python SDK docs: [https://help.aliyun.com/zh/dashscope/](https://help.aliyun.com/zh/dashscope/)
- Qwen model list: [https://help.aliyun.com/zh/dashscope/developer-reference/model-introduction](https://help.aliyun.com/zh/dashscope/developer-reference/model-introduction)
- FastAPI docs: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- Vite + React setup: [https://vitejs.dev/guide/](https://vitejs.dev/guide/)
