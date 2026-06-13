import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "../api/client";

const COUNTRIES = ["UK", "Canada", "Australia", "Germany", "USA"];

interface Result { answer: string; sources: { topic: string; country: string }[] }

export default function VisaGuidance() {
  const [question, setQuestion] = useState("");
  const [country, setCountry] = useState("");
  const [results, setResults] = useState<{ q: string; r: Result }[]>([]);

  const askMutation = useMutation({
    mutationFn: () =>
      api.post("/visa/ask", { message: question }, { params: country ? { country } : {} }).then((r) => r.data),
    onSuccess: (data) => {
      setResults((prev) => [{ q: question, r: data }, ...prev]);
      setQuestion("");
    },
    onError: (err: any) => alert(err.response?.data?.detail || "Could not get an answer"),
  });

  return (
    <div>
      <h1>Visa & Admission Guidance</h1>
      <p style={{ color: "var(--muted)" }}>
        Ask questions about visa requirements, documents, IELTS, or financial proof —
        answers are grounded in our country-specific knowledge base.
      </p>

      <div className="card">
        <label>Country (optional — narrows search)</label>
        <select value={country} onChange={(e) => setCountry(e.target.value)}>
          <option value="">All countries</option>
          {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>

        <label>Your question</label>
        <textarea
          rows={3}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What documents do I need for a Canada study permit?"
          maxLength={2000}
        />
        <button
          className="btn"
          disabled={!question.trim() || askMutation.isPending}
          onClick={() => askMutation.mutate()}
        >
          {askMutation.isPending ? "Searching..." : "Ask"}
        </button>
        <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
          Limited to 10 questions/minute, 100/hour.
        </p>
      </div>

      {results.map((item, i) => (
        <div key={i} className="card">
          <p style={{ fontWeight: 600 }}>Q: {item.q}</p>
          <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{item.r.answer}</div>
          {item.r.sources.length > 0 && (
            <div style={{ marginTop: 12, fontSize: 12, color: "var(--muted)" }}>
              Sources: {item.r.sources.map((s) => `${s.topic} (${s.country})`).join(", ")}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
