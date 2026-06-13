import { useQuery, useMutation } from "@tanstack/react-query";
import api from "../api/client";

export default function Universities() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["shortlist"],
    queryFn: () => api.get("/universities/shortlist").then((r) => r.data),
    retry: false,
  });

  const applyMutation = useMutation({
    mutationFn: (university_id: string) => api.post("/applications/", { university_id }),
    onSuccess: () => alert("Application created — track it from your dashboard"),
    onError: (err: any) => alert(err.response?.data?.detail || "Failed to create application"),
  });

  if (isLoading) return <p>Loading matches...</p>;
  if (error) return <p>Complete your profile first to see matched universities.</p>;

  return (
    <div>
      <h1>Recommended Universities</h1>
      <p style={{ color: "var(--muted)" }}>Ranked by fit with your academic profile and budget.</p>

      {data?.map((uni: any) => (
        <div key={uni.id} className="card">
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <h3 style={{ margin: 0 }}>{uni.name}</h3>
              <p style={{ margin: "4px 0", color: "var(--muted)" }}>
                {uni.course_name} · {uni.city}, {uni.country}
              </p>
            </div>
            <span className="score-badge score-strong">{uni.match_score}% match</span>
          </div>
          <div style={{ display: "flex", gap: 24, fontSize: 14, margin: "12px 0", flexWrap: "wrap" }}>
            <span>QS Rank: {uni.qs_ranking ?? "N/A"}</span>
            <span>Tuition: ${uni.annual_tuition_usd?.toLocaleString()}/yr</span>
            <span>Min GPA: {uni.min_gpa}</span>
            <span>Min IELTS: {uni.min_ielts}</span>
            <span>Visa approval: {uni.visa_approval_rate_pct}%</span>
            <span>Deadline: {uni.application_deadline ?? "Rolling"}</span>
          </div>
          <button className="btn" onClick={() => applyMutation.mutate(uni.id)}>
            Track this Application
          </button>
        </div>
      ))}

      {data?.length === 0 && <p>No matches found for your current profile and target countries.</p>}
    </div>
  );
}
