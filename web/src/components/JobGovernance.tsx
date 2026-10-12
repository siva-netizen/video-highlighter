import type { JobMeta } from "../types/job";

const STAGES: { id: string; label: string }[] = [
  { id: "audio", label: "Extract audio" },
  { id: "transcribe", label: "Transcribe (Whisper)" },
  { id: "energy", label: "Audio energy" },
  { id: "shots", label: "Shot detect (CV-1)" },
  { id: "windows", label: "Windows" },
  { id: "agent", label: "Agent + skills" },
  { id: "keyframes", label: "Keyframes (CV-2)" },
  { id: "dedup", label: "Dedup (CV-3)" },
  { id: "render", label: "Render video" },
];

function stageIndex(id: string | undefined): number {
  if (!id) return -1;
  return STAGES.findIndex((s) => s.id === id);
}

function formatEta(iso: string | undefined): string {
  if (!iso) return "Calculating…";
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

type Props = {
  job: JobMeta;
  onResume?: () => void;
  resuming?: boolean;
};

export function JobGovernance({ job, onResume, resuming = false }: Props) {
  const pct = job.progress_pct ?? (job.status === "completed" ? 100 : 0);
  const activeIdx = stageIndex(job.progress_stage ?? job.stage);
  const running = job.status === "queued" || job.status === "running";

  return (
    <div className="governance" role="status" aria-live="polite">
      <div className="governance-head">
        <div>
          <p className="governance-label">Pipeline status</p>
          <p className="governance-state">{job.progress_message ?? job.stage ?? job.status}</p>
        </div>
        <div className="governance-pct" aria-label={`${pct} percent`}>
          {pct}%
        </div>
      </div>

      <div className="governance-bar" aria-hidden>
        <div className="governance-bar-fill" style={{ width: `${pct}%` }} />
      </div>

      {running && !job.looks_stale && (
        <p className="governance-eta">
          Estimated finish · <strong>{formatEta(job.estimated_completion_at)}</strong>
        </p>
      )}

      {running && job.looks_stale && (
        <p className="governance-stale">
          No progress for a few minutes — worker may have stopped. Use <strong>Continue run</strong> below.
        </p>
      )}

      <ol className="governance-steps">
        {STAGES.map((s, i) => {
          let state: "done" | "active" | "pending" = "pending";
          if (job.status === "completed" || i < activeIdx) state = "done";
          else if (i === activeIdx) state = "active";
          else if (job.status === "failed" && i === activeIdx) state = "active";
          return (
            <li key={s.id} className={`gov-step gov-step-${state}`}>
              <span className="gov-step-dot" />
              <span>{s.label}</span>
            </li>
          );
        })}
      </ol>

      {job.skill && job.skill !== "auto" && (
        <p className="governance-skill">
          Skill in use · <strong>{job.skill}</strong> (agent-selected)
        </p>
      )}

      {job.error && <p className="job-error">{job.error}</p>}

      {job.can_resume && onResume && (
        <div className="governance-resume">
          {job.resume_hint && <p className="field-hint">{job.resume_hint}</p>}
          <button type="button" className="btn btn-accent btn-sm" disabled={resuming} onClick={onResume}>
            {resuming ? "Continuing…" : "Continue run"}
          </button>
        </div>
      )}
    </div>
  );
}
