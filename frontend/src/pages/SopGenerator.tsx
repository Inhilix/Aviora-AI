import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "../api/client";
import { useSopStream } from "../hooks/useSopStream";

export default function SopGenerator() {
  const [universityId, setUniversityId] = useState("");
  const [context, setContext] = useState("");
  const { content, streaming, error, start } = useSopStream();

  const { data: universities } = useQuery({
    queryKey: ["universities-list"],
    queryFn: () => api.get("/universities/").then((r) => r.data),
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      api.post("/sop/generate", { university_id: universityId, additional_context: context || undefined }),
    onSuccess: (res) => {
      const taskId = res.data.task_id;
      start(taskId);
    },
    onError: (err: any) => alert(err.response?.data?.detail || "Failed to start generation"),
  });

  return (
    <div>
      <h1>SOP Generator</h1>

      <div className="card">
        <label>University</label>
        <select value={universityId} onChange={(e) => setUniversityId(e.target.value)}>
          <option value="">Select a university...</option>
          {universities?.map((u: any) => (
            <option key={u.id} value={u.id}>{u.name} — {u.course_name} ({u.country})</option>
          ))}
        </select>

        <label>Additional context (optional)</label>
        <textarea
          rows={4}
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Any specific achievements, projects, or motivations you want included..."
          maxLength={1000}
        />

        <button
          className="btn"
          disabled={!universityId || streaming || generateMutation.isPending}
          onClick={() => generateMutation.mutate()}
        >
          {streaming ? "Generating..." : "Generate SOP"}
        </button>
        <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
          Limited to 5 generations per minute, 50/hour, 200/day.
        </p>
      </div>

      {error && <div className="card" style={{ color: "var(--danger)" }}>{error}</div>}

      {(content || streaming) && (
        <div className="card">
          <h3>Draft</h3>
          <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: 15 }}>
            {content}
            {streaming && <span style={{ opacity: 0.5 }}>▋</span>}
          </div>
          {!streaming && content && (
            <button
              className="btn"
              style={{ marginTop: 12 }}
              onClick={() => navigator.clipboard.writeText(content)}
            >
              Copy to Clipboard
            </button>
          )}
        </div>
      )}
    </div>
  );
}
