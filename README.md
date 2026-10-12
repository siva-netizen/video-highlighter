# ReelBite — Agentic Highlight Maker

Turn a ~30-minute video into a 1–3 minute highlight reel using **Groq** (Whisper + LLM agent) and classical **CV** (shot boundaries, keyframe scoring, pHash dedup).

See [SPEC.md](./SPEC.md) for architecture, ablation plan, and timeline. The in-app **Doc** page (`/doc`) is a shorter walkthrough of stages and tooling.

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

## Run (CLI)

```bash
source .venv/bin/activate
python main.py match.mp4 --target 120 --skill auto --out highlights.mp4
```

Artifacts land under `work/` (transcript, shots, windows, `plan.json`, `summary.md`, keyframes).

## Web UI

| Route | Purpose |
|-------|---------|
| `/` | Landing |
| `/doc` | Pipeline walkthrough (what each stage uses) |
| `/studio` | Upload, session history, live activity, artifact preview |

**Local dev** — fixed ports **8800** (API) and **5174** (Vite):

Terminal 1 — API (repo root, venv active):

```bash
.venv/bin/python -m uvicorn hl.server:app --reload --port 8800
```

Terminal 2 — frontend:

```bash
cd web && npm install && npm run dev
```

Open http://localhost:5174 → **Studio**. Vite proxies `/api` to port 8800.

**Studio behavior:** jobs stored on disk; sidebar **session history**; **Continue** resumes failed/stale runs from cached artifacts; artifact chips open a **right-side preview** (transcript, shots with thumbnails, keyframes, plan, video); **live activity** log at the bottom.

## Docker

Requires Docker Desktop. Host ports are fixed:

| Service | Container | Host port |
|---------|-----------|-----------|
| API | 8000 | **8800** |
| Web (nginx) | 80 | **5174** |

`scripts/pick-docker-ports.sh` exports those ports and errors only if a **non-Docker** process already listens on them (existing ReelBite containers are recreated).

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

- UI: http://localhost:5174  
- API: http://localhost:8800/api/health  

### Job storage (no database)

Docker maps container `/app/work` → **`./data/work/`** on your machine (gitignored). Each run:

- `data/work/jobs/{job_id}/source.*` — uploaded video  
- `data/work/jobs/{job_id}/highlights.mp4` — final reel  
- `data/work/jobs/{job_id}/work/*_transcript.json`, `*_shots.json`, `shot_thumbs/`, `keyframes/`, `*_plan.json`, `summary.md`  
- `data/work/jobs/{job_id}/events.jsonl`, `artifacts.json`, `job.json`  

Local CLI (no Docker) still uses `./work/` at repo root.

**API:** `GET /api/jobs`, `POST /api/jobs/{id}/resume`, artifacts and event streams for the Studio UI.

## Project layout

```
main.py           CLI
hl/server.py      FastAPI for web UI
web/              Vite + React (Landing, Doc, Studio)
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
