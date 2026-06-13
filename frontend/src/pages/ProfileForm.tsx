import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";

const COUNTRIES = ["UK", "Canada", "Australia", "Germany", "USA", "Italy", "Ireland", "Netherlands"];
const DEGREES = ["Bachelors", "Masters", "MBA", "PhD"];

export default function ProfileForm() {
  const queryClient = useQueryClient();
  const { data: existing } = useQuery({
    queryKey: ["profile"],
    queryFn: () => api.get("/profile/").then((r) => r.data),
    retry: false,
  });

  const [form, setForm] = useState({
    gpa: "",
    gpa_scale: "4.0",
    ielts_overall: "",
    ielts_writing: "",
    gap_years: "0",
    work_experience_months: "0",
    financial_proof_usd: "",
    target_countries: [] as string[],
    target_degree: "Masters",
    target_subject: "",
    budget_usd_per_year: "",
  });

  useEffect(() => {
    if (existing) {
      setForm({
        gpa: String(existing.gpa ?? ""),
        gpa_scale: String(existing.gpa_scale ?? "4.0"),
        ielts_overall: String(existing.ielts_overall ?? ""),
        ielts_writing: String(existing.ielts_writing ?? ""),
        gap_years: String(existing.gap_years ?? "0"),
        work_experience_months: String(existing.work_experience_months ?? "0"),
        financial_proof_usd: String(existing.financial_proof_usd ?? ""),
        target_countries: existing.target_countries ?? [],
        target_degree: existing.target_degree ?? "Masters",
        target_subject: existing.target_subject ?? "",
        budget_usd_per_year: String(existing.budget_usd_per_year ?? ""),
      });
    }
  }, [existing]);

  const mutation = useMutation({
    mutationFn: (payload: any) => api.post("/profile/", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["score"] });
      alert("Profile saved");
    },
  });

  function toggleCountry(c: string) {
    setForm((f) => ({
      ...f,
      target_countries: f.target_countries.includes(c)
        ? f.target_countries.filter((x) => x !== c)
        : [...f.target_countries, c],
    }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      gpa: parseFloat(form.gpa),
      gpa_scale: parseFloat(form.gpa_scale),
      ielts_overall: form.ielts_overall ? parseFloat(form.ielts_overall) : null,
      ielts_writing: form.ielts_writing ? parseFloat(form.ielts_writing) : null,
      gap_years: parseInt(form.gap_years),
      work_experience_months: parseInt(form.work_experience_months),
      financial_proof_usd: form.financial_proof_usd ? parseInt(form.financial_proof_usd) : null,
      target_countries: form.target_countries,
      target_degree: form.target_degree,
      target_subject: form.target_subject,
      budget_usd_per_year: form.budget_usd_per_year ? parseInt(form.budget_usd_per_year) : null,
    });
  }

  return (
    <div>
      <h1>My Academic Profile</h1>
      <form onSubmit={handleSubmit} className="card">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <label>GPA</label>
            <input type="number" step="0.01" value={form.gpa} onChange={(e) => setForm({ ...form, gpa: e.target.value })} required />
          </div>
          <div>
            <label>GPA Scale</label>
            <input type="number" step="0.1" value={form.gpa_scale} onChange={(e) => setForm({ ...form, gpa_scale: e.target.value })} />
          </div>
          <div>
            <label>IELTS Overall</label>
            <input type="number" step="0.5" value={form.ielts_overall} onChange={(e) => setForm({ ...form, ielts_overall: e.target.value })} />
          </div>
          <div>
            <label>IELTS Writing</label>
            <input type="number" step="0.5" value={form.ielts_writing} onChange={(e) => setForm({ ...form, ielts_writing: e.target.value })} />
          </div>
          <div>
            <label>Gap Years</label>
            <input type="number" value={form.gap_years} onChange={(e) => setForm({ ...form, gap_years: e.target.value })} />
          </div>
          <div>
            <label>Work Experience (months)</label>
            <input type="number" value={form.work_experience_months} onChange={(e) => setForm({ ...form, work_experience_months: e.target.value })} />
          </div>
          <div>
            <label>Financial Proof (USD)</label>
            <input type="number" value={form.financial_proof_usd} onChange={(e) => setForm({ ...form, financial_proof_usd: e.target.value })} />
          </div>
          <div>
            <label>Annual Budget (USD)</label>
            <input type="number" value={form.budget_usd_per_year} onChange={(e) => setForm({ ...form, budget_usd_per_year: e.target.value })} />
          </div>
          <div>
            <label>Target Degree</label>
            <select value={form.target_degree} onChange={(e) => setForm({ ...form, target_degree: e.target.value })}>
              {DEGREES.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label>Target Subject</label>
            <input value={form.target_subject} onChange={(e) => setForm({ ...form, target_subject: e.target.value })} placeholder="e.g. Computer Science" />
          </div>
        </div>

        <label style={{ marginTop: 12 }}>Target Countries</label>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          {COUNTRIES.map((c) => (
            <button
              type="button"
              key={c}
              onClick={() => toggleCountry(c)}
              className="btn"
              style={{
                background: form.target_countries.includes(c) ? "var(--primary)" : "var(--card)",
                color: form.target_countries.includes(c) ? "white" : "var(--text)",
                border: "1px solid var(--border)",
              }}
            >
              {c}
            </button>
          ))}
        </div>

        <button className="btn" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving..." : "Save Profile"}
        </button>
      </form>
    </div>
  );
}
