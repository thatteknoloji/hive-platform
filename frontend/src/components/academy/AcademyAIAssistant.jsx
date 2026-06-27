import React, { useState } from "react";
import API from "../../api";

const API_PREFIX = "/api/academy";

export default function AcademyAIAssistant({ slug, collapsed, onToggle }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);

  const ask = async (q) => {
    const text = (q || query).trim();
    if (!text) return;
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/ai-assist`, { query: text, slug });
      setAnswer(res.data.answer || "");
      setSources(res.data.sources || []);
    } catch {
      setAnswer("Academy AI şu an yanıt veremiyor.");
      setSources([]);
    } finally {
      setLoading(false);
    }
  };

  if (collapsed) {
    return (
      <button type="button" className="ha-ai-toggle" onClick={onToggle} title="Academy AI">
        🤖
      </button>
    );
  }

  return (
    <aside className="ha-ai-panel">
      <div className="ha-ai-header">
        <h4>🤖 Academy AI</h4>
        <button type="button" className="ha-link-btn" onClick={onToggle}>Kapat</button>
      </div>
      <p className="ha-muted">Yalnızca Academy bilgisini kullanır. İnternet yok.</p>
      <div className="ha-ai-quick">
        <button type="button" className="ha-btn" onClick={() => ask("Bunu anlamadım")}>Bunu anlamadım</button>
        <button type="button" className="ha-btn" onClick={() => ask(`${slug} özeti`)}>Özetle</button>
      </div>
      <textarea
        rows={3}
        placeholder="Sorunuzu yazın…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button type="button" className="ha-btn primary" disabled={loading} onClick={() => ask()}>
        {loading ? "…" : "Sor"}
      </button>
      {answer && (
        <div className="ha-ai-answer">
          <p>{answer}</p>
          {sources.length > 0 && (
            <ul className="ha-ai-sources">
              {sources.map((s) => (
                <li key={s.slug}>{s.title} — {s.section}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <p className="ha-muted ha-ai-priority">Öncelik: Academy → Ansiklopedi → Workflow → API</p>
    </aside>
  );
}
