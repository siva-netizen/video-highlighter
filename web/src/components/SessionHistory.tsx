import { useCallback, useEffect, useState } from "react";
import type { JobHistoryItem } from "../types/history";

function formatWhen(iso: string | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

type Props = {
  activeJobId: string | null;
  onRestore: (jobId: string) => void;
  onResume: (jobId: string) => void;
  onNew: () => void;
  refreshKey?: number;
};

export function SessionHistory({ activeJobId, onRestore, onResume, onNew, refreshKey = 0 }: Props) {
  const [jobs, setJobs] = useState<JobHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/jobs?limit=40");
      if (res.ok) {
        const body = await res.json();
        setJobs(body.jobs ?? []);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <aside className="session-history">
      <div className="session-history-head">
        <p className="governance-label">Session history</p>
        <button type="button" className="btn btn-ghost btn-sm history-new" onClick={onNew}>
          New
        </button>
      </div>
      <p className="activity-sub">Past runs on this server (disk). Click to restore.</p>

      {loading && <p className="activity-empty">Loading…</p>}

      {!loading && jobs.length === 0 && (
        <p className="activity-empty">No sessions yet.</p>
      )}

      <ul className="history-list">
        {jobs.map((j) => (
          <li key={j.id} className="history-row">
            <button
              type="button"
              className={`history-item ${activeJobId === j.id ? "history-item-active" : ""}`}
              onClick={() => onRestore(j.id)}
            >
              <span className="history-item-title">{j.filename ?? j.id}</span>
              <span className="history-item-meta">
                {formatWhen(j.created_at ?? j.started_at)} · {j.status}
                {j.progress_pct != null && j.status === "failed" ? ` · ${j.progress_pct}%` : ""}
                {j.has_video ? " · video" : ""}
                {j.skill && j.skill !== "auto" ? ` · ${j.skill}` : ""}
              </span>
            </button>
            {j.can_resume && (
              <button
                type="button"
                className="btn btn-ghost btn-sm history-resume"
                title="Continue from saved artifacts"
                onClick={(ev) => {
                  ev.stopPropagation();
                  onResume(j.id);
                }}
              >
                Continue
              </button>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
}
