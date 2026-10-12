import { Link } from "react-router-dom";
import { WireTunnel } from "../components/WireTunnel";

const TAGS = [
  "Whisper",
  "Groq",
  "LangGraph",
  "PySceneDetect",
  "OpenCV",
  "pHash",
  "ffmpeg",
  "Skills",
];

export function Landing() {
  return (
    <>
      <section className="hero grid-cell">
        <div className="hero-copy">
          <h1 className="hero-title">
            <span className="hero-slash" aria-hidden />
            <span>Agentic</span>
            <span>highlights</span>
            <span>from long</span>
            <span>match video</span>
          </h1>
          <p className="hero-lead">
            Upload your match or talk. The agent picks the right skill, finds
            peaks in commentary, and CV cleans the cuts.
          </p>
          <div className="hero-actions">
            <Link className="btn btn-accent" to="/studio">
              Make highlights
            </Link>
            <Link className="btn btn-ghost" to="/doc">
              Read the doc
            </Link>
          </div>
        </div>
        <div className="hero-visual grid-inner">
          <WireTunnel />
        </div>
      </section>

      <div className="tag-row grid-cell">
        {TAGS.map((t, i) => (
          <span key={t} className="tag" style={{ ["--rot" as string]: `${(i % 5) - 2}deg` }}>
            {t}
          </span>
        ))}
      </div>

      <section className="trust grid-cell">
        <div className="trust-block">
          <strong>CV-1</strong>
          <span>Shot boundaries</span>
        </div>
        <div className="trust-block">
          <strong>CV-2</strong>
          <span>Keyframe score</span>
        </div>
        <div className="trust-block">
          <strong>CV-3</strong>
          <span>pHash dedup</span>
        </div>
        <div className="trust-block trust-accent">
          <span className="gear" aria-hidden />
          Skills loaded from disk — router picks playbook automatically.
        </div>
      </section>
    </>
  );
}
