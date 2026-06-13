import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api/client";

export default function Register() {
  const [form, setForm] = useState({ email: "", password: "", full_name: "", phone: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/auth/register", form);
      await api.post("/auth/login", { email: form.email, password: form.password });
      navigate("/profile");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed");
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: "60px auto" }}>
      <div className="card">
        <h2>Create your account</h2>
        <form onSubmit={handleSubmit}>
          <label>Full name</label>
          <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          <label>Email</label>
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <label>Phone (optional)</label>
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <label>Password (min 8 characters)</label>
          <input type="password" minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
          <button className="btn" type="submit">Register</button>
        </form>
        <p style={{ marginTop: 16, fontSize: 14 }}>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
