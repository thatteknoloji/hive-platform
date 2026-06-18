import React, { useState, useEffect, useCallback, useRef } from "react";
import API from "../api";
import { loadSSSPrefill, clearSSSPrefill } from "../utils/sssPrefill";


export default function SSSAutomation({ importHint = null }) {
  const [formData, setFormData] = useState({
    city: "Aydın",
    district: "Kuşadası",
    category: "Gece Hayatı",
    subcategory: "Barlar, kulüpler, eğlence mekanları",
    main_keyword: "kuşadası gece hayatı",
    secondary_keywords: "kuşadası barlar, kuşadası eğlence, kuşadası gece kulüpleri",
    keyword_count: 50,
  });
  const [extraKeywords, setExtraKeywords] = useState([]);
  const [talonImport, setTalonImport] = useState(null);
  const [status, setStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pendingAutoStart, setPendingAutoStart] = useState(false);
  const [preview, setPreview] = useState(null);
  const autoStartDone = useRef(false);

  const refreshStatus = useCallback(async () => {
    try {
      const res = await API.get("/api/sss-automation/status");
      setStatus(res.data);
    } catch {
      /* sessiz yenileme */
    }
  }, []);

  const applyPrefill = useCallback((prefill) => {
    if (!prefill) return;
    setFormData({
      city: prefill.city || "Aydın",
      district: prefill.district || "Kuşadası",
      category: prefill.category || "Gece Hayatı",
      subcategory: prefill.subcategory || "Barlar, kulüpler, eğlence mekanları",
      main_keyword: prefill.main_keyword || "kuşadası gece hayatı",
      secondary_keywords: prefill.secondary_keywords || "",
      keyword_count: prefill.keyword_count || 50,
    });
    setExtraKeywords(prefill.extra_keywords || []);
    setTalonImport(prefill.research_summary || { seedKeyword: prefill.main_keyword });
    setMessage("Talon research verileri forma aktarıldı — alanları kontrol edip başlatabilirsiniz.");
    if (prefill.autoStart) setPendingAutoStart(true);
  }, []);

  useEffect(() => {
    const prefill = loadSSSPrefill();
    if (prefill) {
      applyPrefill(prefill);
      clearSSSPrefill();
    } else if (importHint?.summary) {
      setTalonImport(importHint.summary);
      if (importHint.autoStart) setPendingAutoStart(true);
    }
  }, [importHint, applyPrefill]);

  useEffect(() => {
    refreshStatus();
    const t = setInterval(refreshStatus, 3000);
    return () => clearInterval(t);
  }, [refreshStatus]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "keyword_count" ? parseInt(value, 10) || 50 : value,
    }));
  };

  const handleStart = useCallback(async () => {
    setLoading(true);
    setError("");
    setMessage("");
    setShowReport(false);
    try {
      const payload = {
        ...formData,
        secondary_keywords: formData.secondary_keywords
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        extra_keywords: extraKeywords,
      };
      const res = await API.post("/api/sss-automation/start", payload);
      setMessage(`Üretim başlatıldı — Oturum: ${res.data.session_id}`);
      setTalonImport(null);
      setPendingAutoStart(false);
      await refreshStatus();
    } catch (e) {
      setError(e.response?.data?.detail || e.hiveMessage || e.message);
    }
    setLoading(false);
  }, [formData, extraKeywords, refreshStatus]);

  useEffect(() => {
    if (!pendingAutoStart || autoStartDone.current || status?.running) return;
    autoStartDone.current = true;
    handleStart();
  }, [pendingAutoStart, status?.running, handleStart]);

  const handleReport = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.get("/api/sss-automation/report");
      setReport(res.data);
      setShowReport(true);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const handlePreview = async () => {
    setLoading(true);
    setError("");
    setPreview(null);
    try {
      const payload = {
        ...formData,
        secondary_keywords: formData.secondary_keywords
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      const res = await API.post("/api/sss-automation/preview", payload);
      setPreview(res.data);
      setMessage("Önizleme hazır — kelime limitleri ve ilan linkleri kontrol edildi.");
    } catch (e) {
      setError(e.response?.data?.detail || e.hiveMessage || e.message);
    }
    setLoading(false);
  };

  const handleRepair = async () => {
    if (!window.confirm("Boş veya ince SSS sayfaları yeniden yayınlanacak. Devam?")) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/sss-automation/repair", {
        city: formData.city,
        district: formData.district,
        category: formData.category,
        subcategory: formData.subcategory,
        secondary_keywords: formData.secondary_keywords,
        limit: 50,
      });
      setMessage(`Onarım tamamlandı: ${res.data.repaired} güncellendi, ${res.data.skipped} atlandı, ${res.data.failed} hata`);
      await refreshStatus();
      await handleReport();
    } catch (e) {
      setError(e.response?.data?.detail || e.hiveMessage || e.message);
    }
    setLoading(false);
  };

  const running = status?.running;
  const total = status?.total || 0;
  const processed = status?.processed || 0;
  const progressPct = status?.progress_pct || 0;

  return (
    <div className="modul-sayfa" style={{ padding: "1.5rem" }}>
      <h2>❓ SSS Otomatik Üretim Zinciri</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "1.25rem" }}>
        Talon anahtar kelime → SSS üretimi → WordPress yayını → IndexNow bildirimi
      </p>

      {talonImport && (
        <div style={{
          marginBottom: "1rem",
          padding: "0.85rem 1rem",
          borderRadius: 8,
          border: "1px solid var(--olive2)",
          background: "rgba(107,142,35,0.12)",
        }}>
          <strong style={{ color: "var(--olive2)" }}>🐝 Talon&apos;dan aktarıldı</strong>
          <div style={{ fontSize: "0.85rem", marginTop: "0.35rem", color: "var(--text2)" }}>
            Seed: <strong>{talonImport.seedKeyword}</strong>
            {talonImport.serpCount != null && <> · SERP: {talonImport.serpCount}</>}
            {talonImport.competitorCount != null && <> · Rakip: {talonImport.competitorCount}</>}
            {talonImport.faqCount != null && <> · SSS fikri: {talonImport.faqCount}</>}
            {extraKeywords.length > 0 && <> · Aktarılan kelime: {extraKeywords.length}</>}
          </div>
        </div>
      )}

      <div style={{ display: "grid", gap: "0.6rem", maxWidth: 640, marginBottom: "1.25rem" }}>
        {[
          ["city", "Şehir"],
          ["district", "İlçe"],
          ["category", "Kategori"],
          ["subcategory", "Alt Kategori"],
          ["main_keyword", "Hedef Anahtar Kelime"],
          ["secondary_keywords", "Yan Anahtar Kelimeler (virgülle)"],
        ].map(([key, label]) => (
          <label key={key} style={{ display: "grid", gap: "0.25rem" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{label}</span>
            <input
              name={key}
              value={formData[key]}
              onChange={handleChange}
              disabled={running}
              style={{ padding: "0.5rem" }}
            />
          </label>
        ))}
        <label style={{ display: "grid", gap: "0.25rem" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Kelime Sayısı (min 50)</span>
          <input
            name="keyword_count"
            type="number"
            min={50}
            max={100}
            value={formData.keyword_count}
            onChange={handleChange}
            disabled={running}
            style={{ padding: "0.5rem", width: 120 }}
          />
        </label>
        {extraKeywords.length > 0 && (
          <details>
            <summary style={{ fontSize: "0.85rem", cursor: "pointer", color: "var(--text-muted)" }}>
              Talon&apos;dan aktarılan kelimeler ({extraKeywords.length})
            </summary>
            <ul style={{ fontSize: "0.8rem", maxHeight: 140, overflowY: "auto", marginTop: "0.5rem" }}>
              {extraKeywords.slice(0, 30).map((k, i) => (
                <li key={i}>{k}</li>
              ))}
              {extraKeywords.length > 30 && <li>… +{extraKeywords.length - 30} daha</li>}
            </ul>
          </details>
        )}
      </div>

      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
        <button
          onClick={handleStart}
          disabled={loading || running}
          className="btn-primary"
        >
          {running ? "Üretim Devam Ediyor…" : loading ? "Başlatılıyor…" : "🚀 Üretimi Başlat"}
        </button>
        <button onClick={handlePreview} disabled={loading || running}>
          👁 Önizleme
        </button>
        <button onClick={handleReport} disabled={loading}>
          📊 Rapor Göster
        </button>
        <button onClick={handleRepair} disabled={loading || running}>
          🔧 Boş Sayfaları Onar
        </button>
        <button onClick={refreshStatus} disabled={loading}>
          🔄 Yenile
        </button>
      </div>

      {error && <div className="hata-kutu" style={{ marginBottom: "1rem" }}>{error}</div>}
      {message && <div style={{ marginBottom: "1rem", color: "var(--accent)" }}>{message}</div>}

      {status && (
        <div style={{ marginBottom: "1.5rem", padding: "1rem", border: "1px solid var(--border)", borderRadius: 8 }}>
          <h3 style={{ marginTop: 0 }}>İlerleme Durumu</h3>
          <div style={{ marginBottom: "0.75rem" }}>
            <div style={{
              height: 12,
              background: "var(--border)",
              borderRadius: 6,
              overflow: "hidden",
            }}>
              <div style={{
                height: "100%",
                width: `${progressPct}%`,
                background: running ? "var(--accent)" : status.status === "completed" ? "#22c55e" : "#ef4444",
                transition: "width 0.4s ease",
              }} />
            </div>
            <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem" }}>
              {processed}/{total} kelime işlendi ({progressPct}%)
            </p>
          </div>

          <table style={{ width: "100%", fontSize: "0.9rem", borderCollapse: "collapse" }}>
            <tbody>
              <tr><td style={{ padding: "0.25rem 0", color: "var(--text-muted)" }}>Durum</td><td><strong>{status.status}</strong></td></tr>
              <tr><td style={{ padding: "0.25rem 0", color: "var(--text-muted)" }}>Adım</td><td>{status.current_step || "—"}</td></tr>
              <tr><td style={{ padding: "0.25rem 0", color: "var(--text-muted)" }}>Güncel kelime</td><td>{status.current_keyword || "—"}</td></tr>
              <tr><td style={{ padding: "0.25rem 0", color: "var(--text-muted)" }}>Yayınlanan</td><td>{status.published || 0}</td></tr>
              <tr><td style={{ padding: "0.25rem 0", color: "var(--text-muted)" }}>Hata</td><td>{status.failed || 0}</td></tr>
              <tr><td style={{ padding: "0.25rem 0", color: "var(--text-muted)" }}>IndexNow</td><td>{status.indexed || 0}</td></tr>
            </tbody>
          </table>

          {status.last_page && (
            <div style={{ marginTop: "1rem", padding: "0.75rem", background: "var(--bg-secondary, #1a1a2e)", borderRadius: 6 }}>
              <strong>Son üretilen sayfa:</strong>
              <div style={{ marginTop: "0.35rem" }}>
                {status.last_page.title}
                {status.last_page.url && (
                  <> — <a href={status.last_page.url} target="_blank" rel="noreferrer">{status.last_page.url}</a></>
                )}
              </div>
              <div style={{ fontSize: "0.8rem", marginTop: "0.35rem", color: "var(--text-muted)" }}>
                {status.last_page.faq_count != null && <>SSS: {status.last_page.faq_count} · </>}
                {status.last_page.intro_words != null && <>Giriş: {status.last_page.intro_words} kelime · </>}
                {status.last_page.html_chars != null && <>{status.last_page.html_chars} karakter</>}
                {status.last_page.listing_links > 0 && <> · {status.last_page.listing_links} ilan linki</>}
              </div>
            </div>
          )}
        </div>
      )}

      {preview?.page && (
        <div style={{ marginBottom: "1.5rem", padding: "1rem", border: "1px solid var(--border)", borderRadius: 8 }}>
          <h3 style={{ marginTop: 0 }}>SSS Önizleme — {preview.page.seo_title}</h3>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
            Giriş: {preview.page.word_stats?.intro_words} kelime ·
            SSS: {preview.page.word_stats?.faq_count} ·
            Cevap: {preview.page.word_stats?.min_answer_words}–{preview.page.word_stats?.max_answer_words} kelime ·
            HTML: {preview.page.word_stats?.html_chars} karakter ·
            Yayına hazır: {preview.valid_for_publish ? "Evet" : "Hayır"}
          </div>
          <details>
            <summary>HTML önizleme</summary>
            <div
              style={{ marginTop: "0.75rem", padding: "0.75rem", background: "#fff", color: "#111", borderRadius: 6, maxHeight: 320, overflow: "auto" }}
              dangerouslySetInnerHTML={{ __html: preview.page.html }}
            />
          </details>
        </div>
      )}

      {showReport && report && (
        <div style={{ padding: "1rem", border: "1px solid var(--border)", borderRadius: 8 }}>
          <h3>Özet Rapor</h3>
          <ul style={{ lineHeight: 1.8 }}>
            <li>Üretilen kelime: <strong>{report.keywords_generated}</strong></li>
            <li>Yayınlanan sayfa: <strong>{report.pages_published}</strong></li>
            <li>Hatalı sayfa: <strong>{report.pages_failed}</strong></li>
            <li>IndexNow gönderimi: <strong>{report.indexnow_sent}</strong></li>
            <li>Başlangıç: {report.started_at || "—"}</li>
            <li>Bitiş: {report.finished_at || "—"}</li>
          </ul>
          {report.errors?.length > 0 && (
            <details style={{ marginTop: "1rem" }}>
              <summary>Hatalar ({report.errors.length})</summary>
              <pre style={{ fontSize: "0.8rem", overflow: "auto", maxHeight: 200 }}>
                {JSON.stringify(report.errors, null, 2)}
              </pre>
            </details>
          )}
          {report.last_pages?.length > 0 && (
            <details style={{ marginTop: "1rem" }} open>
              <summary>Son yayınlanan sayfalar</summary>
              <ul style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
                {report.last_pages.map((p, i) => (
                  <li key={i}>
                    {p.title}
                    {p.url && <> — <a href={p.url} target="_blank" rel="noreferrer">{p.url}</a></>}
                    {(p.faq_count || p.html_chars) && (
                      <span style={{ color: "var(--text-muted)" }}>
                        {" "}
                        ({p.faq_count || "?"} SSS, {p.html_chars || "?"} karakter
                        {p.listing_links ? `, ${p.listing_links} ilan` : ""})
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
