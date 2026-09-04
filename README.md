# TuneMorph

TuneMorph is an open-source foundation for turning user-supplied audio into coherent,
style-aware MIDI arrangements. It deliberately targets recognisable musical
reinterpretation rather than promising perfect note-for-note transcription of arbitrary
polyphonic recordings.

This first milestone establishes the production-oriented monorepo, FastAPI service,
replaceable audio-engine contracts, responsive Next.js interface, tests, and Docker
development environment. Audio processing is intentionally implemented in subsequent
pipeline milestones rather than represented here by fake progress or mock conversion.

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

- Python 3.12+
- Node.js 20+
- `ffmpeg`/`ffprobe` (required by the processing milestone)
- Docker Compose (optional)

## Local development

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e './audio-engine[dev]' -e './backend[dev]'
uvicorn tunemorph_backend.main:app --reload --port 8000
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
cp .env.example .env
docker compose up --build
```

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
- Interactive OpenAPI — `/docs`; machine-readable schema — `/openapi.json`

Project, upload, job, result, and download endpoints are introduced with the processing
pipeline. See [the architecture document](docs/architecture.md) for their planned shape.

## Models, preview rendering, and limitations

The engine uses explicit adapter interfaces, so source separation, transcription,
analysis, and rendering are not coupled to one vendor or model. No large model weights
or copyrighted recordings are distributed. A later milestone can enable Demucs under
its own terms and fall back to the fast pipeline when separation is unavailable.

FluidSynth will be the preferred local MIDI renderer. Install it through your operating
system and set `PREVIEW_SOUNDFONT` to a legally obtained General MIDI SoundFont. TuneMorph
does not bundle a dedicated music-box SoundFont.

At this milestone the upload interface is demonstrative and does not send files: this is
made explicit in the UI. There is no fabricated job progress or placeholder MIDI output.

## Licensing notes

The project code is offered under the MIT license. Principal dependencies are isolated
behind application or engine boundaries: FastAPI (MIT), Pydantic (MIT), Uvicorn (BSD-3),
Next.js (MIT), React (MIT), Tailwind CSS (MIT), SQLAlchemy (MIT), and pytest (MIT).
FFmpeg and FluidSynth licensing depends on the installed build; operators must verify
their distribution configuration. Optional ML adapters and model weights must be reviewed
independently before production distribution.

## Privacy and copyright

Project IDs will use random UUIDs, binary media will stay outside the database, and local
artifacts will live below `data/projects/<uuid>/`. The default retention window is 24
hours. TuneMorph accepts direct uploads only; it does not download media from streaming
services.
