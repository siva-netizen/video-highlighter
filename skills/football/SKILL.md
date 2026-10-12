---
name: football
description: Ranks association-football commentary windows for highlight reels. Use when transcript mentions goals, penalties, saves, red cards, VAR decisions, free kicks, counters, or football-specific commentator language.
metadata:
  pre_roll: 5
  post_roll: 8
  keywords: goal,scores,penalty,red card,save,header,free kick,counter,assist,var,offside
---

# Football highlight scoring

## Instructions

1. Score windows using **event clarity** first, then `energy_peak`.
2. Goals and scored penalties: 9–10; include build-up words ("through on goal", "finishes") when present.
3. World-class saves, woodwork, missed open goals: 7–9.
4. Red cards and major VAR confirmations: 8–10 when outcome is stated in-window.
5. Fast breaks ending in shot or goal: 7–9; dead-ball restarts alone: ≤4.
6. Apply skip rules and replay dedup from [references/scoring-playbook.md](references/scoring-playbook.md).
7. Use longer `post_roll` (up to 12) for goals with visible celebration in text ("scenes", " erupts").

## Examples

### Example 1: Goal

Text: "GOAL! What a finish!" — energy_peak high.

- score: 10
- label: `goal`
- post_roll: 10

### Example 2: Save

Text: "brilliant save", "denied again" — no goal.

- score: 8
- label: `save`

## Troubleshooting

### Offside flag without shot

Do not score above 4 unless a shot or save occurs in the same window.

### Duplicate goal replay

Keep first window with live description; drop replay-only windows with same scorer and minute phrasing.
