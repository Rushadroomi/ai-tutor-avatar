import subprocess
import os
import json
import uuid
import asyncio
from functools import partial
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from piper.voice import PiperVoice
from faster_whisper import WhisperModel
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
BACKEND_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
MODEL_PATH      = os.getenv("PIPER_MODEL", "voices/en_US-lessac-medium.onnx")
RHUBARB         = os.getenv("RHUBARB_EXE", r"rhubarb\rhubarb.exe")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

TUTOR_SYSTEM_PROMPT = (
    "You are Chloe, a friendly and knowledgeable AI tutor. "
    "Keep answers conversational and concise — 2 to 4 sentences unless the "
    "user asks for more detail. Speak naturally, like you're talking out "
    "loud to a student, not writing an essay. Avoid markdown formatting, "
    "bullet points, or asterisks since your replies are converted to speech."
)

FALLBACK_MODELS = [
    OPENROUTER_MODEL,
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "google/gemma-3-12b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "openrouter/free",
]

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Chloe Avatar Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=BACKEND_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Heavy models loaded once at startup ──────────────────────────────────────
print("Loading Piper TTS voice...")
voice = PiperVoice.load(MODEL_PATH)
print("Piper ready.")

print("Loading Whisper STT model (first run ~150 MB download)...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
print("Whisper ready.")

os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


# ── Helpers (blocking — run via executor so async loop is not blocked) ────────
def _synthesize_blocking(text: str, wav_path: str) -> subprocess.CompletedProcess:
    """
    Run Piper TTS in a subprocess.
    Must be called via run_in_executor — NOT called directly from async code.
    """
    piper_exe  = os.path.join("venv", "Scripts", "piper.exe")
    model_path = os.path.abspath(MODEL_PATH)
    return subprocess.run(
        [piper_exe, "--model", model_path, "--output_file", wav_path],
        input=text,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _rhubarb_blocking(wav_path: str, json_path: str) -> subprocess.CompletedProcess:
    """
    Run Rhubarb lip-sync in a subprocess.
    Must be called via run_in_executor — NOT called directly from async code.
    """
    return subprocess.run(
        [os.path.abspath(RHUBARB), "-f", "json", "-o", json_path, wav_path],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _transcribe_blocking(audio_path: str) -> str:
    """
    Run faster-whisper transcription.
    Must be called via run_in_executor — NOT called directly from async code.
    """
    segments, _ = whisper_model.transcribe(audio_path, language="en")
    return " ".join(seg.text.strip() for seg in segments).strip()


async def run_blocking(fn, *args):
    """Run a blocking function in the default thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(fn, *args))


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post("/speak")
async def speak(request: Request):
    """
    Text → WAV audio + Rhubarb viseme timing JSON.
    Each request uses a unique temp filename to prevent concurrent-request collisions.
    """
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)
    if len(text) > 4000:
        return JSONResponse({"error": "Text too long (max 4000 chars)"}, status_code=400)

    req_id    = uuid.uuid4().hex[:8]
    wav_path  = os.path.abspath(os.path.join("outputs", f"speech_{req_id}.wav"))
    json_path = os.path.abspath(os.path.join("outputs", f"visemes_{req_id}.json"))

    try:
        # ── TTS (non-blocking) ──
        tts_result = await run_blocking(_synthesize_blocking, text, wav_path)
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
            return JSONResponse(
                {"error": "TTS failed", "details": tts_result.stderr[:500]},
                status_code=500,
            )

        # ── Rhubarb visemes (non-blocking) ──
        rhubarb_result = await run_blocking(_rhubarb_blocking, wav_path, json_path)
        if rhubarb_result.returncode != 0:
            return JSONResponse(
                {"error": "Rhubarb failed", "details": rhubarb_result.stderr[:500]},
                status_code=500,
            )

        with open(json_path, "r") as f:
            viseme_data = json.load(f)

        return {
            "audio_url": f"/outputs/speech_{req_id}.wav",
            "visemes":   viseme_data["mouthCues"],
        }

    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "Processing timed out"}, status_code=504)
    finally:
        # Clean up temp Rhubarb JSON (WAV is served statically so keep it briefly)
        if os.path.exists(json_path):
            try:
                os.remove(json_path)
            except OSError:
                pass


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """WebM audio blob (from browser mic) → transcribed text."""
    if audio.size and audio.size > 10 * 1024 * 1024:  # 10 MB guard
        return JSONResponse({"error": "Audio file too large"}, status_code=413)

    req_id   = uuid.uuid4().hex[:8]
    raw_path = os.path.join("outputs", f"mic_{req_id}.webm")

    try:
        data = await audio.read()
        if not data:
            return JSONResponse({"error": "Empty audio file"}, status_code=400)

        with open(raw_path, "wb") as f:
            f.write(data)

        text = await run_blocking(_transcribe_blocking, raw_path)
        return {"text": text}

    except Exception as e:
        return JSONResponse({"error": f"Transcription error: {str(e)}"}, status_code=500)
    finally:
        if os.path.exists(raw_path):
            try:
                os.remove(raw_path)
            except OSError:
                pass


@app.post("/chat")
async def chat(request: Request):
    """User message + history → AI reply from OpenRouter LLM with fallback chain."""
    body = await request.json()
    user_message = (body.get("message") or "").strip()
    history      = body.get("history", [])

    if not user_message:
        return JSONResponse({"error": "No message provided"}, status_code=400)
    if not OPENROUTER_API_KEY:
        return JSONResponse(
            {"error": "OPENROUTER_API_KEY not set in server .env"},
            status_code=500,
        )

    # Enforce server-side context window cap (20 turns = 40 messages)
    history = history[-20:]

    messages = [{"role": "system", "content": TUTOR_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    async with httpx.AsyncClient(timeout=30.0) as client:
        last_error = None
        for model_name in FALLBACK_MODELS:
            try:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type":  "application/json",
                    },
                    json={"model": model_name, "messages": messages},
                )
                if resp.status_code == 200:
                    data  = resp.json()
                    reply = data["choices"][0]["message"]["content"]
                    # Strip any markdown that leaked through despite the system prompt
                    reply = reply.replace("**", "").replace("*", "").replace("```", "")
                    return {"reply": reply, "model_used": model_name}
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except httpx.TimeoutException:
                last_error = f"Timeout on {model_name}"
                continue

    return JSONResponse(
        {"error": f"All models unavailable. Last error: {last_error}"},
        status_code=503,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "piper": True, "whisper": True}


@app.get("/")
async def root():
    return {"status": "Chloe Avatar backend running"}