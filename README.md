# MeetMind

**A consent-first AI meeting assistant that turns conversations into searchable knowledge and accountable action.**

MeetMind accepts a consented meeting recording, transcribes it locally with faster-whisper, sends the transcript to Google Gemini for structured analysis, and creates English or Hindi read-aloud audio with Kokoro. Meetings, tasks, consent records, and generated files remain organized in one responsive web application.

## What MeetMind does

- Uploads MP3, WAV, M4A, MP4, and WebM meeting recordings
- Requires host confirmation that participants consented to recording and processing
- Transcribes English, Hindi, Hinglish, and other supported languages locally
- Generates concise summaries, key points, decisions, and action items with Gemini
- Extracts owners, due dates, priorities, and source quotes for tasks
- Reads meeting summaries aloud with local Kokoro voices
- Searches meeting titles, summaries, and transcripts
- Tracks open and completed action items
- Stores application data locally in SQLite
- Includes a demo meeting, so the interface works before AI services are configured
- Adapts to desktop, tablet, and mobile screens

## Processing flow

```text
Participant consent
        ↓
Upload meeting audio
        ↓
faster-whisper transcription
        ↓
Google Gemini analysis
        ↓
Summary · Decisions · Key points · Action items
        ↓
Kokoro read-aloud audio
```

## Technology

| Area | Technology |
| --- | --- |
| Web API | FastAPI and Uvicorn |
| Frontend | HTML, CSS, and JavaScript |
| Database | SQLite |
| Speech-to-text | faster-whisper |
| Meeting analysis | Google Gemini API |
| Text-to-speech | Kokoro |
| Container runtime | Python 3.12, ffmpeg, eSpeak NG, and libsndfile |

## Requirements

### Full AI experience

- Python 3.11 or 3.12
- A Google Gemini API key
- Internet access during the first model download
- Several gigabytes of free disk space for Python and model files
- ffmpeg available on the system, or Docker

### Demo experience

- Python 3.13 or newer is supported by the lightweight setup
- The included demo meeting, dashboard, search, tasks, and consent views remain available

Python 3.11 or 3.12 provides the widest compatibility with faster-whisper, Kokoro, PyTorch, and their native dependencies.

## Quick start on Windows

### Command Prompt

```cmd
cd /d "C:\Users\Siddhi Joshi\Documents\projects\MeetMind"
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

### PowerShell

```powershell
cd "C:\Users\Siddhi Joshi\Documents\projects\MeetMind"
.\run.ps1
```

The startup script creates a virtual environment, installs the appropriate dependencies, and starts the development server.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) after Uvicorn reports that the server is running. Keep the terminal open while using the application. Press `Ctrl+C` to stop it.

### Select a Python 3.12 installation

```powershell
.\run.ps1 -PythonPath "C:\path\to\Python312\python.exe"
```

The script uses `.venv-full` for Python 3.11/3.12 and `.venv` for the lightweight runtime. This keeps both environments independent.

## Configure Gemini

The repository includes a local `.env` file and a safe template in `.env.example`.

1. Open `.env`.
2. Paste your key after `GEMINI_API_KEY=`.
3. Save the file.
4. Restart MeetMind.

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Never commit the `.env` file or share its contents.

## Manual installation

Use Python 3.11 or 3.12 for the complete installation.

```powershell
python -m venv .venv-full
.\.venv-full\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

For the dashboard and demo without local AI model packages:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lite.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Docker

Docker provides Python 3.12 and the native packages required by faster-whisper and Kokoro.

