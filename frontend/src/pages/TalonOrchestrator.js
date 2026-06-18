import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

const INTENT_LABELS = {
  informational: "Bilgilendirici",
  commercial: "Ticari",
  local: "Yerel",
  navigational: "Navigasyon",
  transactional: "İşlem",
  faq: "SSS",
  comparison: "Karşılaştırma",
};

const PAGE_TYPE_LABELS = {
  astro_landing: "Astro Landing",
  wordpress_page: "WordPress Sayfa",
  faq: "SSS",
  blog: "Blog",
  category: "Kategori",
  support_network: "Destek Ağı",
  no_publish: "Yayınlama",
};

export default function TalonOrchestrator({
  onNavigateAstro,
  onNavigatePageHub,
  onNavigateSSS,
  embedded = false,
}) {
  const [seedKeyword, setSeedKeyword] = useState("kuşadası gece hayatı");
  const [location, setLocation] = useState("Kuşadası");
  const [limit, setLimit] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [selectedKw, setSelectedKw] = useState(null);
  const [message, setMessage] = useState("");

  const loadHealth = useCallback(async () => {
    try {
      const res = await API.get("/api/talon/orchestrator/health");
      setHealth(res.data);
    } catch (e) {
      setHealth({ ready: false, error: e.message });
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  const runFullResearch = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    setResult(null);
    setSelectedKw(null);
    try {
      const res = await API.post("/api/talon/orchestrator/full-research", {
        seed_keyword: seedKeyword,
        location,
        limit,
      });
      setResult(res.data);
      if (res.data.keywords?.length) {
        setSelectedKw(res.data.keywords[0]);
      }
      setMessage(`Araştırma tamamlandı — ${res.data.keywords?.length || 0} keyword`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Araştırma başarısız");
    } finally {
      setLoading(false);
    }
  };

  const sendToAstro = () => {
    if (!result?.astro_factory_ready?.length) {
      setError("Astro Factory için hazır keyword yok");
      return;
    }
    sessionStorage.setItem(
      "talon_orchestrator_astro",
      JSON.stringify({
        seed_keyword: result.seed_keyword,
        location: result.location,
        keywords: result.astro_factory_ready,
        geo_pages: result.geo_pages,
      })
    );
    setMessage("Astro Factory verisi session'a kaydedildi");
    if (onNavigateAstro) onNavigateAstro();
  };

  const sendToPageHub = () => {
    if (!result?.page_hub_ready?.length) {
      setError("Page Hub için hazır keyword yok");
      return;
    }
    sessionStorage.setItem(
      "talon_orchestrator_page_hub",
      JSON.stringify({
        queue: result.page_hub_ready,
        seed_keyword: result.seed_keyword,
        location: result.location,
      })
    );
    setMessage("Page Hub kuyruğu session'a kaydedildi");
    if (onNavigatePageHub) onNavigatePageHub();
  };

  const sendToSSS = () => {
    if (!result?.sss_ready?.length && !result?.faq_questions?.length) {
      setError("SSS için hazır veri yok");
      return;
    }
    sessionStorage.setItem(
      "talon_orchestrator_sss",
      JSON.stringify({
        keywords: result.sss_ready?.map((r) => r.keyword) || [],
        faq_questions: result.faq_questions || [],
        main_keyword: result.seed_keyword,
        location: result.location,
      })
    );
    setMessage("SSS Automation verisi session'a kaydedildi");
    if (onNavigateSSS) onNavigateSSS();
  };

  const providerStatus = health?.providers || {};

  return (
    <div className={embedded ? "talon-orchestrator talon-orchestrator-embedded" : "talon-orchestrator"}>
      {!embedded && (
        <>
          <h2>🎯 Talon Orchestrator</h2>
          <p className="modul-desc">
            Merkezi SEO karar motoru — keyword keşfi, intent, sayfa tipi, GEO cluster, rakip analizi ve içerik brief.
          </p>
          <div className="status-row" style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {Object.entries(providerStatus).map(([name, status]) => (
              <span
                key={name}
                className={`badge ${status === "configured" || status === "available" ? "ok" : "warn"}`}
                style={{
                  padding: "2px 8px",
                  borderRadius: 4,
                  fontSize: 12,
                  background: status === "configured" || status === "available" ? "#1a3d2a" : "#3d2a1a",
                }}
              >
                {name}: {status}
              </span>
            ))}
            {health && (
              <span style={{ fontSize: 12, opacity: 0.8 }}>
                {health.ready ? "✓ Hazır" : "○ Provider eksik"}
              </span>
            )}
          </div>
        </>
      )}

      <div className="form-grid" style={{ display: "grid", gap: "0.75rem", maxWidth: embedded ? "100%" : 600, marginBottom: "1rem" }}>
        <label>
          Seed keyword
          <input
            value={seedKeyword}
            onChange={(e) => setSeedKeyword(e.target.value)}
            placeholder="kuşadası gece hayatı"
          />
        </label>
        <label>
          Lokasyon
          <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Kuşadası" />
        </label>
        <label>
          Limit
          <input
            type="number"
            min={5}
            max={100}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          />
        </label>
        <button type="button" className="btn-primary" onClick={runFullResearch} disabled={loading}>
          {loading ? "Araştırılıyor…" : "Full Research"}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}
      {message && <div className="success-msg" style={{ color: "#6f6", marginBottom: "0.5rem" }}>{message}</div>}

      {result && (
        <>
          <div className="action-row" style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
            <button type="button" onClick={sendToAstro}>Astro Factory&apos;ye gönder</button>
            <button type="button" onClick={sendToPageHub}>Page Hub&apos;a gönder</button>
            <button type="button" onClick={sendToSSS}>SSS Automation&apos;a gönder</button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <h3>Keyword listesi ({result.keywords?.length || 0})</h3>
              <div style={{ maxHeight: 320, overflow: "auto", border: "1px solid var(--border)", borderRadius: 6 }}>
                <table style={{ width: "100%", fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Keyword</th>
                      <th>Skor</th>
                      <th>Intent</th>
                      <th>Sayfa</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(result.keywords || []).map((kw) => (
                      <tr
                        key={kw.keyword}
                        onClick={() => setSelectedKw(kw)}
                        style={{
                          cursor: "pointer",
                          background: selectedKw?.keyword === kw.keyword ? "rgba(255,200,0,0.1)" : "transparent",
                        }}
                      >
                        <td>{kw.keyword}</td>
                        <td>{kw.opportunity_score}</td>
                        <td>{INTENT_LABELS[kw.intent] || kw.intent}</td>
                        <td>{PAGE_TYPE_LABELS[kw.recommended_page_type] || kw.recommended_page_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div>
              <h3>Detay</h3>
              {selectedKw ? (
                <div style={{ fontSize: 13 }}>
                  <p><strong>Keyword:</strong> {selectedKw.keyword}</p>
                  <p><strong>Opportunity:</strong> {selectedKw.opportunity_score}</p>
                  <p><strong>GEO skor:</strong> {selectedKw.geo_score}</p>
                  <p><strong>Intent:</strong> {INTENT_LABELS[selectedKw.intent] || selectedKw.intent}</p>
                  <p><strong>Sayfa tipi:</strong> {PAGE_TYPE_LABELS[selectedKw.recommended_page_type] || selectedKw.recommended_page_type}</p>
                  {selectedKw.competitors?.length > 0 && (
                    <>
                      <p><strong>Rakipler:</strong></p>
                      <ul>
                        {selectedKw.competitors.slice(0, 5).map((c) => (
                          <li key={c.domain}>{c.domain}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {selectedKw.content_brief && (
                    <>
                      <p><strong>H1:</strong> {selectedKw.content_brief.h1}</p>
                      <p><strong>FAQ:</strong></p>
                      <ul>
                        {(selectedKw.content_brief.faq_questions || []).slice(0, 5).map((q) => (
                          <li key={q}>{q}</li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              ) : (
                <p>Bir keyword seçin</p>
              )}
            </div>
          </div>

          <div style={{ marginTop: "1rem", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
            <div>
              <h4>GEO sayfalar ({result.geo_pages?.length || 0})</h4>
              <ul style={{ fontSize: 12, maxHeight: 120, overflow: "auto" }}>
                {(result.geo_pages || []).slice(0, 8).map((gp) => (
                  <li key={gp.slug || gp.title}>{gp.title || gp.keyword}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>FAQ soruları ({result.faq_questions?.length || 0})</h4>
              <ul style={{ fontSize: 12, maxHeight: 120, overflow: "auto" }}>
                {(result.faq_questions || []).slice(0, 8).map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Hazır kuyruklar</h4>
              <p style={{ fontSize: 12 }}>
                Astro: {result.astro_factory_ready?.length || 0} · Page Hub: {result.page_hub_ready?.length || 0} ·
                SSS: {result.sss_ready?.length || 0} · Publisher: {result.publisher_ready?.length || 0}
              </p>
            </div>
          </div>

          {result.competitors?.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <h4>Top rakipler</h4>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {result.competitors.slice(0, 10).map((c) => (
                  <span key={c.domain} className="badge">{c.domain}</span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
