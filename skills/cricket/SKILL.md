---
name: cricket
description: Ranks cricket broadcast windows for highlight reels from commentary and audio energy. Use when the transcript mentions wickets, sixes, fours, bowling, batting, DRS outcomes, milestones, or typical cricket commentator phrasing.
metadata:
  pre_roll: 6
  post_roll: 6
  keywords: wicket,out,six,four,caught,bowled,lbw,century,fifty,dropped,run out,stumped
---

# Cricket highlight scoring

## Instructions

When scoring windows for a cricket highlight plan:

1. Read each window's `text` and `energy_peak` together — high energy alone is not enough without cricket-relevant language.
2. Assign score 8–10 for clear wickets, sixes/fours with excited commentary, and milestones (50/100) with crowd reaction.
3. Assign score 5–7 for strong chances, near-wickets, or buildup immediately before a wicket in the next window (prefer merging via neighbor context).
4. Assign score 1–3 for dot balls, routine singles, drinks breaks, ads, and replay-only narration without a new event.
5. Set `pad_before` / `pad_after` from metadata unless the moment needs longer celebration (post_roll up to 10 for sixes).
6. Output picks JSON only; respect the playbook in [references/scoring-playbook.md](references/scoring-playbook.md) for skip rules and duplicate replay policy.

## Examples

### Example 1: Six with crowd roar

User context: window text includes "all the way for six" and energy_peak > 2.5.

Actions:

- score: 9
- label: `six`
- reason: cite commentator phrase + crowd peak

### Example 2: Wicket sequence

User context: "gone!", "caught at slip", energy spike.

Actions:

- score: 10
- label: `wicket`
- pad_before: 8 (include delivery run-up when text references the ball)

## Troubleshooting

### Too many low-value boundaries

Cause: scoring every "four" without excitement.

Solution: require energy_peak above median or emphatic wording; demote routine boundaries to ≤5.

### Same ball live + replay

Cause: two windows describe identical outcome.

Solution: keep higher score for live window; drop replay window (see playbook).
