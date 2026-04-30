# recordings/

Drop test WAV files here. They must be:
- Format: WAV (PCM)
- Sample rate: any (backend resamples to 16kHz)
- Channels: mono or stereo (backend downmixes to mono)
- Length: any (backend processes in 5-second chunks)

To use:
1. Open the instructor page (http://localhost:5500/instructor.html)
2. Click "Choose file" → pick a WAV from this folder
3. Click "Upload & transcribe"
4. Watch the student view (http://localhost:5500) for events
