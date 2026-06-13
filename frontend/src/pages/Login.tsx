import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api/client";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/auth/login", { email, password });
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed");
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto" }}>
      <div className="card">
        <h2>Sign in to StudyAI</h2>
        <form onSubmit={handleSubmit}>
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
          <button className="btn" type="submit">Log in</button>
        </form>
        <p style={{ marginTop: 16, fontSize: 14 }}>
          No account? <Link to="/register">Register</Link>
        </p>
      </div>
    </div>
  );
}