```cmd
copy .env.example .env
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). Application records and generated files persist through the mounted `data`, `uploads`, and `generated` directories. Downloaded AI models persist in the Docker volume named `model-cache`.

Stop the application with:

```cmd
docker compose down
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | Empty | Enables Gemini analysis for uploaded meetings |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model used for summaries and actions |
| `WHISPER_MODEL` | `small` | Local faster-whisper model size |
| `WHISPER_DEVICE` | `cpu` | Inference device, usually `cpu` or `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | Whisper compute type used to control speed and memory |
| `KOKORO_VOICE_EN` | `af_heart` | English read-aloud voice |
| `KOKORO_VOICE_HI` | `hf_alpha` | Hindi read-aloud voice |
| `MEETMIND_DATA_DIR` | `data` | SQLite database directory |
| `MEETMIND_UPLOAD_DIR` | `uploads` | Uploaded meeting recordings |
| `MEETMIND_GENERATED_DIR` | `generated` | Kokoro-generated audio files |

Larger Whisper models may improve accuracy while requiring more memory and processing time. The `small` model provides a practical CPU-friendly starting point.

## Project structure

```text
MeetMind/
├── app/
│   ├── main.py                 FastAPI routes and processing workflow
│   ├── config.py               Environment configuration
│   ├── database.py             SQLite schema and demo data
│   └── services/
│       ├── gemini.py           Gemini structured meeting analysis
│       ├── transcription.py    faster-whisper integration
│       └── tts.py              Kokoro audio generation
├── static/
│   ├── index.html              Application entry page
│   └── assets/
│       ├── app.js              Dashboard and meeting interactions
│       └── styles.css          Responsive visual design
├── data/                       Local database at runtime
├── uploads/                    Uploaded recordings at runtime
├── generated/                  Generated read-aloud files at runtime
├── .env.example                Configuration template
├── requirements.txt            Complete AI dependencies
├── requirements-lite.txt       Lightweight demo dependencies
├── run.ps1                     Windows startup helper
├── Dockerfile
└── docker-compose.yml
```

## Using MeetMind

1. Open **New meeting**.
2. Choose a meeting audio or video file.
3. Add a title, spoken language, and participant names.
4. Confirm that every participant agreed to recording and processing.
5. Select **Transcribe and summarize**.
6. Open the finished meeting to review its summary, transcript, decisions, actions, and consent log.
7. Select **Read aloud** to generate Kokoro audio for the summary.

The first transcription and read-aloud request can take longer because model files are downloaded and initialized.

## API

Interactive OpenAPI documentation is available while the server is running:

- Swagger UI at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- OpenAPI schema at [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check server and Gemini configuration status |
| `GET` | `/api/dashboard` | Load dashboard statistics and recent records |
| `GET` | `/api/meetings` | List or search meetings |
| `POST` | `/api/meetings` | Upload and process a consented meeting |
| `GET` | `/api/meetings/{id}` | Retrieve a meeting and its tasks |
| `POST` | `/api/meetings/{id}/read-aloud` | Generate Kokoro summary audio |
| `GET` | `/api/tasks` | List extracted action items |
| `PATCH` | `/api/tasks/{id}` | Update an action item's status |

## Local data and privacy

- Uploaded recordings are saved in `uploads/`.
- Generated Kokoro files are saved in `generated/`.
- Meetings, consent records, and tasks are stored in `data/meetmind.db`.
- faster-whisper and Kokoro process content locally after their models are downloaded.
- Meeting transcripts are sent to Google only when a Gemini API key is configured.
- The application does not place transcript content in application logs.
- Runtime records, recordings, generated audio, model caches, and secrets are excluded from Git.

Gemini service tiers have their own usage limits and data-handling terms. Review the terms for the selected tier before processing confidential or regulated meetings.

The current consent implementation records the host's attestation for listed participants. Production use should add signed participant consent links, identity controls, configurable retention, and legal review for the regions where the product operates.

## Troubleshooting

### MeetMind starts in demo mode

Add `GEMINI_API_KEY` to `.env` and restart the server. Python 3.13 or newer also selects the lightweight runtime. Use Python 3.11/3.12 or Docker for faster-whisper and Kokoro.

### `Kokoro is not installed`

Install `requirements.txt` in a Python 3.11/3.12 environment. Docker also installs Kokoro and its native dependencies.

### `faster-whisper is not installed`

The lightweight dependencies are active. Start MeetMind with Python 3.11/3.12 and install `requirements.txt`.

### ffmpeg or audio decoding errors

Install ffmpeg and ensure it is available on `PATH`, or use Docker. Converting unusual recordings to WAV, MP3, or WebM can also resolve decoding problems.

### Port 8000 is already in use

Stop the earlier server with `Ctrl+C`, or start on another port:

```powershell
python -m uvicorn app.main:app --port 8001
```

### Reset local demo data

Stop the server and remove `data/meetmind.db`. MeetMind recreates the database and demo meeting on the next start. Back up any records you want to keep before removing it.

## Current MVP boundaries

- Host-attested consent instead of signed participant consent links
- Uploaded recordings instead of a bot joining Google Meet
- Local single-workspace storage without authentication
- Background processing inside the application process
- Local task tracking without email, calendar, Jira, or Slack integrations

These boundaries keep the first release simple enough to test the core meeting-to-action workflow.

## Development checks

```powershell
python -m compileall -q app
node --check static\assets\app.js
```

When changing the interface, verify the dashboard, upload form, meeting tabs, task status controls, read-aloud state, and mobile layout.

