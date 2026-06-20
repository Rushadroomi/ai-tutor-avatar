# AI Tutor Avatar — Chloe

A 3D avatar that takes text or voice input and responds with natural
conversation, speech, and accurate real-time lip sync — fully self-hosted,
with no Microsoft Azure or other cloud lip-sync/avatar services involved.

![Status](https://img.shields.io/badge/status-active%20development-yellow)

---

## Features

- **Text or voice input** — type a message or just talk
- **Live Conversation Mode** — continuous listening with automatic speech
  detection, no push-to-talk required
- **Interrupt / barge-in** — talk over Chloe mid-sentence and she stops
  immediately to listen
- **On-screen transcript** — full conversation shown as chat bubbles
- **Real-time lip sync** — phoneme-accurate mouth movement driven by
  custom-built viseme blend shapes on a rigged GLB avatar
- **AI tutor personality** — concise, conversational responses tuned for
  speech rather than walls of text
- **Zero paid cloud dependencies** — every component runs locally or on a
  free tier

---

## Architecture

```
┌─────────────┐     text/audio      ┌──────────────┐
│   Browser    │ ──────────────────▶│   FastAPI     │
│  (Three.js)  │                     │   Backend     │
│              │◀──── audio + ───────│               │
│  3D Avatar   │     viseme JSON     │               │
└─────────────┘                     └───────┬───────┘
                                             │
                  ┌──────────────┬───────────┼───────────┬──────────────┐
                  ▼              ▼           ▼           ▼              
            ┌──────────┐  ┌───────────┐ ┌─────────┐ ┌────────────┐
            │  Piper   │  │  Rhubarb  │ │ faster- │ │ OpenRouter │
            │  (TTS)   │  │(lip sync) │ │ whisper │ │   (LLM)    │
            │  local   │  │  local    │ │ (STT)   │ │ free tier  │
            └──────────┘  └───────────┘ └─────────┘ └────────────┘
```

| Layer | Technology | Notes |
|---|---|---|
| 3D rendering | Three.js (r128) | GLTFLoader, morph-target driven lip sync |
| Text-to-speech | [Piper](https://github.com/rhasspy/piper) | Local, offline, neural voice |
| Lip sync timing | [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync) | Phoneme → viseme cue extraction |
| Speech-to-text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Local, offline, runs on CPU |
| Conversational AI | [OpenRouter](https://openrouter.ai) free-tier models | Multi-model fallback chain |
| Backend | FastAPI | Python, async |
| Avatar rigging | Blender (Python scripting) | Custom viseme shape keys hand-fitted to mesh |

---

## Project structure

```
avatar-project/
├── backend/
│   ├── main.py              # FastAPI app — /speak /transcribe /chat
│   ├── requirements.txt
│   ├── .env.example          # template — copy to .env and add your key
│   ├── rhubarb/               # NOT in repo — download separately, see below
│   ├── voices/                 # NOT in repo — download separately, see below
│   └── outputs/                  # generated at runtime, gitignored
├── frontend/
│   ├── index.html             # full app — scene, UI, conversation logic
│   └── avatar.glb              # NOT in repo — custom asset, keep your own backup
├── add_visemes.py             # Blender script — generates viseme shape keys on the avatar mesh
├── README.md
└── .gitignore
```

---

## Required assets (not included in this repo)

These are excluded from version control deliberately — see *Why these aren't committed* below.

1. **Rhubarb Lip Sync**
   Download from: https://github.com/DanielSWolf/rhubarb-lip-sync/releases
   Get `Rhubarb-Lip-Sync-1.13.0-Windows.zip` (or latest), extract it, and
   place the contents into `backend/rhubarb/` so that
   `backend/rhubarb/rhubarb.exe` exists.

2. **Piper voice model**
   Download both files from:
   https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/medium
   - `en_US-lessac-medium.onnx`
   - `en_US-lessac-medium.onnx.json`
   Place both into `backend/voices/`.

3. **Avatar GLB** (`frontend/avatar.glb`)
   This is a custom-rigged asset — the base model was sourced, then
   processed through a custom Blender pipeline (`add_visemes.py`) to add
   hand-fitted viseme blend shapes aligned to this specific mesh's geometry.
   It is **not** publicly re-downloadable as-is.
   **Keep your own backup of this file** (Drive, USB, etc.) — if it's lost,
   the viseme-fitting process in `add_visemes.py` would need to be redone
   from scratch against a new base mesh.

### Why these aren't committed
Rhubarb and the Piper voice model are large, freely re-downloadable
third-party binaries — committing them would bloat the repo and slow every
clone for no benefit. The avatar GLB is large and unique to this project,
but git is the wrong tool for long-term binary asset storage (no diffing,
repo grows forever); it's excluded here and should be backed up separately
by whoever owns the asset.

---

## Setup

### 1. Backend

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Get a free API key from https://openrouter.ai/keys, then:

```cmd
copy .env.example .env
```

Edit `.env` and paste your key:

```
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
```

Download and place the required assets (see section above), then start the server:

```cmd
uvicorn main:app --reload
```

First run downloads the Whisper model automatically (~150MB, one-time).
Server runs at `http://127.0.0.1:8000`.

### 2. Frontend

```cmd
cd frontend
python -m http.server 3000
```

Open **http://localhost:3000** in your browser.

---

## Usage

- **Type + Speak** — enter text, click Speak (or press Enter)
- **Hold-to-talk mic button** — hold, speak, release
- **Live Conversation Mode** — click "Start Live Conversation" for hands-free,
  continuous back-and-forth conversation with automatic interrupt support

> **Note:** Live Mode uses your microphone continuously to detect speech.
> For the cleanest experience (avoiding the mic picking up Chloe's own
> voice through your speakers), **headphones are recommended**.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | Free key from https://openrouter.ai/keys, used for the conversational AI brain |

---

## Roadmap — production checklist

| Area | Status | Notes |
|---|---|---|
| Secrets management | ✅ Done | `.env` excluded from git, `.env.example` provided |
| Core pipeline (TTS → lip sync → STT → LLM) | ✅ Done | Full loop working end-to-end |
| Live conversation mode | ✅ Done | VAD-based auto turn-taking + interrupt |
| Error handling | 🚧 In progress | Graceful fallback if Piper/Rhubarb/Whisper/OpenRouter fail mid-request |
| Rate limiting | ⬜ Planned | Protect endpoints from abuse |
| Input sanitization | ⬜ Planned | Harden `/chat` and `/transcribe` against malformed input |
| Performance tuning | ⬜ Planned | Whisper model size tradeoffs, response caching |
| Deployment | ⬜ Planned | Dockerize backend, host (Render/Railway/VPS), frontend on Vercel/Netlify |
| Automated tests | ⬜ Planned | Coverage for FastAPI endpoints |
| Responsive layout | ⬜ Planned | Current UI is fixed-width, needs mobile support |
| Voice selection UI | ⬜ Planned | Let users pick from multiple Piper voices |
| Loading/error UX polish | ⬜ Planned | User-facing messages instead of raw errors |

---

## License

Add your chosen license here (e.g., MIT) before making this repo public.

## Status

🚧 Active development — see commit history for daily progress.
