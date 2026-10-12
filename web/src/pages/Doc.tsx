import { Link } from "react-router-dom";

const STAGES: {
  id: string;
  name: string;
  tech: string;
  inOut: string;
  why: string;
}[] = [
  {
    id: "audio",
    name: "Audio extract",
    tech: "ffmpeg",
    inOut: "Video → 16 kHz mono FLAC",
    why: "Feeds Whisper and loudness analysis without shipping full video to STT.",
  },
  {
    id: "transcribe",
    name: "Transcribe",
    tech: "Groq Whisper (large-v3-turbo)",
    inOut: "Audio → timestamped transcript JSON",
    why: "Commentary text drives what moments matter (goals, wickets, excitement).",
  },
  {
    id: "energy",
    name: "Audio energy",
    tech: "numpy / ffmpeg samples",
    inOut: "Audio → per-second RMS z-score",
    why: "Crowd roar and peak volume align with highlights even when words are sparse.",
  },
  {
    id: "cv1",
    name: "CV-1 · Shots",
    tech: "PySceneDetect ContentDetector",
    inOut: "Video → shot boundaries JSON + preview thumbnails",
    why: "Cuts land on clean scene changes, not mid-action frames.",
  },
  {
    id: "windows",
    name: "Windows",
    tech: "Python merge",
    inOut: "Transcript + energy → ~10–30 s scoring windows",
    why: "Agent scores manageable chunks instead of the full 30-minute transcript at once.",
  },
  {
    id: "agent",
    name: "Agent",
    tech: "LangGraph + Groq (router + scorer + critic)",
    inOut: "Windows + skills on disk → ranked moments",
    why: "Router picks cricket/football/generic skill; scorer uses tools; critic fixes duration and diversity.",
  },
  {
    id: "cv2",
    name: "CV-2 · Keyframes",
    tech: "OpenCV (Laplacian sharpness, motion, brightness)",
    inOut: "Each clip → best 1–3 frames on disk",
    why: "Representative stills for the plan; drops blur, black, and transition frames.",
  },
  {
    id: "cv3",
    name: "CV-3 · Dedup",
    tech: "pHash + Hamming distance",
    inOut: "Moments → replay duplicates removed",
    why: "Same goal live + replay does not appear twice in the reel.",
  },
  {
    id: "render",
    name: "Render",
    tech: "ffmpeg concat",
    inOut: "Clips + source audio → highlights.mp4",
    why: "Final reel with original commentary audio in sync.",
  },
];

export function Doc() {
  return (
    <section className="doc-page grid-cell">
      <div className="doc-head">
        <div className="studio-head-row">
          <Link to="/" className="btn btn-ghost btn-sm studio-back">
            ← Home
          </Link>
          <h1>How ReelBite works</h1>
        </div>
        <p className="doc-lead">
          Walkthrough of the pipeline, what each stage uses, and where artifacts land on disk. Use{" "}
          <Link to="/studio">Studio</Link> to run a job and inspect live activity.
        </p>
      </div>

      <div className="doc-grid">
        <article className="doc-card">
          <h2>End-to-end flow</h2>
          <ol className="doc-flow">
            <li>Upload a long match video in Studio (target highlight length 60–300 s).</li>
            <li>Backend runs stages in order; progress and tool calls stream to Live activity.</li>
            <li>Agent loads sport skills from <code>skills/*/SKILL.md</code> (router picks one).</li>
            <li>CV snaps agent picks to shots, scores keyframes, dedups replays.</li>
            <li>Output: <code>highlights.mp4</code>, plan, summary, transcript, shots, keyframes.</li>
          </ol>
        </article>

        <article className="doc-card">
          <h2>Who does what</h2>
          <ul className="doc-roles">
            <li>
              <strong>Transcript + energy</strong> — when something exciting happened.
            </li>
            <li>
              <strong>LLM agent + skills</strong> — which windows become highlights and why.
            </li>
            <li>
              <strong>CV-1 / CV-2 / CV-3</strong> — where to cut and which frames represent each moment.
            </li>
          </ul>
        </article>
      </div>

      <h2 className="doc-section-title">Pipeline stages</h2>
      <div className="doc-stage-table-wrap">
        <table className="doc-stage-table">
          <thead>
            <tr>
              <th>Stage</th>
              <th>Technology</th>
              <th>Input → output</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {STAGES.map((s) => (
              <tr key={s.id}>
                <td>
                  <strong>{s.name}</strong>
                </td>
                <td>{s.tech}</td>
                <td>{s.inOut}</td>
                <td>{s.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="doc-grid doc-grid-3">
        <article className="doc-card">
          <h3>CV-1</h3>
          <p>PySceneDetect on the source video. Studio shows a shot timeline and thumbnail grid.</p>
        </article>
        <article className="doc-card">
          <h3>CV-2</h3>
          <p>OpenCV samples frames inside each chosen clip; highest sharpness wins.</p>
        </article>
        <article className="doc-card">
          <h3>CV-3</h3>
          <p>Perceptual hash compares keyframes; near-duplicates drop from the plan.</p>
        </article>
      </div>

      <article className="doc-card doc-storage">
        <h2>Storage (no database)</h2>
        <p>
          Each job lives under <code>work/jobs/&#123;job_id&#125;/</code>: source video,{" "}
          <code>work/*_transcript.json</code>, <code>*_shots.json</code>, <code>keyframes/</code>,{" "}
          <code>*_plan.json</code>, <code>events.jsonl</code>, <code>highlights.mp4</code>. Session
          history in Studio reads this folder list. Failed runs can <strong>Continue</strong> from
          cached stages.
        </p>
        <p>
          API keys: set <code>GROQ_API_KEY</code> in server <code>.env</code> (Docker or local
          uvicorn on port 8800).
        </p>
      </article>

      <div className="doc-actions">
        <Link className="btn btn-accent" to="/studio">
          Open Studio
        </Link>
      </div>
    </section>
  );
}
