import React, { useEffect, useState } from "react";
import API from "../../api";
import { resolveModuleNavId } from "./academyConfig";

const API_PREFIX = "/api/academy";

const TYPE_ICONS = {
  doc: "📄",
  module: "🧩",
  api: "🔌",
  workflow: "⚡",
  video: "▶",
};

export default function AcademyCommandPalette({ open, onClose, onOpenDoc, onNavigateModule }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (!open) {
      setQ("");
      setResults([]);
    }
  }, [open]);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!q.trim()) {
        setResults([]);
        return;
      }
      try {
        const res = await API.get(`${API_PREFIX}/palette`, { params: { q } });
        setResults(res.data.results || []);
      } catch {
        setResults([]);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [q]);

  const activate = (r) => {
    if (r.type === "doc") onOpenDoc?.(r.id);
    else if (r.type === "module" || r.type === "api") {
      const navId = resolveModuleNavId(r.id);
      if (navId) onNavigateModule?.(navId);
    } else if (r.type === "workflow") onOpenDoc?.(r.id);
    onClose?.();
  };

  if (!open) return null;

  return (
    <div className="ha-global-search-overlay" onClick={onClose} role="presentation">
      <div className="ha-global-search ha-palette" onClick={(e) => e.stopPropagation()}>
        <h3>⌘K Command Palette</h3>
        <p className="ha-muted">Doküman · Modül · API · Workflow · Sorun · Video</p>
        <input
          autoFocus
          placeholder='Ara: "authority", "publish", "sorun"...'
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <ul>
          {results.map((r, i) => (
            <li key={`${r.type}-${r.id}-${i}`}>
              <button type="button" onClick={() => activate(r)}>
                <strong>{TYPE_ICONS[r.type] || "•"} {r.label}</strong>
                <span>{r.section} · {r.type}</span>
              </button>
            </li>
          ))}
          {q && !results.length && <li className="ha-muted" style={{ padding: 12 }}>Sonuç yok</li>}
        </ul>
        <p className="ha-muted ha-palette-hint">ESC ile kapat · Voice Search — yakında</p>
      </div>
    </div>
  );
}
