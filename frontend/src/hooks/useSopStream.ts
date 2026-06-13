import { useState, useCallback, useRef } from "react";

export function useSopStream() {
  const [content, setContent] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const start = useCallback((taskId: string) => {
    setContent("");
    setError(null);
    setStreaming(true);

    const es = new EventSource(`/api/sop/stream/${taskId}`);
    esRef.current = es;

    es.onmessage = (event) => {
      if (event.data === "__DONE__") {
        setStreaming(false);
        es.close();
        return;
      }
      if (event.data === "__ERROR__") {
        setError("Generation failed. Please try again.");
        setStreaming(false);
        es.close();
        return;
      }
      setContent((prev) => prev + event.data);
    };

    es.onerror = () => {
      setStreaming(false);
      es.close();
    };
  }, []);

  const stop = useCallback(() => {
    esRef.current?.close();
    setStreaming(false);
  }, []);

  return { content, streaming, error, start, stop };
}
