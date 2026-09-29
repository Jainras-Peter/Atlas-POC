import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import AtlasChatPage from "./pages/AtlasChatPage";
import QuotesPage from "./pages/QuotesPage";
import UsersPage from "./pages/UsersPage";

const TITLES: Record<string, { title: string; subtitle: string } | null> = {
  "/": null, // Atlas page has its own header
  "/users": {
    title: "Customers",
    subtitle: "Imported by Sales agent · Today / Yesterday / Older",
  },
  "/quotes": {
    title: "Quotes",
    subtitle: "Quotes created for CRM customers",
  },
};

export default function App() {
  const { pathname } = useLocation();
  const meta = TITLES[pathname];
  const isAtlas = pathname === "/";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">QA</div>
          <div>
            <div className="brand-title">QuoteAI</div>
            <div className="brand-sub">Atlas workspace</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/" end>
            <span className="nav-dot" />
            Atlas
          </NavLink>
          <NavLink to="/users">Customers</NavLink>
          <NavLink to="/quotes">Quotes</NavLink>
        </nav>
      </aside>

      <div className="workspace">
        {!isAtlas && meta && (
          <header className="workspace-header">
            <div>
              <h1>{meta.title}</h1>
              <p>{meta.subtitle}</p>
            </div>
          </header>
        )}
        <main className={`workspace-main ${isAtlas ? "atlas-fill" : ""}`}>
          <Routes>
            <Route path="/" element={<AtlasChatPage />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/quotes" element={<QuotesPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
