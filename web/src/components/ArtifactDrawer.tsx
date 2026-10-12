import { useEffect, useState } from "react";
import type { ArtifactManifest, Plan, Shot, ShotPreview, ShotsArtifact } from "../types/artifacts";

export type DrawerView = "video" | "transcript" | "shots" | "keyframes" | "plan" | null;

type TranscriptSeg = { start: number; end: number; text: string };

const TITLES: Record<Exclude<DrawerView, null>, string> = {
  video: "Highlight reel",
  transcript: "Transcript",
  shots: "CV-1 · Shots",
  keyframes: "CV-2 · Keyframes",
  plan: "Plan & summary",
};

function parseShotsPayload(data: unknown): ShotsArtifact {
  if (Array.isArray(data)) {
    return { shots: data as Shot[], previews: [], count: data.length };
  }
  const body = data as ShotsArtifact;
  return {
    shots: body.shots ?? [],
    previews: body.previews ?? [],
    count: body.count ?? body.shots?.length ?? 0,
  };
}

function ShotTimeline({ shots }: { shots: Shot[] }) {
  const max = Math.max(...shots.map((s) => s.end), 1);
  return (
    <div className="shot-timeline">
      <div className="shot-track">
        {shots.slice(0, 150).map((s) => (
          <div
            key={s.id}
            className="shot-seg"
            style={{
              left: `${(s.start / max) * 100}%`,
              width: `${Math.max(0.35, ((s.end - s.start) / max) * 100)}%`,
            }}
            title={`#${s.id} · ${s.start.toFixed(1)}s – ${s.end.toFixed(1)}s`}
          />
        ))}
      </div>
      <p className="field-hint">
        {shots.length} shots · timeline scaled to {max.toFixed(0)}s
      </p>
    </div>
  );
}

function ShotGallery({ shots, previews }: { shots: Shot[]; previews: ShotPreview[] }) {
  return (
    <div className="shot-artifact">
      <ShotTimeline shots={shots} />
      {previews.length > 0 ? (
        <div className="shot-grid">
          {previews.map((p) => (
            <figure key={p.id} className="shot-card">
              <img src={p.thumb_url} alt="" loading="lazy" />
              <figcaption>
                #{p.id} · {p.start.toFixed(1)}–{p.end.toFixed(1)}s
              </figcaption>
            </figure>
          ))}
        </div>
      ) : (
        <p className="field-hint">Generating shot previews… refresh in a moment.</p>
      )}
    </div>
  );
}

