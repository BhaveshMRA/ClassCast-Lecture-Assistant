# ClassCast

> Real-time AI visual aid for live lectures.

ClassCast listens to a professor speak, transcribes the audio locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), identifies the key concept being taught, and instantly broadcasts an animated HTML visual + plain-English summary to every connected student — no app install, no account, just a browser tab.

It also supports direct PPTX/PDF slide uploads, generating real-time summaries and visuals for each slide bypassing the audio transcription phase.

### New Hackathon Features Added
- **Long-Context RAG**: Upload course syllabus/notes to ground AI outputs in the professor's exact terminology.
- **Persistent SQLite History**: Lecture events are securely saved locally (`classcast.db`), allowing students to refresh their browser without losing the visual timeline.
- **Student Notebook (Export/Import)**: Students can manually save concepts to a private sidebar notebook (via `localStorage`), view them in a modal, and **Export/Import** their notebook as a `.json` file for future study sessions.

---

## How it works

```
Instructor mic / WAV upload
         │
         ▼
  [faster-whisper]        ← runs locally, no cloud STT cost
         │ transcript chunks
         ▼
  [LangGraph pipeline] ◄── Instructor Slide Upload (PPTX/PDF)
                     ◄── Syllabus / Course Notes Upload (RAG Context)
    ├─ batch_accumulator  ← buffers 2-3 sentences
    ├─ concept_extractor  ← Gemini 2.5 Flash classifies: TECHNICAL / EXAMPLE / ADMIN / JOKE
    ├─ decision_router    ← skips jokes & admin; routes to summarize or visualize
    ├─ summary_generator  ← Gemini 2.5 Flash → plain-English summary (~300 ms)
    └─ visual_generator   ← Claude Haiku 4.5 → animated HTML snippet (~2-3 s)
         │ SSE events
         ▼
    [broadcaster] ───────► [SQLite classcast.db] ← Persistent history storage
         │ live feed              │
         ▼                        │ GET /history on load
  Student browsers ◄──────────────┘
  (Notebook uses localStorage)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Transcription | faster-whisper (CTranslate2, runs on CPU) |
| Pipeline | LangGraph + LangChain Core |
| AI (Speed) | Google Gemini 2.5 Flash via OpenRouter |
| AI (Code) | Anthropic Claude Haiku 4.5 via OpenRouter |
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
│       │   └── gemini.py            ← OpenRouter API client
│       ├── routes/
│       │   ├── stream.py            ← GET /stream  (SSE)
│       │   ├── audio.py             ← POST /ingest/audio  (WAV upload)
│       │   ├── slides.py            ← POST /ingest/slides (PPTX/PDF upload)
│       │   └── ws_audio.py          ← WS /ingest/ws  (live mic)
│       └── utils/
│           ├── audio.py             ← WAV decoding + PCM helpers
│           └── slides.py            ← PPTX/PDF text extraction
├── frontend/
│   ├── index.html                   ← student view (w/ live mic status)
│   └── instructor.html              ← instructor controls (w/ live AI transcript)
└── recordings/
    └── README.md                    ← drop test WAV/PPTX files here
```

---

## Quick start (single machine)

### 1. Get an OpenRouter API key

Go to https://openrouter.ai/keys → **Create Key** → copy it.

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
# Open .env and set: OPENROUTER_API_KEY=sk-or-your_key_here
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

Click **Start mic** on the instructor page and speak. You will see what the AI hears directly on your screen. Summaries and visuals will automatically appear on the student page within seconds.

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
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key |
| `OPENROUTER_FLASH_MODEL` | `google/gemini-2.5-flash` | Fast model for extraction & summaries |
| `OPENROUTER_PRO_MODEL` | `anthropic/claude-haiku-4.5` | Smart model for HTML visual generation |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` / `large` |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `BATCH_SENTENCE_COUNT` | `2` | Sentences to buffer before pipeline fires |
| `BATCH_TIMEOUT_SECONDS` | `8.0` | Max seconds to wait before force-flushing buffer |
| `CONCEPT_CONFIDENCE_THRESHOLD` | `0.5` | Min AI confidence to trigger a visual |

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/stream` | SSE stream — students connect here |
| `POST` | `/ingest/audio` | Upload a WAV file (multipart/form-data) |
| `POST` | `/ingest/slides` | Upload a PPTX or PDF file |
| `POST` | `/ingest/syllabus`| Upload Course Syllabus/Notes for RAG context |
| `WS` | `/ingest/ws` | Live mic stream (raw int16 PCM @ 16 kHz) |
| `GET` | `/history` | Fetch the 50 most recent broadcast events (SQLite) |
| `GET` | `/health` | Health check + connected client count |

---

## SSE event types

The student frontend listens for these named events:

| Event | Payload fields | When |
|---|---|---|
| `heartbeat` | `tick`, `timestamp`, `clients` | Every 2 seconds |
| `summary` | `concept`, `text`, `timestamp` | ~300 ms after concept detected |
| `visual` | `concept`, `html`, `timestamp` | ~2-3 s after concept detected |
| `transcript` | `text` | Raw live transcription chunk |
| `mic_status` | `status` | Updates green badge when prof connects |
| `audit` | `concept`, `concept_type`, `confidence`, `action`, `reason` | Every flushed batch |

---

## Running tests

```bash
cd classcast/backend
source .venv/bin/activate
pytest tests/ -v
```

Tests use mocked AI responses — **no API key required**.

---

## Architecture notes

- **SSE over WebSocket for students** — one-way push, native auto-reconnect, no library needed.
- **AudioWorklet + raw PCM** for live mic — avoids ffmpeg dependency on the server; the browser downsamples from 48 kHz to 16 kHz before sending.
- **Non-blocking Whisper** — Whisper transcription runs in an isolated background task, preventing WebSocket starvation and dropouts.
- **Two-phase render via `asyncio.gather`** — summary (Flash, ~300 ms) and visual (Haiku, ~2-3 s) run concurrently so students never see a blank screen.
- **Sandboxed iframe** for visuals — AI-generated HTML runs with `sandbox="allow-scripts"` so it can animate safely.

---

## Known limitations (hackathon scope)

- Single classroom only — no per-room isolation
- No authentication — open to anyone on the network
- No speaker diarization — assumes professor-only mic input

---

## License

MIT
