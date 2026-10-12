---
name: highlight-maker-dev
description: Implements and extends the Agentic Highlight Maker pipeline (Groq STT/LLM, PySceneDetect, OpenCV keyframes, pHash dedup). Use when working in video-highlighter, highlight-maker, SPEC.md, hl/ modules, eval ablation, or sport skills under skills/.
---

# Highlight Maker — development skill

## Instructions

### Step 1: Read SPEC.md

Confirm stage touched (audio → transcribe → windows → agent → CV-1/2/3 → render). Do not add overlays, CLIP, or training per non-goals.

### Step 2: Groq integration

- Env: `GROQ_API_KEY`, optional `STT_MODEL`, `SCORER_MODEL`, `ROUTER_MODEL`
- Whisper: 16 kHz mono, 10-minute chunks, cache `work/*_transcript.json`
- Scorer/Router: structured JSON output; batch windows in one scorer call when possible

### Step 3: Sport skills (Anthropic layout)

Each sport lives in `skills/<name>/SKILL.md` with `references/scoring-playbook.md`.

After editing skills:

```bash
python skills/scripts/validate_all.py
```

Loader: `hl/skills.py` — `discover_skill_catalog()` (YAML only) → router; `load_skill()` (body + references) → scorer. Agent graph in `hl/agent.py` (LangGraph). CLI `--skill` choices come from disk, not hardcoded.

### Step 4: CV stages (do not cut for report)

- CV-1: `hl/shots.py`, `hl/snap.py` — PySceneDetect, merge shots < 2s
- CV-2: `hl/keyframes.py` — Laplacian sharpness, motion, brightness gate
- CV-3: `hl/dedup.py` — pHash + histogram

### Step 5: CLI smoke

```bash
python main.py path/to/video.mp4 --target 120 --skill auto
```

Requires ffmpeg/ffprobe on PATH.

## Examples

### Example: New sport skill

1. Copy `skills/generic/` → `skills/rugby/`
2. Update frontmatter `name`, `description` (what + when), `metadata.pre_roll/post_roll/keywords`
3. Edit `references/scoring-playbook.md`
4. Run `validate_all.py`
5. Add `rugby` to CLI choices in `main.py` and router hints in `hl/agent.py` if needed

## Troubleshooting

### Skill not found

Cause: folder name ≠ `name` in frontmatter, or missing `SKILL.md`.

Solution: run `python skills/scripts/validate_all.py`.

### Groq model 404

Cause: model slug changed.

Solution: list models via Groq API; update `.env` overrides.
