import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";



export default function IndexingFix() {
  const [audit, setAudit] = useState(null);
  const [fixResult, setFixResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [site, setSite] = useProjectSiteField();

  const loadAudit = useCallback(async () => {
    setError("");
    try {
      const res = await API.get("/api/indexing/audit", { params: { site } });
      setAudit(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  }, [site]);

  useEffect(() => {
    loadAudit();
  }, [loadAudit]);

  const runFix = async () => {
    setLoading(true);
    setError("");
    setFixResult(null);
    try {
      const res = await API.post("/api/indexing/fix-all", { site });
      setFixResult(res.data);
      await loadAudit();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const submitIndexNow = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/indexing/indexnow", { site });
      setFixResult({ indexnow: res.data });
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const deployRobots = async () => {
    setLoading(true);
    setError("");
    setFixResult(null);
    try {
      const res = await API.post("/api/indexing/robots-deploy", { site });
      setFixResult(res.data);
      await loadAudit();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  return (
    <div className="modul-sayfa" style={{ padding: "1.5rem" }}>
      <h2>🔍 Google İndeksleme Düzeltici</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
        Seçili proje — SSL, permalink, noindex, robots, IndexNow ve sitemap otomasyonu
      </p>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <input
          value={site}
          onChange={(e) => setSite(e.target.value)}
          placeholder="https://example.com"
          style={{ flex: 1, minWidth: 240, padding: "0.5rem" }}
        />
        <button onClick={loadAudit} disabled={loading}>🔄 Denetle</button>
        <button onClick={runFix} disabled={loading} className="btn-primary">
          {loading ? "Çalışıyor…" : "⚡ Tümünü Düzelt"}
        </button>
        <button onClick={deployRobots} disabled={loading}>🤖 robots.txt Yükle</button>
        <button onClick={submitIndexNow} disabled={loading}>📤 IndexNow</button>
      </div>

      {error && <div className="hata-kutu" style={{ marginBottom: "1rem" }}>{error}</div>}

      {audit && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h3>Denetim — {audit.skor} {audit.hazir ? "✅" : "⚠️"}</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "0.4rem" }}>Kontrol</th>
                <th style={{ textAlign: "left" }}>Durum</th>
                <th style={{ textAlign: "left" }}>Detay</th>
              </tr>
            </thead>
            <tbody>
              {(audit.kontroller || []).map((c, i) => (
                <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                  <td style={{ padding: "0.4rem" }}>{c.kontrol}</td>
                  <td>{c.durum === "ok" ? "✅" : "❌"}</td>
                  <td style={{ color: "var(--text-muted)" }}>{c.detay}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {fixResult && (
        <div>
          <h3>Son işlem sonucu</h3>
          <pre style={{ background: "var(--bg-secondary)", padding: "1rem", overflow: "auto", fontSize: "0.8rem", borderRadius: 8 }}>
            {JSON.stringify(fixResult, null, 2)}
          </pre>
        </div>
      )}

      <div style={{ marginTop: "1.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
        <p><strong>Gerekli ayarlar:</strong> VPS_SSH_PASS, CLOUDFLARE_API_TOKEN (opsiyonel), GSC OAuth (opsiyonel)</p>
        <p>
          <a href="https://search.google.com/search-console" target="_blank" rel="noreferrer">
            Google Search Console
          </a>
          {" · "}
          <a href={`${site}/wp-sitemap.xml`} target="_blank" rel="noreferrer">Sitemap</a>
        </p>
      </div>
    </div>
  );
}
