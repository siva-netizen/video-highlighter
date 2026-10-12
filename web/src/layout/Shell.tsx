import { Link, Outlet, useLocation } from "react-router-dom";

export function Shell() {
  const { pathname } = useLocation();
  const onStudio = pathname.startsWith("/studio");
  const onDoc = pathname.startsWith("/doc");

  return (
    <div className="page">
      <header className="topbar grid-cell">
        <Link to="/" className="logo">
          <span className="logo-mark" aria-hidden />
          ReelBite
        </Link>
        <nav className="nav">
          {onStudio || onDoc ? (
            <Link to="/">Home</Link>
          ) : (
            <Link to="/doc">Doc</Link>
          )}
          {onStudio && <span className="nav-current">Studio</span>}
          {onDoc && <span className="nav-current">Doc</span>}
        </nav>
        {onStudio || onDoc ? (
          <Link className="btn btn-ghost btn-sm" to="/">
            ← Back
          </Link>
        ) : (
          <Link className="btn btn-accent btn-sm" to="/studio">
            Open studio
          </Link>
        )}
      </header>
      <Outlet />
      <footer className="footer grid-cell">
        <span>ReelBite · Agentic Highlight Maker</span>
        <span>Built by Precision and Recall</span>
      </footer>
    </div>
  );
}
