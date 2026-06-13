import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import api from "../api/client";

function scoreClass(band?: string) {
  if (!band) return "";
  return "score-" + band.toLowerCase().replace(" ", "-");
}

export default function Dashboard() {
  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.get("/students/me").then((r) => r.data),
  });

  const { data: score } = useQuery({
    queryKey: ["score"],
    queryFn: () => api.get("/profile/score").then((r) => r.data),
    retry: false,
  });

  const { data: checklist } = useQuery({
    queryKey: ["checklist"],
    queryFn: () => api.get("/documents/checklist").then((r) => r.data),
  });

  return (
    <div>
      <h1>Welcome{me ? `, ${me.full_name}` : ""}</h1>

      <div className="card">
        <h3>Profile Score</h3>
        {score ? (
          <>
            <span className={`score-badge ${scoreClass(score.band)}`}>
              {score.total}/100 — {score.band}
            </span>
            <div style={{ marginTop: 12, fontSize: 14, color: "var(--muted)" }}>
              GPA: {score.breakdown?.gpa}/40 · IELTS: {score.breakdown?.ielts}/30 ·
              Financial: {score.breakdown?.financial}/20 · Experience: {score.breakdown?.experience}/10
            </div>
          </>
        ) : (
          <p>
            Complete your <Link to="/profile">profile</Link> to see your score.
          </p>
        )}
      </div>

      <div className="card">
        <h3>Document Checklist</h3>
        {checklist ? (
          <ul>
            {checklist.required.map((doc: string) => (
              <li key={doc}>
                {checklist.uploaded.includes(doc) ? "✅" : "⬜️"} {doc}
              </li>
            ))}
          </ul>
        ) : (
          <p>Loading...</p>
        )}
        <Link to="/documents" className="btn" style={{ display: "inline-block", marginTop: 8 }}>
          Manage Documents
        </Link>
      </div>

      <div className="card">
        <h3>Quick Actions</h3>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link to="/universities" className="btn">Find Universities</Link>
          <Link to="/sop" className="btn">Generate SOP</Link>
          <Link to="/interview" className="btn">Mock Interview</Link>
          <Link to="/visa" className="btn">Visa Guidance</Link>
        </div>
      </div>
    </div>
  );
}
