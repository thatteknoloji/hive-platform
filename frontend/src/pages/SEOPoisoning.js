import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

const API_PREFIX = "/api/seo-poisoning";

function apiError(e) {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : e?.message || "İstek başarısız";
}

export default function SEOPoisoning() {
  const [health, setHealth] = useState(null);
  const [domain, setDomain] = useState("");
  const [keywords, setKeywords] = useState("dolandırıcı, şikayet, güvenilir mi");
  const [platforms, setPlatforms] = useState("medium,wordpress,blogger");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [campaigns, setCampaigns] = useState(null);

  const refreshHealth = useCallback(async () => {
    try {
      const r = await API.get(`${API_PREFIX}/health`);
      setHealth(r.data);
    } catch (e) {
      setHealth({ error: apiError(e) });
    }
  }, []);

  useEffect(() => { refreshHealth(); }, [refreshHealth]);

  const runCampaign = async () => {
    if (!domain.trim()) {
      setError("Hedef domain gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const kw = keywords.split(",").map((k) => k.trim()).filter(Boolean);
      const plats = platforms.split(",").map((p) => p.trim()).filter(Boolean);
      const r = await API.post(`${API_PREFIX}/campaign`, {
        target_domain: domain.trim(),
        keywords: kw,
        platforms: plats,
      });
      setResult(r.data);
      refreshHealth();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadCampaigns = async () => {
    try {
      const r = await API.get(`${API_PREFIX}/campaigns`);
      setCampaigns(r.data);
    } catch (e) {
      setError(apiError(e));
    }
  };

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">☠️</div>
        <div className="info">
          <h2>SEO Poisoning</h2>
          <p>Ollama ile içerik üret → Medium, WordPress, Blogger'a yayınla.</p>
        </div>
      </div>

      <div className="hive-alert" style={{ background: "rgba(180,0,0,0.2)", border: "2px solid #c00", padding: "1rem", borderRadius: 8, marginBottom: "1rem", fontWeight: 600 }}>
        ⚠️ ETİK UYARI: Bu modül yalnızca yetkili test ortamları içindir. Yanıltıcı içerik yayınlamak tamamen kullanıcının sorumluluğundadır.
      </div>

      {health && (
        <div style={{ marginBottom: "1rem", fontSize: "0.85rem" }}>
          Medium: {health.medium_configured ? "✓" : "✗"} · WordPress: {health.wordpress_configured ? "✓" : "✗"} · Blogger: {health.blogger_configured ? "✓" : "✗"}
        </div>
      )}

      {error && <div className="hata">{error}</div>}

      <div className="talon-form">
        <div className="form-grup">
          <label>Hedef Domain</label>
          <input value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="rakipsitesi.com" />
        </div>
        <div className="form-grup">
          <label>Keywords (virgülle)</label>
          <input value={keywords} onChange={(e) => setKeywords(e.target.value)} />
        </div>
        <div className="form-grup">
          <label>Platformlar</label>
          <input value={platforms} onChange={(e) => setPlatforms(e.target.value)} placeholder="medium,wordpress,blogger" />
        </div>
        <button className="btn btn-danger" onClick={runCampaign} disabled={loading}>
          {loading ? "Çalışıyor…" : "☠️ İçerik Üret ve Yayınla"}
        </button>
        <button className="btn btn-outline" style={{ marginLeft: "0.5rem" }} onClick={loadCampaigns}>
          Geçmiş
        </button>
      </div>

      {result && (
        <pre style={{ marginTop: "1rem", fontSize: "0.8rem", whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
      {campaigns && (
        <pre style={{ marginTop: "1rem", fontSize: "0.8rem", whiteSpace: "pre-wrap", maxHeight: 300, overflow: "auto" }}>
          {JSON.stringify(campaigns, null, 2)}
        </pre>
      )}
    </div>
  );
}
