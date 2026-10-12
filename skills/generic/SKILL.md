---
name: generic
description: Ranks commentary-driven windows for highlight reels when no sport-specific skill applies. Use for talks, podcasts, lectures, esports, or mixed content when user selects generic skill or router cannot match cricket/football.
metadata:
  pre_roll: 4
  post_roll: 4
  keywords: amazing,incredible,wow,breakthrough,finally,winner,applause,laughter
---

# Generic highlight scoring

## Instructions

1. Prefer **complete narrative beats** (setup → punchline → reaction) over isolated noise.
2. Score 8–10 for emotional peaks: applause, laughter, surprise, explicit "announcement" language.
3. Score 6–8 for substantive insights with moderate energy (key quotes, conclusions).
4. Score ≤4 for filler, sponsor reads, long silence, or repetitive phrasing across neighbors.
5. Use `energy_peak` as tie-breaker, not sole signal — require meaningful words in `text`.
6. Follow diversity and dedup rules in [references/scoring-playbook.md](references/scoring-playbook.md).

## Examples

### Example 1: Talk climax

Text: "And that's why we rebuilt the entire stack" + energy rise.

- score: 8
- label: `climax`

### Example 2: Applause-only

Text: "[applause]" with weak transcript — energy high.

- score: 7 if sustained; else 5

## Troubleshooting

### No commentary (music-only windows)

Score from energy only; cap at 6 unless project README notes music-only mode.

### Near-duplicate quotes

If two windows share same sentence stem within 30s, keep higher score only.
