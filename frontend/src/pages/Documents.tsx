import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";

const DOC_TYPES = ["transcript", "ielts", "passport", "sop", "lor", "financial", "other"];

export default function Documents() {
  const queryClient = useQueryClient();
  const [docType, setDocType] = useState("transcript");
  const [file, setFile] = useState<File | null>(null);

  const { data: docs } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get("/documents/").then((r) => r.data),
  });

  const { data: checklist } = useQuery({
    queryKey: ["checklist"],
    queryFn: () => api.get("/documents/checklist").then((r) => r.data),
  });

  const uploadMutation = useMutation({
    mutationFn: () => {
      const formData = new FormData();
      formData.append("doc_type", docType);
      formData.append("file", file!);
      return api.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["checklist"] });
      setFile(null);
    },
    onError: (err: any) => alert(err.response?.data?.detail || "Upload failed"),
  });

  return (
    <div>
      <h1>Documents</h1>

      <div className="card">
        <h3>Checklist</h3>
        {checklist && (
          <ul>
            {checklist.required.map((d: string) => (
              <li key={d}>{checklist.uploaded.includes(d) ? "✅" : "⬜️"} {d}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h3>Upload Document</h3>
        <label>Document Type</label>
        <select value={docType} onChange={(e) => setDocType(e.target.value)}>
          {DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <label>File (max 10MB)</label>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button className="btn" disabled={!file || uploadMutation.isPending} onClick={() => uploadMutation.mutate()}>
          {uploadMutation.isPending ? "Uploading..." : "Upload"}
        </button>
      </div>

      <div className="card">
        <h3>Uploaded Files</h3>
        {docs?.length ? (
          <table style={{ width: "100%", fontSize: 14 }}>
            <thead>
              <tr><th align="left">Type</th><th align="left">File</th><th align="left">Size</th><th align="left">Uploaded</th></tr>
            </thead>
            <tbody>
              {docs.map((d: any) => (
                <tr key={d.id}>
                  <td>{d.doc_type}</td>
                  <td>{d.file_name}</td>
                  <td>{(d.file_size_bytes / 1024).toFixed(1)} KB</td>
                  <td>{new Date(d.uploaded_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p>No documents uploaded yet.</p>}
      </div>
    </div>
  );
}
