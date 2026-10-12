# Agentic Highlight Maker

Turn a ~30-minute video into a 1–3 minute highlight reel using **Groq** (Whisper + LLM agent) and classical **CV** (shot boundaries, keyframe scoring, pHash dedup).

See [SPEC.md](./SPEC.md) for architecture, ablation plan, and timeline.

## Prerequisites

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) and ffprobe on `PATH`
- Groq API key

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

Optional overrides: `STT_MODEL`, `SCORER_MODEL`, `ROUTER_MODEL`.

## Run

```bash
python main.py match.mp4 --target 120 --skill auto --out highlights.mp4
```

Artifacts land under `work/` (transcript, shots, windows, `plan.json`, `summary.md`, keyframes).

## Project layout

```
main.py           CLI
hl/               pipeline modules
skills/           cricket, football, generic playbooks
eval/             ground truth + metrics stub
work/             runtime cache (gitignored)
```

## Evaluation

Hand-mark events in `eval/ground_truth.json`, then:

```bash
python eval/run_eval.py --plan work/your_video_plan.json --video-id cricket_sample
```

Full ablation variants (A–D) are described in SPEC §9.

## License

MIT (add license file if you publish publicly)
