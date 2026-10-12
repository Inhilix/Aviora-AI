import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";

const DOC_TYPES = ["transcript", "ielts", "passport", "sop", "lor", "financial", "other"];

type Doc = {
  id: string;
  doc_type: string;
  file_name: string;
  file_size_bytes: number;
  uploaded_at: string;
  is_sensitive: boolean;
  has_blurred_preview: boolean;
  is_image: boolean;
};

export default function Documents() {
  const queryClient = useQueryClient();
  const [docType, setDocType] = useState("transcript");
  const [file, setFile] = useState<File | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);

  const { data: docs } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get("/documents/").then((r) => r.data as Doc[]),
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

  const activeDoc = docs?.find((d) => d.id === previewId) ?? null;
  const previewUrl =
    activeDoc && activeDoc.is_image
      ? `/api/documents/${activeDoc.id}/preview?reveal=${revealed ? "true" : "false"}`
      : null;

  const openPreview = (doc: Doc) => {
    setPreviewId(doc.id);
    // Sensitive docs start blurred; non-sensitive images show clear.
    setRevealed(!doc.is_sensitive);
  };

  const closePreview = () => {
    setPreviewId(null);
    setRevealed(false);
  };

  return (
    <div>
      <h1>Documents</h1>
      <p className="doc-privacy-note">
        Sensitive uploads (passport, financial, transcript, IELTS, LOR) show a blurred
        preview by default so details stay private on shared screens.
      </p>

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
              <tr>
                <th align="left">Type</th>
                <th align="left">File</th>
                <th align="left">Size</th>
                <th align="left">Privacy</th>
                <th align="left">Uploaded</th>
                <th align="left"></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.doc_type}</td>
                  <td>{d.file_name}</td>
                  <td>{(d.file_size_bytes / 1024).toFixed(1)} KB</td>
                  <td>
                    {d.is_sensitive ? (
                      <span className="privacy-badge privacy-blurred">Blurred preview</span>
                    ) : (
                      <span className="privacy-badge privacy-clear">Standard</span>
                    )}
                  </td>
                  <td>{new Date(d.uploaded_at).toLocaleDateString()}</td>
                  <td>
                    {d.is_image ? (
                      <button className="btn btn-secondary" type="button" onClick={() => openPreview(d)}>
                        Preview
                      </button>
                    ) : (
                      <a className="btn btn-secondary" href={`/api/documents/${d.id}/download`}>
                        Download
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p>No documents uploaded yet.</p>}
      </div>

      {activeDoc && previewUrl && (
        <div className="preview-overlay" role="dialog" aria-modal="true" aria-label="Document preview">
          <div className="preview-panel">
            <div className="preview-header">
              <div>
                <strong>{activeDoc.file_name}</strong>
                <div className="preview-meta">{activeDoc.doc_type}</div>
              </div>
              <div className="preview-actions">
                {activeDoc.is_sensitive && (
                  <button
                    className="btn"
                    type="button"
                    onClick={() => setRevealed((v) => !v)}
                  >
                    {revealed ? "Blur again" : "Reveal (private)"}
                  </button>
                )}
                <a className="btn btn-secondary" href={`/api/documents/${activeDoc.id}/download`}>
                  Download original
                </a>
                <button className="btn btn-secondary" type="button" onClick={closePreview}>
                  Close
                </button>
              </div>
            </div>
            {activeDoc.is_sensitive && !revealed && (
              <p className="preview-blur-hint">
                Showing blurred preview — reveal only when you are on a private screen.
              </p>
            )}
            <div className={`preview-frame ${activeDoc.is_sensitive && !revealed ? "is-blurred" : ""}`}>
              <img
                key={previewUrl}
                src={previewUrl}
                alt={`${activeDoc.doc_type} preview`}
                className="preview-image"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
