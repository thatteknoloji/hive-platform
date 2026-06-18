import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

const STEPS = ["Çek", "Düzenle", "Yayın Önizle", "Yayınla"];

export default function StoryForgeUrlWizard({ embedded = false }) {
  const [step, setStep] = useState(0);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [lokasyon, setLokasyon] = useState("");
  const [categorySlug, setCategorySlug] = useState("gece-hikaye");
  const [customRules, setCustomRules] = useState("");
  const [rules, setRules] = useState(null);

  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [scraped, setScraped] = useState(null);
  const [publishPreview, setPublishPreview] = useState(null);
  const [published, setPublished] = useState(null);
  const [history, setHistory] = useState([]);

  const loadHealth = useCallback(async () => {
    setHealthError("");
    try {
      const res = await API.get("/api/storyforge/scraper/health", { timeout: 45000 });
      setHealth(res.data);
      return res.data;
    } catch (e) {
      setHealth(null);
      const msg = e.hiveMessage || e.message || "Backend yanıt vermiyor";
      setHealthError(`Health API: ${msg}`);
      return null;
    }
  }, []);

  const loadRules = useCallback(async () => {
    try {
      const res = await API.get("/api/storyforge/rules");
      setRules(res.data.rules || null);
      setCustomRules((prev) => prev || res.data.rules?.custom_rules || "");
    } catch {
      setRules(null);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const res = await API.get("/api/storyforge/scraper/history");
      setHistory(res.data.history || []);
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    loadRules();
    loadHistory();
  }, [loadHealth, loadRules, loadHistory]);

  const handleScrape = async () => {
    if (!url.trim()) { setError("Hikaye linki gerekli"); return; }
    setLoading(true);
    setError("");
    setMessage("");
    setScraped(null);
    setPublishPreview(null);
    setPublished(null);
    try {
      const res = await API.post("/api/storyforge/scrape", { url: url.trim() });
      setScraped(res.data);
      if (!title && res.data.title) setTitle(res.data.title);
      setMessage(
        `Çekildi: ${res.data.word_count ?? "?"} kelime · ${res.data.char_count} karakter`
      );
      setStep(1);
    } catch (e) {
      setError(e.response?.data?.detail || e.hiveMessage || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRewrite = async () => {
    if (!scraped?.text) { setError("Önce hikaye çekin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/storyforge/scrape/rewrite", {
        text: scraped.text,
        title: title || scraped.title || "",
        custom_rules: customRules,
      });
      setContent(res.data.content || "");
      setTitle(title || res.data.suggested_title || scraped.title || "");
      setLokasyon(res.data.suggested_lokasyon || "");
      setExcerpt(res.data.suggested_excerpt || "");
      if (res.data.suggested_categories?.main_slug) {
        setCategorySlug(res.data.suggested_categories.main_slug);
      }
      const src = res.data.source_word_count ?? scraped?.word_count ?? "?";
      setMessage(
        `Yeniden yazıldı (${res.data.engine}) — ${res.data.word_count} kelime (kaynak: ${src})`
      );
      setStep(1);
    } catch (e) {
      setError(e.response?.data?.detail || e.hiveMessage || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePublishPreview = async () => {
    if (!title.trim() || !content.trim()) {
      setError("Başlık ve içerik gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/storyforge/scrape/preview-publish", {
        title: title.trim(),
        content: content.trim(),
        lokasyon: lokasyon.trim(),
        excerpt: excerpt.trim(),
        category_slug: categorySlug,
      });
      setPublishPreview(res.data);
      setMessage("Yayın önizlemesi hazır");
      setStep(2);
    } catch (e) {
      setError(e.response?.data?.detail || e.hiveMessage || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!title.trim() || !content.trim()) {
      setError("Başlık ve içerik gerekli");
      return;
    }
    setLoading(true);
    setError("");
    setPublished(null);
    try {
      const res = await API.post("/api/storyforge/scrape/publish", {
        title: title.trim(),
        content: content.trim(),
        lokasyon: lokasyon.trim(),
        excerpt: excerpt.trim(),
        category_slug: categorySlug,
        source_url: scraped?.source_url || url.trim(),
      });
      setPublished(res.data);
      setMessage(res.data.proof_message || res.data.message || "Yayınlandı");
      setStep(3);
      await loadHistory();
    } catch (e) {
      setError(e.response?.data?.detail || e.hiveMessage || e.message);
    } finally {
      setLoading(false);
    }
  };

  const ready = health?.ready;

  const rootClass = embedded ? "storyforge-url-wizard" : "category-hub storyforge-v3";

  return (
    <div className={rootClass}>
      {!embedded && (
        <header className="ch-header">
          <h2>📖 StoryForge — Link Çekici</h2>
          <p className="ch-sub">Çek → Kurallı düzenle → Yayın önizle → Yayınla + kanıt</p>
          <button type="button" className="btn btn-outline btn-small" onClick={loadHealth}>
            ↻ Yenile
          </button>
        </header>
      )}
      {embedded && (
        <div className="sf-embedded-toolbar">
          <p className="sf-dim">Adım adım: çek → düzenle → yayın önizle → kanıt</p>
          <button type="button" className="btn btn-outline btn-small" onClick={loadHealth}>
            ↻ Durum
          </button>
        </div>
      )}

      {healthError && <p className="storyforge-error">{healthError}</p>}

      <div className="ch-preview-box" style={{ marginBottom: "1rem" }}>
        <p className={health?.crw?.available ? "sf-ok" : "ch-warn"}>
          fastCRW: {health?.crw?.available ? "✓" : "○"} {health?.crw?.url}
        </p>
        <p className={health?.ollama?.available ? "sf-ok" : "ch-warn"}>
          Ollama: {health?.ollama?.available ? "✓" : "○"} {health?.ollama?.model}
        </p>
        <p className={health?.wordpress?.connected ? "sf-ok" : "ch-warn"}>
          WordPress: {health?.wordpress?.connected ? "✓ bağlı" : "○ bağlı değil"}
        </p>
      </div>

      <div className="ch-create-actions" style={{ marginBottom: "1rem" }}>
        {STEPS.map((label, i) => (
          <span
            key={label}
            style={{
              padding: "4px 10px",
              borderRadius: 6,
              fontSize: 12,
              background: step === i ? "rgba(255,200,0,0.15)" : "transparent",
              border: "1px solid var(--border)",
            }}
          >
            {i + 1}. {label}
          </span>
        ))}
      </div>

      {/* ADIM 1: Çek */}
      <div className="ch-panel">
        <h4>1. Hikaye linki — önizleme</h4>
        <input
          className="storyforge-input"
          placeholder="https://www.wattpad.com/story/..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          style={{ marginBottom: "0.5rem", width: "100%" }}
        />
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleScrape}
          disabled={loading || !url.trim() || !health?.crw?.available}
        >
          {loading ? "Çekiliyor…" : "Çek ve Önizle"}
        </button>
        {scraped && (
          <div className="ch-preview-box" style={{ marginTop: "1rem" }}>
            <p className="sf-ok">
              ✓ {scraped.word_count ?? "?"} kelime · {scraped.char_count} karakter · {scraped.title || "Başlıksız"}
            </p>
            <p className="sf-dim">Kaynak: {scraped.source_url}</p>
            <strong>Orijinal önizleme</strong>
            <pre className="ch-preview-snippet" style={{ maxHeight: 200, overflow: "auto" }}>
              {(scraped.text || "").substring(0, 2000)}
            </pre>
          </div>
        )}
      </div>

      {/* ADIM 2: Düzenle */}
      <div className="ch-panel">
        <h4>2. Kurallı yeniden yazma ve düzenleme</h4>
        {rules && (
          <p className="sf-dim">
            Şehir: {rules.city} · Min kelime: {rules.min_words} ·
            <button type="button" className="btn-link" onClick={loadRules}> kuralları yenile</button>
          </p>
        )}
        <label className="storyforge-label">Özel kurallar (Ollama prompt)</label>
        <textarea
          className="storyforge-input"
          rows={4}
          value={customRules}
          onChange={(e) => setCustomRules(e.target.value)}
          placeholder="Mekanları değiştir, ton, SEO kuralları..."
          style={{ width: "100%", marginBottom: "0.5rem" }}
        />
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleRewrite}
          disabled={loading || !scraped?.text || !health?.ollama?.available}
        >
          {loading ? "Yazılıyor…" : "Kurallara Göre Yeniden Yaz"}
        </button>

        <div className="storyforge-meta-row" style={{ marginTop: "1rem" }}>
          <div>
            <label className="storyforge-label">Başlık</label>
            <input className="storyforge-input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className="storyforge-label">Lokasyon</label>
            <input className="storyforge-input" value={lokasyon} onChange={(e) => setLokasyon(e.target.value)} />
          </div>
          <div>
            <label className="storyforge-label">Kategori slug</label>
            <input className="storyforge-input" value={categorySlug} onChange={(e) => setCategorySlug(e.target.value)} />
          </div>
        </div>
        <label className="storyforge-label">İçerik (HTML düzenlenebilir)</label>
        <textarea
          className="storyforge-input"
          rows={12}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          style={{ width: "100%", fontFamily: "monospace", fontSize: 13 }}
        />
        {content && (
          <>
            <strong>İçerik önizleme</strong>
            <div
              className="ch-preview-snippet"
              style={{ maxHeight: 280, overflow: "auto" }}
              dangerouslySetInnerHTML={{ __html: content.substring(0, 8000) }}
            />
          </>
        )}
        <button
          type="button"
          className="btn btn-primary"
          style={{ marginTop: "0.75rem" }}
          onClick={handlePublishPreview}
          disabled={loading || !content.trim() || !title.trim()}
        >
          Yayın Önizlemesi Al
        </button>
      </div>

      {/* ADIM 3: Yayın önizle */}
      {publishPreview && (
        <div className="ch-preview-box">
          <h4>3. Nereye yayınlanacak?</h4>
          <p><strong>WordPress:</strong> {publishPreview.wp_site}</p>
          <p><strong>Post tipi:</strong> {publishPreview.post_type}</p>
          <p><strong>Slug:</strong> {publishPreview.slug}</p>
          <p><strong>Kategori:</strong> {publishPreview.category_slug}
            {publishPreview.sub_category && ` / ${publishPreview.sub_category}`}
          </p>
          <p><strong>Tahmini URL:</strong>{" "}
            <a href={publishPreview.estimated_url} target="_blank" rel="noopener noreferrer">
              {publishPreview.estimated_url}
            </a>
          </p>
          <p className="sf-dim">{publishPreview.message}</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handlePublish}
            disabled={loading || !ready}
          >
            {loading ? "Yayınlanıyor…" : "WordPress'e Yayınla"}
          </button>
        </div>
      )}

      {/* ADIM 4: Yayın kanıtı */}
      {published && (
        <div className="ch-preview-box" style={{ borderColor: published.verified ? "#4ade80" : "#fbbf24" }}>
          <h4>4. Yayın kanıtı</h4>
          <p className={published.verified ? "sf-ok" : "ch-warn"}>
            {published.verified ? "✓ Yayın doğrulandı" : "○ Doğrulama şüpheli"}
          </p>
          {published.link && (
            <p className="storyforge-ok">
              <strong>Yayınlanan link:</strong>{" "}
              <a href={published.link} target="_blank" rel="noopener noreferrer">
                {published.display_url || published.link}
              </a>
            </p>
          )}
          <p className="sf-dim">
            Post ID: {published.post_id} · HTTP {published.status_code || published.verification?.http_status}
            {published.live ? " · Canlı ✓" : ""}
          </p>
          {published.verification?.proof && (
            <pre className="ch-preview-snippet" style={{ fontSize: 11 }}>
              {JSON.stringify(published.verification.proof, null, 2)}
            </pre>
          )}
        </div>
      )}

      {history.length > 0 && (
        <div className="ch-panel">
          <h4>Son yayınlar</h4>
          <ul className="ch-queue-list">
            {history.slice(0, 8).map((h, i) => (
              <li key={h.post_id || i}>
                {h.title}
                {h.verified && " ✓"}
                {h.link && (
                  <> · <a href={h.link} target="_blank" rel="noopener noreferrer">
                    {h.display_url || h.link}
                  </a></>
                )}
                <span className="sf-dim"> · {h.at}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="storyforge-error">{error}</p>}
      {message && <p className="storyforge-ok">{message}</p>}
    </div>
  );
}
