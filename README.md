# Agentic Highlight Maker

Turn a ~30-minute video into a 1–3 minute highlight reel using **Groq** (Whisper + LLM agent) and classical **CV** (shot boundaries, keyframe scoring, pHash dedup).

See [SPEC.md](./SPEC.md) for architecture, ablation plan, and timeline.

## Prerequisites

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) and ffprobe on `PATH`
- Groq API key

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

On macOS, `python` / `pip` are often missing until the venv is activated — use `python3` above, or run without activating:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py match.mp4 --target 120 --skill auto
```

Optional overrides: `STT_MODEL`, `SCORER_MODEL`, `ROUTER_MODEL`.

## Run

```bash
source .venv/bin/activate
python main.py match.mp4 --target 120 --skill auto --out highlights.mp4
```

Artifacts land under `work/` (transcript, shots, windows, `plan.json`, `summary.md`, keyframes).

## Web UI (CodeBite-style)

Terminal 1 — API (from repo root, venv active):

```bash
.venv/bin/python -m uvicorn hl.server:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd web && npm install && npm run dev
```

Open http://localhost:5173 — upload video in **Studio**, poll until `highlights.mp4` plays.

## Docker

Requires Docker Desktop running. Ports are chosen from free candidates on your machine:

| Service | Container | Default host port | Fallbacks |
|---------|-----------|-------------------|-----------|
| API | 8000 | **8800** | 8000, 8001, 8080 |
| Web (nginx) | 80 | **5173** | 5174, 3000, 8081 |

```bash
cp .env.example .env   # set GROQ_API_KEY
chmod +x scripts/docker-up.sh scripts/pick-docker-ports.sh
./scripts/docker-up.sh
```

Manual:

```bash
source scripts/pick-docker-ports.sh
HOST_API_PORT=$HOST_API_PORT HOST_WEB_PORT=$HOST_WEB_PORT docker compose up --build
```

UI: `http://localhost:$HOST_WEB_PORT` · API direct: `http://localhost:$HOST_API_PORT/api/health`

### Job storage (no database)

Each run is stored on **local disk** under `work/jobs/{job_id}/` (Docker volume `highlight-work`):

- `highlights.mp4` — final reel
- `work/*_shots.json`, `keyframes/`, `*_plan.json`, `summary.md`, `events.jsonl`, `artifacts.json`

Optional host bind for easy access: add to `docker-compose.yml` under `api.volumes`:

`- ./data/work:/app/work`

**Session history:** Studio sidebar lists past jobs via `GET /api/jobs` (disk scan). Click a row to restore governance, activity log, and artifacts for that run.

## Project layout

```
main.py           CLI
hl/server.py      FastAPI for web UI
web/              Vite + React frontend
hl/               pipeline modules
skills/           Anthropic-style sport skills (see below)
eval/             ground truth + metrics stub
work/             runtime cache (gitignored)
.cursor/skills/   Cursor agent skill for developing this repo
```

### Sport skills (Agent Skills format)

Per [Anthropic’s skill guide](https://claude.com/resources/guides/the-complete-guide-to-building-skills-for-claude/planning-and-design):

```
skills/
├── cricket/SKILL.md + references/scoring-playbook.md
├── football/...
├── generic/...
└── scripts/validate_all.py
```

Validate after edits:

```bash
python skills/scripts/validate_all.py
```

## Evaluation

Hand-mark events in `eval/ground_truth.json`, then:

```bash
python eval/run_eval.py --plan work/your_video_plan.json --video-id cricket_sample
```

Full ablation variants (A–D) are described in SPEC §9.

## License

MIT (add license file if you publish publicly)