export function ArtifactDrawer({
  jobId,
  view,
  open,
  running,
  onClose,
}: {
  jobId: string | null;
  view: DrawerView;
  open: boolean;
  running: boolean;
  onClose: () => void;
}) {
  const [manifest, setManifest] = useState<ArtifactManifest | null>(null);
  const [shotsData, setShotsData] = useState<ShotsArtifact>({ shots: [], previews: [], count: 0 });
  const [plan, setPlan] = useState<Plan | null>(null);
  const [summary, setSummary] = useState("");
  const [transcript, setTranscript] = useState<TranscriptSeg[]>([]);

  useEffect(() => {
    if (!jobId || !open) return;
    let cancelled = false;

    const load = async () => {
      const mRes = await fetch(`/api/jobs/${jobId}/artifacts`);
      if (!mRes.ok || cancelled) return;
      const m: ArtifactManifest = await mRes.json();
      setManifest(m);

      if (m.artifacts.cv1_shots.ready) {
        const r = await fetch(`/api/jobs/${jobId}/artifacts/shots`);
        if (r.ok && !cancelled) setShotsData(parseShotsPayload(await r.json()));
      }
      if (m.artifacts.transcript?.ready) {
        const tr = await fetch(`/api/jobs/${jobId}/artifacts/transcript`);
        if (tr.ok && !cancelled) setTranscript(await tr.json());
      }
      if (m.artifacts.plan.ready) {
        const p = await fetch(`/api/jobs/${jobId}/plan`);
        if (p.ok && !cancelled) setPlan(await p.json());
        const s = await fetch(`/api/jobs/${jobId}/summary`);
        if (s.ok && !cancelled) {
          const body = await s.json();
          setSummary(body.markdown ?? "");
        }
      }
    };

    load();
    const id = running ? setInterval(load, 2000) : undefined;
    return () => {
      cancelled = true;
      if (id) clearInterval(id);
    };
  }, [jobId, open, running]);

  if (!view || !open) return null;

  const title = TITLES[view];
  const arts = manifest?.artifacts;

  return (
    <section className="artifact-preview-panel artifact-slide-panel" aria-label="Artifact preview">
      <header className="artifact-preview-head">
        <h3>{title}</h3>
        <button type="button" className="toast-close" onClick={onClose} aria-label="Close preview">
          ×
        </button>
      </header>
      <div className="artifact-preview-body">
        {view === "video" &&
          (arts?.video.ready && arts.video.url ? (
            <video className="artifact-video" controls src={arts.video.url} />
          ) : (
            <p className="activity-empty">Video not ready yet.</p>
          ))}

        {view === "transcript" && (
          <ul className="transcript-list">
            {transcript.length === 0 && <p className="activity-empty">Transcript not ready.</p>}
            {transcript.slice(0, 200).map((s, i) => (
              <li key={i}>
                <time>{s.start.toFixed(1)}s</time> {s.text}
              </li>
            ))}
          </ul>
        )}

        {view === "shots" &&
          (shotsData.shots.length ? (
            <ShotGallery shots={shotsData.shots} previews={shotsData.previews} />
          ) : (
            <p className="activity-empty">Shots not ready.</p>
          ))}

        {view === "keyframes" && (
          <div className="keyframe-grid">
            {(arts?.cv2_keyframes.items ?? []).map((kf) => (
              <figure key={kf.path} className="keyframe-card">
                <img src={kf.url} alt="" loading="lazy" />
                <figcaption>w{kf.window_id}</figcaption>
              </figure>
            ))}
            {!arts?.cv2_keyframes.ready && (
              <p className="activity-empty">Keyframes not ready.</p>
            )}
          </div>
        )}

        {view === "plan" && plan && (
          <div className="plan-artifact">
            <p>
              Skill <strong>{plan.skill}</strong> · {plan.moments.length} moments
            </p>
            <ul className="plan-list">
              {plan.moments.map((m, i) => (
                <li key={i}>
                  <strong>{m.label ?? "moment"}</strong> ({m.clip.start.toFixed(1)}–
                  {m.clip.end.toFixed(1)}s)
                </li>
              ))}
            </ul>
            {summary && <pre className="activity-json plan-summary">{summary}</pre>}
          </div>
        )}
        {view === "plan" && !plan && <p className="activity-empty">Plan not ready.</p>}
      </div>
    </section>
  );
}

export function ArtifactLauncher({
  jobId,
  manifest,
  activeView,
  onOpen,
}: {
  jobId: string | null;
  manifest: ArtifactManifest | null;
  activeView?: DrawerView;
  onOpen: (view: Exclude<DrawerView, null>) => void;
}) {
  if (!jobId) return null;
  const a = manifest?.artifacts;
  const chips: { id: Exclude<DrawerView, null>; label: string; ready: boolean }[] = [
    { id: "transcript", label: "Transcript", ready: !!a?.transcript?.ready },
    { id: "shots", label: "Shots", ready: !!a?.cv1_shots.ready },
    { id: "keyframes", label: "Keyframes", ready: !!a?.cv2_keyframes.ready },
    { id: "plan", label: "Plan", ready: !!a?.plan.ready },
    { id: "video", label: "Video", ready: !!a?.video.ready },
  ];

  return (
    <div className="artifact-launcher">
      <p className="governance-label">Artifacts</p>
      <div className="artifact-chips">
        {chips.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`artifact-chip ${c.ready ? "artifact-chip-ready" : ""} ${activeView === c.id ? "artifact-chip-active" : ""}`}
            disabled={!c.ready}
            onClick={() => onOpen(c.id)}
          >
            {c.label}
            {c.ready && <span className="artifact-dot" />}
          </button>
        ))}
      </div>
    </div>
  );
}
