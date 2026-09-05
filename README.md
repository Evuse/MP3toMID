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
- `DELETE /api/projects/{id}` — remove database records and private artifacts
- Interactive OpenAPI — `/docs`; machine-readable schema — `/openapi.json`

Processing, result, and download endpoints are introduced with the processing pipeline.
See [the architecture document](docs/architecture.md) for their planned shape.

## Models, preview rendering, and limitations

The engine uses explicit adapter interfaces, so source separation, transcription,
analysis, and rendering are not coupled to one vendor or model. No large model weights
or copyrighted recordings are distributed. A later milestone can enable Demucs under
its own terms and fall back to the fast pipeline when separation is unavailable.

FluidSynth will be the preferred local MIDI renderer. Install it through your operating
system and set `PREVIEW_SOUNDFONT` to a legally obtained General MIDI SoundFont. TuneMorph
does not bundle a dedicated music-box SoundFont.

The UI creates a project and uploads audio to the API. It reports only actual request and
validation states; there is no fabricated processing progress or placeholder MIDI output.

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
