import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

const MODE_LABELS = {
  auto: "Otomatik (DFS varsa önce, yoksa ücretsiz)",
  free: "Sadece ücretsiz",
  dataforseo: "Sadece DataForSEO",
};

/**
 * @param {object} props
 * @param {string} props.category - backlink | domain | rank | serp | keyword | ai_overview
 * @param {string} [props.label]
 * @param {function} [props.onChange] - (mode) => void
 * @param {boolean} [props.compact]
 */
export default function ProviderSelector({ category, label, onChange, compact = false }) {
  const [mode, setMode] = useState("auto");
  const [health, setHealth] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await API.get("/api/provider-settings");
      const s = res.data?.settings || {};
      setMode(s[category] || "auto");
      setHealth(res.data?.health);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    }
  }, [category]);

  useEffect(() => {
    load();
  }, [load]);

  const handleChange = async (next) => {
    setMode(next);
    setSaving(true);
    setError("");
    try {
      await API.post("/api/provider-settings", { [category]: next });
      await load();
      onChange?.(next);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const catHealth = health?.categories?.[category];
  const dfsOk = health?.dataforseo_configured;

  if (compact) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
        <label style={{ fontSize: "0.85rem", fontWeight: 600 }}>{label || "Provider"}:</label>
        <select
          value={mode}
          onChange={(e) => handleChange(e.target.value)}
          disabled={saving}
          style={{ padding: "0.35rem 0.5rem", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg2)", color: "var(--text)" }}
        >
          <option value="auto">Otomatik</option>
          <option value="free">Ücretsiz</option>
          <option value="dataforseo">DataForSEO</option>
        </select>
        {dfsOk ? <span style={{ fontSize: "0.75rem", color: "var(--ok)" }}>DFS ✓</span> : <span style={{ fontSize: "0.75rem", color: "var(--text2)" }}>DFS —</span>}
        {error && <span style={{ fontSize: "0.75rem", color: "var(--error)" }}>{error}</span>}
      </div>
    );
  }

  return (
    <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", marginBottom: "1rem" }}>
      <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem" }}>{label || "Provider Tercihi"}</h4>
      <p style={{ fontSize: "0.8rem", color: "var(--text2)", marginBottom: "0.75rem" }}>
        DataForSEO opsiyonel — API Ayarlarından login/password ekleyin. Seçim tüm panelde geçerlidir.
      </p>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
        {["auto", "free", "dataforseo"].map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => handleChange(m)}
            disabled={saving}
            style={{
              padding: "0.4rem 0.75rem",
              borderRadius: 6,
              border: mode === m ? "2px solid var(--accent)" : "1px solid var(--border)",
              background: mode === m ? "var(--bg2)" : "transparent",
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>
      <div style={{ fontSize: "0.78rem", color: "var(--text2)" }}>
        DataForSEO: {dfsOk ? "✓ yapılandırılmış" : "○ anahtar yok (ücretsiz fallback)"}
        {catHealth?.chain?.length > 0 && <> · Zincir: {catHealth.chain.join(" → ")}</>}
      </div>
      {error && <p style={{ color: "var(--error)", fontSize: "0.8rem", marginTop: "0.5rem" }}>{error}</p>}
    </div>
  );
}

export function ProviderSettingsPanel() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    API.get("/api/provider-settings/health").then((r) => setHealth(r.data)).catch(() => {});
  }, []);

  const cats = [
    { id: "backlink", label: "Backlink" },
    { id: "domain", label: "Domain" },
    { id: "rank", label: "Sıra Takibi" },
    { id: "serp", label: "SERP" },
    { id: "keyword", label: "Keyword" },
    { id: "ai_overview", label: "AI Overview" },
  ];

  return (
    <div>
      <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Provider Tercihleri</h3>
      {cats.map((c) => (
        <ProviderSelector key={c.id} category={c.id} label={c.label} />
      ))}
      {health && (
        <p style={{ fontSize: "0.8rem", color: "var(--text2)" }}>
          DataForSEO durumu: {health.dataforseo_configured ? "Bağlı" : "Yapılandırılmamış — ücretsiz modlar çalışmaya devam eder"}
        </p>
      )}
    </div>
  );
}
