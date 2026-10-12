import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  ArtifactDrawer,
  ArtifactLauncher,
  type DrawerView,
} from "../components/ArtifactDrawer";
import { ActivityStream } from "../components/ActivityStream";
import { JobGovernance } from "../components/JobGovernance";
import { SessionHistory } from "../components/SessionHistory";
import { pushToast, ToastStack, type ToastItem } from "../components/ToastStack";
import type { ArtifactManifest } from "../types/artifacts";
import type { JobEvent } from "../types/events";
import type { JobMeta } from "../types/job";

const TARGET_MIN = 60;
const TARGET_MAX = 300;

function formatTarget(seconds: number): string {
  if (seconds >= 60 && seconds % 60 === 0) {
    return `${seconds / 60} min (${seconds}s)`;
  }
  return `${seconds}s`;
}

export function Studio() {
  const [target, setTarget] = useState(120);
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<JobMeta | null>(null);
  const [busy, setBusy] = useState(false);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [drawerView, setDrawerView] = useState<DrawerView>(null);
  const [manifest, setManifest] = useState<ArtifactManifest | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [resuming, setResuming] = useState(false);
  const lastErrorRef = useRef<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.ok)
      .then(setApiOk)
      .catch(() => {
        setApiOk(false);
        pushToast(setToasts, "API unreachable", "error");
      });
  }, []);

  const pollEvents = useCallback(async (jobId: string, cursor: number) => {
    const res = await fetch(`/api/jobs/${jobId}/events?after=${cursor}`);
    if (!res.ok) return cursor;
    const body = await res.json();
    const batch: JobEvent[] = body.events ?? [];
    if (batch.length) {
      setEvents((prev) => [...prev, ...batch]);
      return body.next ?? cursor + batch.length;
    }
    return cursor;
  }, []);

  const loadManifest = useCallback(async (jobId: string) => {
    const res = await fetch(`/api/jobs/${jobId}/artifacts`);
    if (res.ok) setManifest(await res.json());
  }, []);

  const pollJob = useCallback(
    (jobId: string) => {
      let evCursor = 0;
      const tick = async () => {
        const jobRes = await fetch(`/api/jobs/${jobId}`);
        await pollEvents(jobId, evCursor).then((n) => {
          evCursor = n;
        });
        if (!jobRes.ok) {
          pushToast(setToasts, "Lost connection to job status", "error");
          setBusy(false);
          return;
        }
        const data: JobMeta = await jobRes.json();
        setJob(data);
        await loadManifest(jobId);

        if (data.error && data.error !== lastErrorRef.current) {
          lastErrorRef.current = data.error;
          pushToast(setToasts, data.error, "error");
        }

        if (data.status === "queued" || data.status === "running") {
          setTimeout(tick, 1200);
        } else {
          await pollEvents(jobId, evCursor);
          setBusy(false);
          setHistoryRefresh((k) => k + 1);
          if (data.status === "completed") {
            pushToast(setToasts, "Highlight reel ready", "info");
          }
        }
      };
      tick();
    },
    [pollEvents, loadManifest],
  );

  const restoreSession = useCallback(
    async (jobId: string) => {
      setActiveJobId(jobId);
      setEvents([]);
      setDrawerView(null);
      lastErrorRef.current = null;
      const jobRes = await fetch(`/api/jobs/${jobId}`);
      if (!jobRes.ok) {
        pushToast(setToasts, "Could not restore session", "error");
        return;
      }
      const data: JobMeta = await jobRes.json();
      setJob(data);
      if (data.error) {
        lastErrorRef.current = data.error;
        pushToast(setToasts, data.error, "error");
      }
      const evRes = await fetch(`/api/jobs/${jobId}/events?full=true`);
      if (evRes.ok) {
        const evBody = await evRes.json();
        setEvents(evBody.events ?? []);
      }
      await loadManifest(jobId);
      if (data.status === "queued" || data.status === "running") {
        setBusy(true);
        pollJob(jobId);
      } else {
        setBusy(false);
      }
    },
    [pollJob, loadManifest],
  );

  const resumeSession = useCallback(
    async (jobId: string) => {
      setResuming(true);
      setActiveJobId(jobId);
      setBusy(true);
      lastErrorRef.current = null;
      const res = await fetch(`/api/jobs/${jobId}/resume`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = (body as { detail?: string | { msg?: string }[] }).detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail) && detail[0]?.msg
              ? detail[0].msg
              : "Could not resume session";
        pushToast(setToasts, msg, "error");
        setResuming(false);
        setBusy(false);
        return;
      }
      const body = await res.json();
      pushToast(setToasts, body.resume_hint ?? "Resuming from saved artifacts", "info");
      setEvents([]);
      setResuming(false);
      setHistoryRefresh((k) => k + 1);
      pollJob(jobId);
    },
    [pollJob],
  );

  function startNewSession() {
    setJob(null);
    setFile(null);
    setEvents([]);
    setActiveJobId(null);
    setBusy(false);
    setDrawerView(null);
    setManifest(null);
    lastErrorRef.current = null;
  }

  function openDrawer(view: Exclude<DrawerView, null>) {
    setDrawerView(view);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setJob(null);
    setEvents([]);
    setDrawerView(null);
    lastErrorRef.current = null;
    const body = new FormData();
    body.append("video", file);
    body.append("target_seconds", String(target));
    body.append("skill", "auto");
    const res = await fetch("/api/jobs", { method: "POST", body });
    if (!res.ok) {
      setBusy(false);
      const msg = "Upload failed";
      setJob({ id: "", status: "failed", error: msg });
      pushToast(setToasts, msg, "error");
      return;
    }
    const { job_id } = await res.json();
    setActiveJobId(job_id);
    setHistoryRefresh((k) => k + 1);
    pollJob(job_id);
  }

  const showForm = !job && !busy;
  const showWorkspace = !!job || busy;
  const jobId = activeJobId ?? job?.id ?? null;
  const running = busy || job?.status === "queued" || job?.status === "running";

  return (
    <section className={`studio grid-cell studio-page ${drawerView ? "studio-drawer-open" : ""}`}>
      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))} />

      <div className="studio-head">
        <h2>Studio</h2>
        <p>
          {apiOk === false
            ? "API unreachable — check Docker or uvicorn on port 8800."
            : "History left · activity center · artifacts slide in on the right."}
        </p>
      </div>

      <div className="studio-claude-layout">
        <SessionHistory
          activeJobId={activeJobId}
          onRestore={restoreSession}
          onResume={resumeSession}
          onNew={startNewSession}
          refreshKey={historyRefresh}
        />

        <div className="studio-center">
          {showForm && (
            <form className="studio-form" onSubmit={onSubmit}>
              <label className="field">
                <span>Video file</span>
                <input
                  type="file"
                  accept="video/*"
                  required
                  onChange={(ev) => setFile(ev.target.files?.[0] ?? null)}
                />
              </label>
              <label className="field">
                <span>Highlight length — {formatTarget(target)}</span>
                <input
                  type="range"
                  min={TARGET_MIN}
                  max={TARGET_MAX}
                  step={15}
                  value={target}
                  onChange={(ev) => setTarget(Number(ev.target.value))}
                />
              </label>
              <button className="btn btn-accent btn-wide" type="submit" disabled={busy || !file}>
                Generate highlights
              </button>
            </form>
          )}

          {showWorkspace && (
            <>
              <JobGovernance
                job={
                  job ?? {
                    id: jobId ?? "",
                    status: "queued",
                    progress_pct: 0,
                    progress_message: "Starting…",
                  }
                }
                onResume={jobId ? () => resumeSession(jobId) : undefined}
                resuming={resuming}
              />
              <ArtifactLauncher jobId={jobId} manifest={manifest} onOpen={openDrawer} />
              <ActivityStream events={events} />
            </>
          )}
        </div>

        <ArtifactDrawer
          jobId={jobId}
          view={drawerView}
          open={!!drawerView}
          running={running}
          onClose={() => setDrawerView(null)}
        />
      </div>
    </section>
  );
}
