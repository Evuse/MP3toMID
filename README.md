# TuneMorph

TuneMorph is an open-source foundation for turning user-supplied audio into coherent,
style-aware MIDI arrangements. It deliberately targets recognisable musical
reinterpretation rather than promising perfect note-for-note transcription of arbitrary
polyphonic recordings.

The first two milestones establish the production-oriented monorepo, FastAPI service,
private UUID project storage, streamed and decoded audio uploads, replaceable audio-engine
contracts, responsive Next.js interface, tests, and Docker development environment. Audio
analysis and conversion are implemented in subsequent pipeline milestones rather than
represented here by fake progress or mock conversion.

## Repository layout

| Path | Purpose |
| --- | --- |
| `frontend/` | Next.js 16, React, strict TypeScript, Tailwind CSS |
| `backend/` | FastAPI application, configuration, REST API |
| `audio-engine/` | Independent Python package and DSP/model adapter contracts |
| `shared/` | Shared API documentation and future generated contracts |
| `tests/` | Cross-package and integration tests |
| `docker/` | Backend and frontend container definitions |
| `docs/` | Architecture and engineering decisions |

## Prerequisites

- Python 3.11+
- Node.js 20+
- `ffmpeg`/`ffprobe` (required now to validate MP3, M4A and FLAC; WAV uses a native decoder)
- Docker Compose (optional)

## Local development

```bash
cp .env.example .env
make setup
make backend
```

`make setup` creates `.venv` and installs both local Python packages in editable mode.
Using `make backend` deliberately invokes `.venv/bin/python -m uvicorn`, so macOS cannot
accidentally execute a globally installed `uvicorn` with the wrong interpreter.

On macOS, install the decoder used for MP3 validation once:

```bash
brew install ffmpeg
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>; API docs are at <http://localhost:8000/docs>.

## Docker

```bash
docker compose up --build
```

Copying `.env.example` to `.env` is optional; all development defaults work without it.

The source tree is mounted for development. Project data is retained in the named
`tunemorph-data` volume and is never served as a public static directory.

## Checks

```bash
pytest
ruff check backend audio-engine tests
black --check backend audio-engine tests
cd frontend && npm run lint && npm run typecheck && npm run format:check
```

## Current API

- `GET /health` — liveness and service version
- `GET /api/styles` — stable metadata for built-in style plugins
- `POST /api/projects` — create a private UUID project
- `POST /api/projects/{id}/audio` — stream, limit and decode-validate an audio upload
- `GET /api/projects/{id}` and `GET /api/projects/{id}/status` — project state
- `POST /api/projects/{id}/process` — enqueue analysis, transcription, styling and rendering
- `GET /api/projects/{id}/analysis` — detected BPM, key, duration and note count
- `GET /api/projects/{id}/midi` — download the transformed Standard MIDI File
- `GET /api/projects/{id}/preview` — play or download the synthesized WAV preview
- `DELETE /api/projects/{id}` — remove database records and private artifacts
- Interactive OpenAPI — `/docs`; machine-readable schema — `/openapi.json`

The processing request runs in a bounded local background executor and reports real stage
boundaries. The queue interface can later be replaced by a distributed worker.

## Models, preview rendering, and limitations

The working FAST engine uses NumPy/SciPy spectral, onset-energy and dominant-pitch
analysis to create a recognisable melodic MIDI reduction, applies quantization,
transpose, range, density and polyphony transformations, and renders a deterministic
synthesized WAV preview. It intentionally avoids Numba/LLVM, so setup works with standard
Python 3.11–3.14 installations on macOS. This is not a note-perfect transcription of dense
polyphonic audio. The explicit adapters allow a model-backed transcriber and Demucs
separation to replace this path without changing the API.

FluidSynth will be the preferred local MIDI renderer. Install it through your operating
system and set `PREVIEW_SOUNDFONT` to a legally obtained General MIDI SoundFont. TuneMorph
does not bundle a dedicated music-box SoundFont.

The UI creates a project and uploads audio to the API. It reports only actual request and
validation states; there is no fabricated processing progress or placeholder MIDI output.
Style cards have an explicit selected state, Advanced Settings exposes real controls whose
values are persisted with the project, and a successful upload displays an original-audio
player backed by the private project endpoint.

## Troubleshooting

### Upload reports that the project cannot be created

The browser sends API calls to the Next.js same-origin `/backend/*` proxy. In local
development, start the API on port 8000 before the frontend. Docker configures the proxy
to use the `backend` service automatically. For a different API address, set
`BACKEND_INTERNAL_URL` in the frontend process; do not use a Docker-only hostname in a
browser-facing variable.

```bash
curl http://localhost:8000/health
curl http://localhost:3000/backend/health
```

Both calls should return `{"status":"ok",...}`. If the first fails, start Uvicorn. If
only the second fails, restart Next.js after changing `BACKEND_INTERNAL_URL`.

### `ModuleNotFoundError: No module named 'tunemorph_backend'`

This means Uvicorn is running with a Python interpreter where the local backend package
was not installed. On macOS, the path in the traceback often reveals a global Uvicorn
(for example `/Library/Frameworks/Python.framework/...`) even though the prompt displays
`(.venv)`. From the repository root, repair the environment and start the exact venv
interpreter:

```bash
make setup
make backend
```

To verify the interpreter manually:

```bash
.venv/bin/python -c "import sys, tunemorph_backend; print(sys.executable)"
.venv/bin/python -m uvicorn tunemorph_backend.main:app --reload --port 8000
```

## Licensing notes

The project code is offered under the MIT license. Principal dependencies are isolated
behind application or engine boundaries: FastAPI (MIT), Pydantic (MIT), Uvicorn (BSD-3),
Next.js (MIT), React (MIT), Tailwind CSS (MIT), SQLAlchemy (MIT), NumPy (BSD-3), SciPy
(BSD-3), SoundFile (BSD-3), Mido (MIT), and pytest (MIT).
FFmpeg and FluidSynth licensing depends on the installed build; operators must verify
their distribution configuration. Optional ML adapters and model weights must be reviewed
independently before production distribution.

## Privacy and copyright

Project IDs will use random UUIDs, binary media will stay outside the database, and local
artifacts will live below `data/projects/<uuid>/`. The default retention window is 24
hours. TuneMorph accepts direct uploads only; it does not download media from streaming
services.
