import { Link, Outlet, useLocation } from "react-router-dom";

export function Shell() {
  const { pathname } = useLocation();
  const onStudio = pathname.startsWith("/studio");

  return (
    <div className="page">
      <header className="topbar grid-cell">
        <Link to="/" className="logo">
          <span className="logo-mark" aria-hidden />
          ReelBite
        </Link>
        <nav className="nav">
          {!onStudio && <a href="/#pipeline">Pipeline</a>}
          <Link to="/studio">Studio</Link>
        </nav>
        <Link className="btn btn-accent btn-sm" to="/studio">
          Open studio
        </Link>
      </header>
      <Outlet />
      <footer className="footer grid-cell">
        <span>ReelBite · Agentic Highlight Maker</span>
        <span>GROQ_API_KEY in server .env</span>
      </footer>
    </div>
  );
}
