"""Tools exposed to the LLM agent (function calling)."""

from __future__ import annotations

from typing import Any


class WindowTools:
    def __init__(self, windows: list[dict], picks: list[dict] | None = None):
        self.windows = {w["id"]: w for w in windows}
        self.picks = picks or []

    def get_window(self, window_id: int) -> dict[str, Any]:
        return self.windows[window_id]

    def get_neighbors(self, window_id: int, n: int = 2) -> list[dict]:
        ids = sorted(self.windows)
        try:
            idx = ids.index(window_id)
        except ValueError:
            return []
        lo = max(0, idx - n)
        hi = min(len(ids), idx + n + 1)
        return [self.windows[i] for i in ids[lo:hi]]

    def list_picks(self) -> dict[str, Any]:
        total = sum(
            (p.get("pad_before", 0) + p.get("pad_after", 0) + 15)
            for p in self.picks
        )
        return {"picks": self.picks, "estimated_seconds": total}

    def check_overlap(self, window_ids: list[int]) -> dict[str, Any]:
        issues: list[str] = []
        selected = [self.windows[i] for i in window_ids if i in self.windows]
        selected.sort(key=lambda w: w["start"])
        for i in range(len(selected) - 1):
            a, b = selected[i], selected[i + 1]
            if b["start"] - a["end"] < 20:
                issues.append(
                    f"Windows {a['id']} and {b['id']} within 20s proximity"
                )
        return {"issues": issues}
