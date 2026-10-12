import { useEffect, useState } from "react";
import type { ArtifactManifest, Plan, Shot, ShotPreview, ShotsArtifact } from "../types/artifacts";

type Tab = "reel" | "cv1" | "cv2" | "plan";

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

function ShotTimeline({ shots, duration }: { shots: Shot[]; duration: number }) {
  const max = duration || Math.max(...shots.map((s) => s.end), 1);
  return (
    <div className="shot-timeline" role="img" aria-label="Shot boundary timeline">
      <div className="shot-track">
        {shots.slice(0, 120).map((s) => (
          <div
            key={s.id}
            className="shot-seg"
            title={`#${s.id} · ${s.start.toFixed(1)}s – ${s.end.toFixed(1)}s`}
            style={{
              left: `${(s.start / max) * 100}%`,
              width: `${Math.max(0.4, ((s.end - s.start) / max) * 100)}%`,
            }}
          />
        ))}
      </div>
      <p className="field-hint">{shots.length} shots · timeline scaled to {max.toFixed(0)}s</p>
    </div>
  );
}

function ShotGallery({ shots, previews }: { shots: Shot[]; previews: ShotPreview[] }) {
  const duration = Math.max(...shots.map((s) => s.end), 1);
  return (
    <div className="shot-artifact">
      <ShotTimeline shots={shots} duration={duration} />
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
        <p className="field-hint">Generating shot previews…</p>
      )}
    </div>
  );
}

export function ArtifactPanel({ jobId, running }: { jobId: string | null; running: boolean }) {
  const [tab, setTab] = useState<Tab>("reel");
  const [manifest, setManifest] = useState<ArtifactManifest | null>(null);
  const [shotsData, setShotsData] = useState<ShotsArtifact>({ shots: [], previews: [], count: 0 });
  const [plan, setPlan] = useState<Plan | null>(null);
  const [summary, setSummary] = useState("");

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    const load = async () => {
      const mRes = await fetch(`/api/jobs/${jobId}/artifacts`);
      if (!mRes.ok || cancelled) return;
      const m: ArtifactManifest = await mRes.json();
      setManifest(m);

      if (m.artifacts.cv1_shots.ready) {
        const sRes = await fetch(`/api/jobs/${jobId}/artifacts/shots`);
        if (sRes.ok && !cancelled) setShotsData(parseShotsPayload(await sRes.json()));
      }
      if (m.artifacts.plan.ready) {
        const pRes = await fetch(`/api/jobs/${jobId}/plan`);
        if (pRes.ok && !cancelled) setPlan(await pRes.json());
      }
      if (m.artifacts.summary.ready) {
        const sumRes = await fetch(`/api/jobs/${jobId}/summary`);
        if (sumRes.ok && !cancelled) {
          const body = await sumRes.json();
          setSummary(body.markdown ?? "");
        }
      }
    };

    load();
    if (running) {
      const id = setInterval(load, 2000);
      return () => {
        cancelled = true;
        clearInterval(id);
      };
    }
    return () => {
      cancelled = true;
    };
  }, [jobId, running]);

  if (!jobId) {
    return (
      <div className="artifact-panel">
        <p className="activity-empty">Artifacts appear here during the run.</p>
      </div>
    );
  }

  const arts = manifest?.artifacts;
  const tabs: { id: Tab; label: string; ready: boolean }[] = [
    { id: "reel", label: "Highlight", ready: !!arts?.video.ready },
    { id: "cv1", label: "CV-1 Shots", ready: !!arts?.cv1_shots.ready },
    { id: "cv2", label: "CV-2 Frames", ready: !!arts?.cv2_keyframes.ready },
    { id: "plan", label: "Plan", ready: !!arts?.plan.ready },
  ];

  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <p className="governance-label">Session artifacts</p>
        <p className="activity-sub">Stored on disk for this job · no database</p>
      </div>
      <div className="artifact-tabs" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`artifact-tab ${tab === t.id ? "artifact-tab-active" : ""} ${t.ready ? "artifact-tab-ready" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {t.ready && <span className="artifact-dot" />}
          </button>
        ))}
      </div>

      <div className="artifact-body">
        {tab === "reel" && (
          arts?.video.ready && arts.video.url ? (
            <video className="artifact-video" controls src={arts.video.url} />
          ) : (
            <p className="activity-empty">Highlight reel renders last…</p>
          )
        )}

        {tab === "cv1" && (
          shotsData.shots.length > 0 ? (
            <ShotGallery shots={shotsData.shots} previews={shotsData.previews} />
          ) : (
            <p className="activity-empty">Waiting for shot detection…</p>
          )
        )}

        {tab === "cv2" && (
          <div className="keyframe-grid">
            {(arts?.cv2_keyframes.items ?? []).map((kf) => (
              <figure key={kf.path} className="keyframe-card">
                <img src={kf.url} alt={`Window ${kf.window_id}`} loading="lazy" />
                <figcaption>w{kf.window_id}</figcaption>
              </figure>
            ))}
            {!arts?.cv2_keyframes.ready && (
              <p className="activity-empty">Keyframes appear after agent picks…</p>
            )}
          </div>
        )}

        {tab === "plan" && (
          plan ? (
            <div className="plan-artifact">
              <p>
                Skill <strong>{plan.skill}</strong> · {plan.moments.length} moments · target{" "}
                {plan.target_seconds}s
              </p>
              <ul className="plan-list">
                {plan.moments.map((m, i) => (
                  <li key={i}>
                    <strong>{m.label ?? "moment"}</strong> ({m.clip.start.toFixed(1)}–
                    {m.clip.end.toFixed(1)}s) — {m.reason}
                  </li>
                ))}
              </ul>
              {summary && <pre className="activity-json plan-summary">{summary}</pre>}
              {arts?.cv3_dedup.ready && (
                <p className="field-hint">{arts.cv3_dedup.note}</p>
              )}
            </div>
          ) : (
            <p className="activity-empty">Plan available after agent + CV stages…</p>
          )
        )}
      </div>
    </div>
  );
}
