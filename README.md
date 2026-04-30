# ClassCast

> Real-time AI visual aid for live lectures.

ClassCast listens to a professor speak, transcribes the audio locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), identifies the key concept being taught, and instantly broadcasts an animated HTML visual + plain-English summary to every connected student — no app install, no account, just a browser tab.

---

## How it works

```
Instructor mic / WAV upload
         │
         ▼
  [faster-whisper]        ← runs locally, no cloud STT cost
         │ transcript chunks
         ▼
  [LangGraph pipeline]
    ├─ batch_accumulator  ← buffers 2-3 sentences
    ├─ concept_extractor  ← Gemini Flash classifies: TECHNICAL / EXAMPLE / ADMIN / JOKE
    ├─ decision_router    ← skips jokes & admin; routes to summarize or visualize
    ├─ summary_generator  ← Gemini Flash → plain-English summary (~300 ms)
    └─ visual_generator   ← Gemini Pro → animated HTML snippet (~2-3 s)
         │ SSE events
         ▼
  Student browsers        ← EventSource auto-reconnects; no WebSocket needed
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Transcription | faster-whisper (CTranslate2, runs on CPU) |
| Pipeline | LangGraph + LangChain Core |
| AI | Google Gemini Flash (fast path) + Gemini Pro (visuals) |
| Frontend | Vanilla HTML/JS — zero build step |
| Realtime | Server-Sent Events (SSE) |
| Mic capture | Web Audio API + AudioWorklet → raw PCM over WebSocket |

---

## Project structure

```
classcast/
├── README.md                        ← you are here
├── SETUP_TWO_LAPTOPS.md             ← two-laptop demo guide
├── backend/
│   ├── requirements.txt
│   ├── .env.example                 ← copy to .env and fill in your API key
│   ├── pyproject.toml
│   └── app/
│       ├── main.py                  ← FastAPI entry point
│       ├── config.py                ← all settings via pydantic-settings
│       ├── broadcaster.py           ← SSE pub/sub fan-out
│       ├── models.py                ← Pydantic event contracts
│       ├── pipeline/
│       │   ├── graph.py             ← LangGraph wiring
│       │   ├── state.py             ← PipelineState TypedDict
│       │   ├── batch_accumulator.py
│       │   ├── concept_extractor.py
│       │   ├── decision_router.py
│       │   ├── summary_generator.py
│       │   └── visual_generator.py
│       ├── services/
│       │   ├── whisper.py           ← faster-whisper singleton
│       │   └── gemini.py            ← Gemini Flash + Pro clients
│       ├── routes/
│       │   ├── stream.py            ← GET /stream  (SSE)
│       │   ├── audio.py             ← POST /ingest/audio  (WAV upload)
│       │   └── ws_audio.py          ← WS /ingest/ws  (live mic)
│       └── utils/
│           └── audio.py             ← WAV decoding + PCM helpers
├── frontend/
│   ├── index.html                   ← student view
│   └── instructor.html              ← instructor controls
└── recordings/
    └── README.md                    ← drop test WAV files here
```

---

## Quick start (single machine)

### 1. Get a Gemini API key

Go to https://aistudio.google.com/apikey → **Create API key** → copy it.

### 2. Start the backend

```bash
cd classcast/backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies (first run takes 1-3 min)
pip install -r requirements.txt

# Create your .env file and add your API key
cp .env.example .env
# Open .env and set: GEMINI_API_KEY=your_key_here

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 3. Serve the frontend

Open a second terminal tab:

```bash
cd classcast/frontend
python3 -m http.server 5500
```

### 4. Open the pages

| Who | URL |
|---|---|
| Instructor | http://localhost:5500/instructor.html |
| Student(s) | http://localhost:5500 |

Click **Start mic** on the instructor page and speak. Summaries and visuals appear on the student page within seconds.

---

## Two-laptop demo (teacher + student on different machines)

See **[SETUP_TWO_LAPTOPS.md](./SETUP_TWO_LAPTOPS.md)** for the full step-by-step guide.

TL;DR:
1. Backend runs on the **teacher laptop** with `--host 0.0.0.0`
2. Find the teacher laptop's LAN IP: `ipconfig getifaddr en0`
3. Edit `frontend/index.html` — change `BACKEND_URL` to `http://<TEACHER_IP>:8000`
4. Student opens `http://<TEACHER_IP>:5500` — nothing to install

---

## Environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Your Google AI Studio key |
| `GEMINI_FLASH_MODEL` | `gemini-2.0-flash-exp` | Model for fast paths (extraction, summary) |
| `GEMINI_PRO_MODEL` | `gemini-1.5-pro` | Model for visual HTML generation |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` / `large` |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `BATCH_SENTENCE_COUNT` | `2` | Sentences to buffer before pipeline fires |
| `BATCH_TIMEOUT_SECONDS` | `8.0` | Max seconds to wait before force-flushing buffer |
| `CONCEPT_CONFIDENCE_THRESHOLD` | `0.5` | Min Gemini confidence to trigger a visual |

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/stream` | SSE stream — students connect here |
| `POST` | `/ingest/audio` | Upload a WAV file (multipart/form-data) |
| `WS` | `/ingest/ws` | Live mic stream (raw int16 PCM @ 16 kHz) |
| `GET` | `/health` | Health check + connected client count |
| `POST` | `/test/publish` | Manually broadcast any JSON payload |

---

## SSE event types

The student frontend listens for these named events:

| Event | Payload fields | When |
|---|---|---|
| `heartbeat` | `tick`, `timestamp`, `clients` | Every 2 seconds |
| `summary` | `concept`, `text`, `timestamp` | ~300 ms after concept detected |
| `visual` | `concept`, `html`, `timestamp` | ~2-3 s after concept detected |
| `audit` | `concept`, `concept_type`, `confidence`, `action`, `reason` | Every flushed batch |

---

## Running tests

```bash
cd classcast/backend
source .venv/bin/activate
pytest tests/ -v
```

Tests use mocked Gemini responses — **no API key required**.

---

## Manual smoke test

With the backend running:

```bash
# 1. Confirm SSE works
curl -X POST localhost:8000/test/publish \
  -H "Content-Type: application/json" \
  -d '{"message": "hello from curl"}'
# → should instantly appear in every open student tab

# 2. Upload a test WAV
curl -F "file=@recordings/your_lecture.wav" localhost:8000/ingest/audio
# → watch backend logs + student tab for events
```

---

## Architecture notes

- **SSE over WebSocket for students** — one-way push, native auto-reconnect, no library needed.
- **AudioWorklet + raw PCM** for live mic — avoids ffmpeg dependency on the server; the browser downsamples from 48 kHz to 16 kHz before sending.
- **Singleton Whisper model** pre-warmed at startup via `lifespan` — first transcription is fast.
- **Two-phase render via `asyncio.gather`** — summary (Flash, ~300 ms) and visual (Pro, ~2-3 s) run concurrently so students never see a blank screen.
- **Sandboxed iframe** for visuals — Gemini-generated HTML runs with `sandbox="allow-scripts"` so it can animate but cannot access the parent page.
- **Module-level batch buffer** — single-room singleton, easy to key by `session_id` for multi-instructor later.

---

## Known limitations (hackathon scope)

- Single classroom only — no per-room isolation
- No authentication — open to anyone on the network
- No persistent storage — audit events are broadcast-only, in-memory
- No RAG — concept extractor uses Gemini only, not course materials
- No speaker diarization — assumes professor-only mic input

---

## License

MIT
