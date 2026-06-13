import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "../api/client";

interface Message { role: "user" | "assistant"; content: string }

export default function MockInterview() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hello, I'll be conducting your mock visa interview today. Please tell me — which university and course have you been accepted to?" },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);

  const sendMutation = useMutation({
    mutationFn: (message: string) =>
      api.post("/interview/message", { message, session_id: sessionId }).then((r) => r.data),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setMessages((m) => [...m, { role: "assistant", content: data.response }]);
    },
    onError: (err: any) => {
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${err.response?.data?.detail || "Error processing message"}` }]);
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend() {
    if (!input.trim()) return;
    setMessages((m) => [...m, { role: "user", content: input }]);
    sendMutation.mutate(input);
    setInput("");
  }

  return (
    <div>
      <h1>Mock Visa Interview</h1>
      <p style={{ color: "var(--muted)" }}>
        Practice answering common student visa interview questions. Limited to 5 messages/minute.
      </p>

      <div className="card" style={{ minHeight: 400, display: "flex", flexDirection: "column" }}>
        <div style={{ flex: 1, overflowY: "auto", maxHeight: 450 }}>
          {messages.map((m, i) => (
            <div key={i} className={`chat-message ${m.role}`}>{m.content}</div>
          ))}
          {sendMutation.isPending && <div className="chat-message assistant">Thinking...</div>}
          <div ref={bottomRef} />
        </div>

        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Type your answer..."
            style={{ marginBottom: 0 }}
            maxLength={2000}
          />
          <button className="btn" onClick={handleSend} disabled={sendMutation.isPending}>Send</button>
        </div>
      </div>
    </div>
  );
}
