# ClassCast — Two-Laptop Demo Setup

> **Teacher laptop** runs the backend (Python server) and the instructor control page.
> **Student laptop** opens the student view in a browser — nothing else needed.

Both laptops must be on the **same Wi-Fi network**.

---

## Step 0 — Find the teacher laptop's local IP

On the **teacher laptop**, open Terminal and run:

```bash
ipconfig getifaddr en0
```

You will get something like `192.168.1.42`.  
Write it down — you need it for Step 4.

---

## Step 1 — Install Python 3.11+ (teacher laptop only)

Check if you already have it:

```bash
python3 --version
```

If it shows `Python 3.11.x` or newer, skip this step.  
Otherwise, download from https://python.org/downloads and install.

---

## Step 2 — Get a Gemini API key (teacher laptop only)

1. Go to https://aistudio.google.com/apikey
2. Click **Create API key**
3. Copy it — you will paste it in Step 3.

---

## Step 3 — Start the backend (teacher laptop)

Open Terminal, then run these commands **one at a time**:

```bash
# 1. Go into the backend folder
cd /Applications/Projects-Claudcode/ClassCast/classcast/backend

# 2. Create a Python virtual environment
python3 -m venv .venv

# 3. Activate it
source .venv/bin/activate

# 4. Install all dependencies (takes 1-3 minutes first time)
pip install -r requirements.txt

# 5. Create your .env file from the template
cp .env.example .env
```

Now **open `.env` in any text editor** and fill in your Gemini key:

```
GEMINI_API_KEY=paste_your_key_here
```

Save the file, then start the server:

```bash
# 6. Start the server (keep this terminal open)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ The backend is running. **Do not close this terminal.**

---

## Step 4 — Edit the student frontend to point to the teacher laptop

On the **teacher laptop**, open this file in a text editor:

```
/Applications/Projects-Claudcode/ClassCast/classcast/frontend/index.html
```

Find this line (near the bottom, inside `<script>`):

```js
const BACKEND_URL = 'http://localhost:8000';
```

Change it to use the teacher laptop's IP you found in Step 0:

```js
const BACKEND_URL = 'http://192.168.1.42:8000';   // ← use YOUR IP
```

Save the file.

---

## Step 5 — Serve the frontend (teacher laptop)

Open a **second Terminal tab** and run:

```bash
cd /Applications/Projects-Claudcode/ClassCast/classcast/frontend
python3 -m http.server 5500
```

Leave this running too.

---

## Step 6 — Open the instructor page (teacher laptop)

On the **teacher laptop**, open Chrome or Safari and go to:

```
http://localhost:5500/instructor.html
```

You should see:
- **Upload pre-recorded audio** panel
- **Live microphone** panel

---

## Step 7 — Open the student page (student laptop)

On the **student laptop**, open Chrome or Safari and go to:

```
http://192.168.1.42:5500/index.html
```

Replace `192.168.1.42` with the teacher laptop's actual IP.

You should see "Student view" with a green **Connected** badge and the heartbeat ticking every 2 seconds.

---

## Step 8 — Do the demo

### Option A — Live mic (recommended for demo)

1. On the **teacher laptop** instructor page, click **Start mic**
2. Speak into the microphone — explain a concept clearly (e.g. "Newton's third law states that for every action there is an equal and opposite reaction.")
3. After ~5 seconds of speech the pipeline fires:
   - ~300ms later → the **student laptop** shows a text summary
   - ~2-3s later → an animated HTML visual appears

4. Click **Stop mic** when done.

### Option B — Upload a pre-recorded WAV

1. Drop a WAV lecture recording into `classcast/recordings/`
2. On the **teacher laptop** instructor page, click **Choose file** → select the WAV
3. Click **Upload & transcribe**
4. Watch the **student laptop** page update automatically

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Student page shows "Disconnected" | Make sure both laptops are on the same Wi-Fi. Double-check the IP in `index.html`. |
| "Whisper pre-warm skipped" in server log | Ignored — Whisper loads on first audio chunk. |
| Upload says "Upload failed" | The server may not be running. Check the backend terminal. |
| Mic button says "Mic error" | Chrome requires HTTPS for mic on non-localhost. Use the file upload option instead, OR open the instructor page via `http://localhost:5500/instructor.html` on the same machine as the server. |
| Events appear in the log but no visual | Check that `GEMINI_API_KEY` is set in `.env` and the model name is valid. |
| Port 8000 or 5500 already in use | Change the port: `uvicorn ... --port 8001` and `python3 -m http.server 5501`, then update the URLs accordingly. |

---

## Quick-reference URLs

| URL | What it is |
|---|---|
| `http://localhost:8000/health` | Backend health check (open on teacher laptop) |
| `http://localhost:5500/instructor.html` | Instructor controls (teacher laptop) |
| `http://<TEACHER_IP>:5500/` | Student view (student laptop) |
| `http://<TEACHER_IP>:5500/instructor.html` | Also works from student laptop (for testing) |
