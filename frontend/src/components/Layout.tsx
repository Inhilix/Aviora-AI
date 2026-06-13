import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/profile", label: "My Profile" },
  { to: "/universities", label: "Universities" },
  { to: "/documents", label: "Documents" },
  { to: "/sop", label: "SOP Generator" },
  { to: "/interview", label: "Mock Interview" },
  { to: "/visa", label: "Visa Guidance" },
];

export default function Layout() {
  return (
    <div className="layout">
      <nav className="sidebar">
        <h2 style={{ fontSize: 18, marginBottom: 24 }}>StudyAI</h2>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
