import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import API from "../api";


const ENGINE_LABELS = {
  groq: "Groq",
  openrouter: "OpenRouter",
  openai: "OpenAI",
  gemini: "Google Gemini",
  deepseek: "DeepSeek",
  perplexity: "Perplexity",
  together: "Together AI",
  mistral: "Mistral",
  anthropic: "Anthropic",
  ollama: "Yerel Ollama",
  hive_worker: "HIVE Cloud Worker",
  "local-template": "Yerel şablon",
};

const formatEngineName = (raw) => {
  if (!raw) return "";
  const base = raw.replace(/\+pad$/, "");
  const label = ENGINE_LABELS[base] || base;
  return raw.endsWith("+pad") ? `${label} + uzatma` : label;
};

const formatCategoryPath = (cats) => {
  if (!cats) return "";
  const main = cats.main_name || cats.main_slug;
  const sub = cats.sub_name || cats.sub_slug;
  if (main && sub) return `${main} → ${sub}`;
  return main || sub || cats.matched_keyword || "";
};

const buildCategoryOptions = (wpTerms, tree) => {
  const opts = [{ slug: "auto", label: "🎲 Otomatik — içerikten ana + alt belirle" }];
  if (wpTerms?.length) {
    wpTerms.filter((t) => !t.parent).forEach((main) => {
      opts.push({ slug: main.slug, label: `📁 ${main.name}`, isMain: true });
      wpTerms.filter((s) => s.parent === main.id).forEach((sub) => {
        opts.push({ slug: sub.slug, label: `   ↳ ${sub.name}` });
      });
    });
    return opts;
  }
  if (tree) {
    Object.entries(tree).forEach(([slug, meta]) => {
      opts.push({ slug, label: `📁 ${meta.name}` });
      Object.entries(meta.subs || {}).forEach(([subSlug, subName]) => {
        opts.push({ slug: subSlug, label: `   ↳ ${subName}` });
      });
    });
  }
  return opts;
};

export default function StoryForgeStudio({ onOpenCategoryHub, embedded = false, hideManualUrl = false }) {
  const [url, setUrl] = useState("");
  const [batchUrls, setBatchUrls] = useState("");
  const [title, setTitle] = useState("");
  const [lokasyon, setLokasyon] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [category, setCategory] = useState("auto");
  const [original, setOriginal] = useState("");
  const [rewritten, setRewritten] = useState("");
  const [pendingId, setPendingId] = useState("");
  const [engine, setEngine] = useState("");
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [pending, setPending] = useState([]);
  const [genCount, setGenCount] = useState(10);
  const [autoPublish, setAutoPublish] = useState(true);
  const [batchRunning, setBatchRunning] = useState(false);
  const [activeJobId, setActiveJobId] = useState("");
  const [photos, setPhotos] = useState([]);
  const [photoUploading, setPhotoUploading] = useState(false);

  const [rules, setRules] = useState(null);
  const [rulesSaving, setRulesSaving] = useState(false);
  const [importId, setImportId] = useState("");
  const [importInfo, setImportInfo] = useState(null);
  const [importUploading, setImportUploading] = useState(false);
  const [bulkMode, setBulkMode] = useState("quick");
  const [quickPaste, setQuickPaste] = useState("");
  const [quickTitle, setQuickTitle] = useState("");
  const [bulkPaste, setBulkPaste] = useState("");
  const [pastePreview, setPastePreview] = useState(null);
  const [bulkOffset, setBulkOffset] = useState(0);
  const [bulkLimit, setBulkLimit] = useState(0);
  const [bulkDelay, setBulkDelay] = useState(2);
  const [quickLoading, setQuickLoading] = useState(false);
  const [publishedLog, setPublishedLog] = useState([]);
  const [activeJob, setActiveJob] = useState(null);
  const [lastPublish, setLastPublish] = useState(null);
  const [verifyingUrl, setVerifyingUrl] = useState("");
  const publishPanelRef = useRef(null);

  const [wpCategories, setWpCategories] = useState([]);
  const [categoryTree, setCategoryTree] = useState(null);
  const [predictedCategories, setPredictedCategories] = useState(null);
  const [publishedCategories, setPublishedCategories] = useState(null);
  const [catPredicting, setCatPredicting] = useState(false);

  const categoryOptions = useMemo(
    () => buildCategoryOptions(wpCategories, categoryTree),
    [wpCategories, categoryTree]
  );

  const formatDisplayUrl = (url) => {
    if (!url) return "";
    return url.replace(/^https?:\/\//, "").replace(/^www\./, "www.");
  };

  const scrollToPublish = () => {
    setTimeout(() => {
      publishPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  };

  const copyLink = async (url) => {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setMessage("Link kopyalandı!");
    } catch {
      setMessage(formatDisplayUrl(url));
    }
  };

  const recordPublish = (item) => {
    setLastPublish(item);
    setPublishedLog((prev) => {
      const key = item.link || item.id;
      if (key && prev.some((p) => (p.link || p.id) === key)) return prev;
      return [{ ...item, display_url: item.display_url || formatDisplayUrl(item.link) }, ...prev].slice(0, 50);
    });
    scrollToPublish();
  };

  const BULK_MODES = [
    { id: "quick", label: "⚡ Çat Yapıştır", hint: "Tek hikaye — kopyala yapıştır, dönüştür, yayınla" },
    { id: "paste", label: "📋 Toplu Yapıştır", hint: "Birden fazla hikaye — --- ile ayır, tek tıkla yayınla" },
    { id: "file", label: "📁 Dosya Yükle", hint: "TXT, Word, JSONL, CSV — binlerce hikaye" },
  ];

  const refreshMeta = useCallback(async () => {
    try {
      const [statsRes, jobsRes, pendingRes, photosRes, pubRes] = await Promise.all([
        API.get("/api/storyforge/stats"),
        API.get("/api/storyforge/jobs?limit=10"),
        API.get("/api/storyforge/pending"),
        API.get("/api/storyforge/photos"),
        API.get("/api/storyforge/published?limit=30"),
      ]);
      setStats(statsRes.data);
      setJobs(jobsRes.data.jobs || []);
      setPending(pendingRes.data.pending || []);
      setPhotos(photosRes.data.photos || []);
      setPublishedLog(pubRes.data.published || []);
    } catch {
      /* panel yenileme sessiz */
    }
  }, []);

  useEffect(() => {
    refreshMeta();
    API.get("/api/storyforge/rules")
      .then((res) => setRules(res.data.rules || null))
      .catch(() => {});
    API.get("/api/storyforge/categories")
      .then((res) => {
        setWpCategories(res.data.wp_terms || []);
        setCategoryTree(res.data.tree || null);
      })
      .catch(() => {});
    const pollMs = activeJobId || batchRunning ? 4000 : 15000;
    const t = setInterval(refreshMeta, pollMs);
    return () => clearInterval(t);
  }, [refreshMeta, activeJobId, batchRunning]);

  useEffect(() => {
    if (!activeJobId) return undefined;
    const poll = setInterval(async () => {
      try {
        const res = await API.get(`/api/storyforge/jobs/${activeJobId}`);
        const job = res.data;
        setActiveJob(job);
        if (job.status === "completed" || job.status === "failed") {
          setActiveJobId("");
          setBatchRunning(false);
          const links = (job.results || []).filter((r) => r.link);
          setMessage(
            `Tamamlandı: ${job.published} yayınlandı, ${job.failed} hata (${job.done}/${job.total})`
          );
          if (links.length > 0) {
            const last = links[links.length - 1];
            setLastPublish({
              title: last.title || "Toplu yayın",
              link: last.link,
              live: last.live,
              post_id: last.post_id,
              published_at: new Date().toISOString(),
              source: job.type,
            });
          }
          refreshMeta();
        }
      } catch {
        setActiveJobId("");
        setActiveJob(null);
        setBatchRunning(false);
      }
    }, 2500);
    return () => clearInterval(poll);
  }, [activeJobId, refreshMeta]);

  const handleVerifyLink = async (url) => {
    if (!url) return;
    setVerifyingUrl(url);
    try {
      const res = await API.get(`/api/storyforge/verify-link?url=${encodeURIComponent(url)}`);
      const live = res.data.live;
      setPublishedLog((prev) => prev.map((p) => (p.link === url ? { ...p, live, status_code: res.data.status_code } : p)));
      if (lastPublish?.link === url) {
        setLastPublish((p) => ({ ...p, live, status_code: res.data.status_code }));
      }
      setMessage(live ? `✓ Sayfa canlı: ${url}` : `⚠ Sayfa yanıt vermiyor (HTTP ${res.data.status_code || "?"})`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setVerifyingUrl("");
    }
  };

  const handleFetch = async () => {
    if (!url.trim()) {
      setError("Lütfen bir hikaye linki girin.");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/storyforge/fetch", { url: url.trim() });
      const d = res.data;
      setOriginal(d.original || "");
      setRewritten(d.rewritten || "");
      setTitle(d.suggested_title || "");
      setLokasyon(d.suggested_lokasyon || "");
      setPendingId(d.pending_id || "");
      setEngine(d.engine || "");
      if (d.suggested_categories) setPredictedCategories(d.suggested_categories);
      setExcerpt(`Kuşadası escort hikayesi — ${d.suggested_lokasyon || "Kuşadası"}`);
      setMessage(`Dönüştürüldü (${formatEngineName(d.engine) || "ai"}) — ${d.word_count || "?"} kelime`);
      refreshMeta();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!title.trim() || !rewritten.trim()) {
      setError("Başlık ve hikaye metni gerekli.");
      return;
    }
    setPublishing(true);
    setError("");
    try {
      const res = await API.post("/api/storyforge/publish", {
        title: title.trim(),
        content: rewritten,
        lokasyon: lokasyon.trim(),
        excerpt: excerpt.trim(),
        category_slug: category,
        status: "publish",
        pending_id: pendingId,
      });
      if (res.data.categories) setPublishedCategories(res.data.categories);
      if (res.data.link) {
        recordPublish({
          title: title.trim(),
          link: res.data.link,
          display_url: res.data.display_url || formatDisplayUrl(res.data.link),
          post_id: res.data.post_id,
          live: res.data.live,
          status_code: res.data.status_code,
          categories: res.data.categories,
          published_at: new Date().toISOString(),
          source: "manual",
        });
      }
      const disp = res.data.display_url || formatDisplayUrl(res.data.link);
      const catPath = formatCategoryPath(res.data.categories);
      setMessage(res.data.message || (disp ? `Yayınlandı! ${catPath ? `[${catPath}] ` : ""}Şu adreste: ${disp}` : "Yayınlandı!"));
      setUrl("");
      setOriginal("");
      setRewritten("");
      setPendingId("");
      refreshMeta();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setPublishing(false);
    }
  };

  const handlePhotoUpload = async (e) => {
    const fileList = e.target.files;
    if (!fileList || !fileList.length) return;
    setPhotoUploading(true);
    setError("");
    try {
      const fd = new FormData();
      Array.from(fileList).forEach((f) => fd.append("files", f));
      const res = await API.post("/api/storyforge/photos", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPhotos(res.data.photos || []);
      setMessage(`${res.data.uploaded} foto yüklendi — havuzda ${res.data.total_photos} foto`);
      refreshMeta();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setPhotoUploading(false);
      e.target.value = "";
    }
  };

  const handleClearPhotos = async () => {
    if (!window.confirm("Foto havuzunu temizlemek istediğine emin misin?")) return;
    try {
      await API.delete("/api/storyforge/photos");
      setPhotos([]);
      setMessage("Foto havuzu temizlendi");
      refreshMeta();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleAutoGenerate = async () => {
    setBatchRunning(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/storyforge/generate", {
        count: genCount,
        auto_publish: autoPublish,
        category_slug: category,
        delay_sec: 1,
      });
      setActiveJobId(res.data.job_id);
      setActiveJob({ id: res.data.job_id, status: "running", done: 0, total: genCount, published: 0, failed: 0, results: [] });
      setMessage(res.data.message || "Üretim başlatıldı — aşağıda canlı takip et");
      refreshMeta();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setBatchRunning(false);
    }
  };

  const refreshCategories = async () => {
    try {
      const res = await API.get("/api/storyforge/categories");
      setWpCategories(res.data.wp_terms || []);
      setCategoryTree(res.data.tree || null);
    } catch { /* sessiz */ }
  };

  const predictCategory = useCallback(async (opts = {}) => {
    const slug = opts.categorySlug ?? category;
    const content = opts.content ?? rewritten ?? quickPaste ?? original ?? "";
    const t = opts.title ?? title ?? quickTitle ?? "";
    const loc = opts.lokasyon ?? lokasyon ?? "";
    if (slug !== "auto" && !content.trim()) {
      const term = wpCategories.find((c) => c.slug === slug);
      if (term) {
        const parent = term.parent ? wpCategories.find((c) => c.id === term.parent) : null;
        setPredictedCategories(parent
          ? { main_name: parent.name, main_slug: parent.slug, sub_name: term.name, sub_slug: term.slug, mode: "manual" }
          : { main_name: term.name, main_slug: term.slug, mode: "manual" });
      }
      return;
    }
    if (!content.trim() && slug === "auto") return;
    setCatPredicting(true);
    try {
      const res = await API.post("/api/storyforge/categories/predict", {
        title: t,
        content: content.slice(0, 4000),
        lokasyon: loc,
        category_slug: slug,
      });
      setPredictedCategories(res.data.picked);
    } catch { /* sessiz */ }
    finally { setCatPredicting(false); }
  }, [category, rewritten, quickPaste, original, title, quickTitle, lokasyon, wpCategories]);

  useEffect(() => {
    const t = setTimeout(() => predictCategory(), 600);
    return () => clearTimeout(t);
  }, [category, title, quickTitle, lokasyon, rewritten, quickPaste, predictCategory]);

  const renderCategorySelect = (id, disabled = false) => (
    <select
      id={id}
      className="storyforge-input"
      value={category}
      onChange={(e) => setCategory(e.target.value)}
      disabled={disabled}
    >
      {categoryOptions.map((c) => (
        <option key={c.slug} value={c.slug}>{c.label}</option>
      ))}
    </select>
  );

  const handleSaveRules = async () => {
    if (!rules) return;
    setRulesSaving(true);
    setError("");
    try {
      const payload = {
        city: rules.city,
        district: rules.district,
        locations: (rules.locations || []).filter(Boolean),
        character_names: (rules.character_names || []).filter(Boolean),
        keywords: (rules.keywords || []).filter(Boolean),
        custom_rules: rules.custom_rules,
        title_template: rules.title_template,
        min_words: Number(rules.min_words) || 500,
        max_words: Number(rules.max_words) || 1800,
        seo_title_max: Number(rules.seo_title_max) || 60,
        site_url: rules.site_url,
        geo_inject: rules.geo_inject,
        auto_category: rules.auto_category !== false,
      };
      const res = await API.post("/api/storyforge/rules", payload);
      setRules(res.data.rules);
      setMessage("Kurallar kaydedildi");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setRulesSaving(false);
    }
  };

  const handleQuickPaste = async (previewOnly = false) => {
    if (!quickPaste.trim() || quickPaste.trim().length < 80) {
      setError("Hikayeyi yapıştır (en az 80 karakter).");
      return;
    }
    setQuickLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/storyforge/quick", {
        text: quickPaste.trim(),
        title: quickTitle.trim(),
        auto_publish: autoPublish && !previewOnly,
        preview_only: previewOnly,
        category_slug: category,
      });
      const d = res.data;
      setRewritten(d.rewritten || "");
      setTitle(d.suggested_title || "");
      setLokasyon(d.suggested_lokasyon || "");
      setExcerpt(d.suggested_excerpt || "");
      setEngine(d.engine || "");
      setOriginal(quickPaste.trim());
      if (d.suggested_categories) setPredictedCategories(d.suggested_categories);
      if (d.published_categories) setPublishedCategories(d.published_categories);
      if (d.published && d.link) {
        recordPublish({
          title: d.suggested_title,
          link: d.link,
          display_url: d.display_url || formatDisplayUrl(d.link),
          post_id: d.post_id,
          live: d.live,
          status_code: d.status_code,
          engine: d.engine,
          categories: d.published_categories || d.suggested_categories,
          published_at: new Date().toISOString(),
          source: "quick",
        });
        const catPath = formatCategoryPath(d.published_categories || d.suggested_categories);
        setMessage(`Yayınlandı! ${catPath ? `[${catPath}] ` : ""}Şu adreste: ${d.display_url || formatDisplayUrl(d.link)}`);
        setQuickPaste("");
        setQuickTitle("");
      } else if (previewOnly) {
        const cw = d.content_word_count || d.word_count || "?";
        const cat = formatCategoryPath(d.suggested_categories);
        setMessage(`Dönüştürüldü — önizleme (${formatEngineName(d.engine)}, ${cw} anlamlı kelime${cat ? ` · ${cat}` : ""}). Aşağıdan düzenleyip yayınla.`);
      } else {
        const cat = formatCategoryPath(d.published_categories || d.suggested_categories);
        setMessage(`Dönüştürüldü (${formatEngineName(d.engine)}${cat ? ` · ${cat}` : ""}) — yayın için aşağıyı kontrol et`);
      }
      refreshMeta();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setQuickLoading(false);
    }
  };

  useEffect(() => {
    if (bulkMode !== "paste" || !bulkPaste.trim()) {
      setPastePreview(null);
      return undefined;
    }
    const t = setTimeout(async () => {
      try {
        const res = await API.post("/api/storyforge/paste-preview", { text: bulkPaste });
        setPastePreview(res.data);
      } catch {
        setPastePreview(null);
      }
    }, 600);
    return () => clearTimeout(t);
  }, [bulkPaste, bulkMode]);

  const handlePasteRun = async () => {
    if (!bulkPaste.trim()) {
      setError("Toplu hikayeleri yapıştır. Her hikayeyi --- ile ayır.");
      return;
    }
    setBatchRunning(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/storyforge/paste-run", {
        text: bulkPaste,
        auto_publish: autoPublish,
        category_slug: category,
        delay_sec: bulkDelay,
        offset: bulkOffset,
        limit: bulkLimit,
      });
      setActiveJobId(res.data.job_id);
      setActiveJob({ id: res.data.job_id, status: "running", done: 0, total: res.data.total || res.data.import_count, published: 0, failed: 0, results: [] });
      setImportId(res.data.import_id || "");
      setMessage(`${res.data.import_count} hikaye kuyruğa alındı — aşağıda canlı takip et`);
      setBulkPaste("");
      setPastePreview(null);
      refreshMeta();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setBatchRunning(false);
    }
  };

  const handleFileDrop = async (file) => {
    if (!file) return;
    setImportUploading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await API.post("/api/storyforge/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportId(res.data.import_id || "");
      setImportInfo(res.data);
      setMessage(`${res.data.count} hikaye yüklendi — "Yayınlamayı Başlat"a bas`);
      refreshMeta();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setImportUploading(false);
    }
  };

  const handleBulkRewrite = async () => {
    if (!importId.trim()) {
      setError("Önce dosya yükleyin veya import_id girin.");
      return;
    }
    setBatchRunning(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/storyforge/bulk-rewrite", {
        import_id: importId.trim(),
        auto_publish: autoPublish,
        category_slug: category,
        delay_sec: bulkDelay,
        offset: bulkOffset,
        limit: bulkLimit,
      });
      setActiveJobId(res.data.job_id);
      setActiveJob({ id: res.data.job_id, status: "running", done: 0, total: res.data.total, published: 0, failed: 0, results: [] });
      setMessage(res.data.message || "Toplu yeniden yazma başlatıldı — aşağıda canlı takip et");
      refreshMeta();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setBatchRunning(false);
    }
  };

  const updateRuleField = (key, value) => {
    setRules((prev) => ({ ...prev, [key]: value }));
  };

  const updateRuleList = (key, text) => {
    const arr = text.split("\n").map((s) => s.trim()).filter(Boolean);
    setRules((prev) => ({ ...prev, [key]: arr }));
  };

  const handleBatchUrls = async () => {
    const urls = batchUrls
      .split("\n")
      .map((u) => u.trim())
      .filter(Boolean);
    if (!urls.length) {
      setError("En az bir URL girin (her satıra bir link).");
      return;
    }
    setBatchRunning(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/storyforge/batch-urls", {
        urls,
        auto_publish: autoPublish,
        category_slug: category,
        delay_sec: 2,
      });
      setActiveJobId(res.data.job_id);
      setActiveJob({ id: res.data.job_id, status: "running", done: 0, total: urls.length, published: 0, failed: 0, results: [] });
      setMessage(res.data.message || "Toplu iş başlatıldı — aşağıda canlı takip et");
      setBatchUrls("");
      refreshMeta();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setBatchRunning(false);
    }
  };

  const wrapperClass = embedded ? "storyforge-studio-embedded" : "storyforge-panel";

  return (
    <div className={wrapperClass}>
      {!embedded && (
      <header className="storyforge-header">
        <h2>StoryForge — Stüdyo</h2>
        <p className="storyforge-sub">
          Yapıştır, toplu dosya, AI üretim → Kuşadası&apos;na uyarla → WordPress yayını
        </p>
        {stats?.ai_engines?.primary && (
          <div className="sf-ai-banner">
            <div className="sf-ai-primary-row">
              <span className="sf-ai-icon">🤖</span>
              <span>
                Şu an yazan motor:{" "}
                <strong className="sf-ai-name">{stats.ai_engines.primary.label}</strong>
                {stats.ai_engines.primary.model && (
                  <span className="sf-dim"> · {stats.ai_engines.primary.model}</span>
                )}
              </span>
              <span className={`sf-ai-type ${stats.ai_engines.primary.type === "local" ? "sf-ai-local" : "sf-ai-cloud"}`}>
                {stats.ai_engines.primary.type === "local" ? "Yerel" : "Bulut API"}
              </span>
            </div>
            {stats.ai_engines.fallbacks?.length > 0 && (
              <p className="sf-ai-chain">
                Yedek sıra:{" "}
                {stats.ai_engines.fallbacks.map((f, i) => (
                  <span key={f.id}>
                    {i > 0 && " → "}
                    <span className="sf-ai-fallback-item" title={f.model || f.label}>
                      {f.label}
                      {f.model ? ` (${f.model})` : ""}
                    </span>
                  </span>
                ))}
              </p>
            )}
            {(stats.ai_engines.apis?.tavily || stats.ai_engines.apis?.exa) && (
              <p className="sf-ai-geo">
                GEO araştırma:{" "}
                {stats.ai_engines.apis.tavily && <span className="sf-ok">Tavily</span>}
                {stats.ai_engines.apis.tavily && stats.ai_engines.apis.exa && " · "}
                {stats.ai_engines.apis.exa && <span className="sf-ok">Exa</span>}
              </p>
            )}
          </div>
        )}
      </header>
      )}

      <section className="sf-publish-panel" ref={publishPanelRef}>
        <h3>🔗 Nerede Yayınlandı?</h3>
        <p className="sf-publish-hint">Her yayınlanan hikayenin tam linki burada — tıkla, git, kontrol et.</p>

        {lastPublish?.link ? (
          <div className={`sf-last-publish ${lastPublish.live ? "sf-live-ok" : "sf-live-warn"}`}>
            <p className="sf-published-label">✅ Bu hikaye şurada yayında:</p>
            <div className="sf-last-publish-head">
              <span className="sf-publish-badge">{lastPublish.live ? "✓ CANLI" : "⚠ KONTROL ET"}</span>
              <strong>{lastPublish.title || "Son yayın"}</strong>
            </div>
            <a
              href={lastPublish.link}
              target="_blank"
              rel="noopener noreferrer"
              className="sf-publish-url-big"
              title="Hikayeyi sitede aç"
            >
              {lastPublish.display_url || formatDisplayUrl(lastPublish.link)}
            </a>
            <div className="sf-publish-actions">
              <a href={lastPublish.link} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
                Hikayeyi Sitede Aç →
              </a>
              <button type="button" className="btn btn-secondary btn-small" onClick={() => copyLink(lastPublish.link)}>
                Linki Kopyala
              </button>
              <button type="button" className="btn btn-secondary btn-small" onClick={() => handleVerifyLink(lastPublish.link)} disabled={verifyingUrl === lastPublish.link}>
                {verifyingUrl === lastPublish.link ? "Kontrol…" : "Canlı mı?"}
              </button>
                {(lastPublish.content_word_count || lastPublish.word_count) > 0 && (
                  <span className="sf-dim">{lastPublish.content_word_count || lastPublish.word_count} anlamlı kelime</span>
                )}
                {lastPublish.categories?.main_name && <span className="sf-dim">📁 {lastPublish.categories.main_name}{lastPublish.categories.sub_name ? ` › ${lastPublish.categories.sub_name}` : ""}</span>}
                {lastPublish.post_id && <span className="sf-dim">WP #{lastPublish.post_id}</span>}
            </div>
          </div>
        ) : (
          <p className="sf-publish-empty">Henüz bu oturumda yayın yok — hikaye yayınlayınca tam link burada görünecek.</p>
        )}

          {activeJob && activeJob.status === "running" && (
            <div className="sf-job-live">
              <div className="sf-job-live-head">
                <span>⏳ İşlem devam ediyor</span>
                <span>{activeJob.done}/{activeJob.total} · {activeJob.published} yayın · {activeJob.failed} hata</span>
              </div>
              <div className="sf-progress-bar">
                <div className="sf-progress-fill" style={{ width: `${Math.min(100, (activeJob.done / Math.max(activeJob.total, 1)) * 100)}%` }} />
              </div>
              {(activeJob.results || []).length > 0 && (
                <ul className="sf-live-results">
                  {[...(activeJob.results || [])].reverse().map((r, i) => (
                    <li key={i} className={r.status === "published" ? "sf-ok-row" : r.status === "failed" ? "sf-fail-row" : ""}>
                      {r.status === "published" && r.link ? (
                        <div className="sf-live-link-block">
                          <span className="sf-ok">✓</span>
                          <div>
                            <span className="sf-publish-title">{r.title || "Hikaye"}</span>
                            <a href={r.link} target="_blank" rel="noopener noreferrer" className="sf-publish-url-inline">
                              {formatDisplayUrl(r.link)}
                            </a>
                          </div>
                          {r.live === false && <span className="sf-warn-tag">HTTP?</span>}
                        </div>
                      ) : r.status === "failed" ? (
                        <><span className="sf-fail">✗</span> {r.error || r.source_title || "Hata"}</>
                      ) : (
                        <><span className="sf-dim">…</span> {r.title || r.source_title || `#${r.index}`}</>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {publishedLog.length > 0 && (
            <details className="sf-publish-history" open={!lastPublish?.link}>
              <summary>Son yayınlananlar ({publishedLog.length})</summary>
              <ul className="sf-publish-list">
                {publishedLog.map((p) => (
                  <li key={p.id || p.link || p.published_at} className={p.live ? "sf-ok-row" : ""}>
                    <span className={p.live ? "sf-ok" : "sf-dim"}>{p.live ? "✓" : "○"}</span>
                    <div className="sf-publish-item">
                      <span className="sf-publish-title">{p.title || "Hikaye"}</span>
                      {p.link && (
                        <a href={p.link} target="_blank" rel="noopener noreferrer" className="sf-publish-url-inline">
                          {p.display_url || formatDisplayUrl(p.link)}
                        </a>
                      )}
                    </div>
                    <button type="button" className="btn btn-outline btn-small" onClick={() => handleVerifyLink(p.link)} disabled={!p.link || verifyingUrl === p.link}>
                      Doğrula
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          )}
      </section>

      {stats && (
        <div className="storyforge-stats">
          <span className={stats.wp_connected ? "sf-ok" : "sf-warn"}>
            WP: {stats.wp_connected ? "Bağlı" : "Bağlı değil"}
          </span>
          <span>Yayında: {stats.published_stories ?? "—"} hikaye</span>
          <span>Bekleyen: {stats.pending_count}</span>
          <span>Foto havuzu: {stats.photo_pool_count ?? photos.length}</span>
          <span>Aktif iş: {stats.active_jobs}</span>
          {stats.ai_engines?.primary && (
            <span className="sf-ok">
              AI: {stats.ai_engines.primary.label}
              {stats.ai_engines.primary.model ? ` (${stats.ai_engines.primary.model})` : ""}
            </span>
          )}
        </div>
      )}

      <section className="storyforge-photos">
        <h3>Toplu Fotoğraf</h3>
        <p className="storyforge-photo-hint">
          1 foto → tüm hikayelere aynı görsel. 50 foto + 200 hikaye → rotasyonlu dağıtım.
          Foto sayısı ≥ hikaye sayısı → her hikayeye sırayla farklı foto.
        </p>
        <div className="storyforge-btn-row">
          <label className="btn btn-secondary storyforge-file-btn">
            {photoUploading ? "Yükleniyor…" : "Foto Seç (çoklu)"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              multiple
              onChange={handlePhotoUpload}
              disabled={photoUploading || batchRunning}
              hidden
            />
          </label>
          {photos.length > 0 && (
            <button type="button" className="btn btn-secondary" onClick={handleClearPhotos}>
              Havuzu Temizle ({photos.length})
            </button>
          )}
        </div>
        {photos.length > 0 && (
          <ul className="storyforge-photo-list">
            {photos.slice(0, 8).map((p) => (
              <li key={p.id}>
                {p.filename} <span className="sf-dim">#{p.media_id}</span>
              </li>
            ))}
            {photos.length > 8 && <li className="sf-dim">…ve {photos.length - 8} foto daha</li>}
          </ul>
        )}
      </section>

      <section className="storyforge-bulk">
        <h3>Hikaye Girişi — Yeniden Yaz &amp; Yayınla</h3>
        <p className="storyforge-photo-hint">
          Dışarıdan kopyala-yapıştır, toplu metin veya dosya — SEO/GEO kurallarına göre dönüştürülür, WordPress&apos;e otomatik yayınlanır.
        </p>

        <div className="sf-cat-compact">
          <div className="sf-cat-compact-row">
            <label className="storyforge-label">Yayın kategorisi</label>
            {renderCategorySelect("sf-cat-bulk")}
            {onOpenCategoryHub && (
              <button type="button" className="btn btn-outline btn-small" onClick={onOpenCategoryHub}>
                📂 Kategori Merkezi
              </button>
            )}
          </div>
          {(publishedCategories || predictedCategories) && (
            <p className="sf-cat-compact-preview">
              {publishedCategories ? "✅ " : "📍 "}
              {formatCategoryPath(publishedCategories || predictedCategories)}
              {catPredicting && <span className="sf-dim"> …</span>}
            </p>
          )}
          <p className="sf-dim sf-cat-auto-note">Otomatik seçiliyse içerikten belirlenir; detaylı yönetim Kategori Merkezi&apos;nde.</p>
        </div>

        <div className="sf-mode-tabs">
          {BULK_MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              className={`sf-mode-tab ${bulkMode === m.id ? "active" : ""}`}
              onClick={() => setBulkMode(m.id)}
              disabled={batchRunning || quickLoading}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="sf-mode-hint">{BULK_MODES.find((m) => m.id === bulkMode)?.hint}</p>

        <div className="storyforge-meta-row sf-shared-row">
          <div className="storyforge-check">
            <label>
              <input type="checkbox" checked={autoPublish} onChange={(e) => setAutoPublish(e.target.checked)} disabled={batchRunning} />
              {" "}Otomatik WordPress yayını
            </label>
          </div>
          {predictedCategories && category === "auto" && (
            <span className="sf-cat-inline-hint sf-dim">
              Otomatik: {formatCategoryPath(predictedCategories)}
            </span>
          )}
        </div>

        {bulkMode === "quick" && (
          <div className="sf-mode-panel">
            <label className="storyforge-label">Başlık (opsiyonel — boşsa AI üretir)</label>
            <input
              className="storyforge-input"
              placeholder="Örn: Otel Gecesi Hikayesi"
              value={quickTitle}
              onChange={(e) => setQuickTitle(e.target.value)}
              disabled={quickLoading}
            />
            <label className="storyforge-label">Hikayeyi buraya yapıştır</label>
            <textarea
              className="storyforge-textarea sf-paste-area"
              rows={14}
              placeholder="Dışarıdan kopyaladığın hikayeyi buraya yapıştır…&#10;&#10;Groq ile ~3 sn'de Kuşadası'na uyarlanır ve yayınlanır."
              value={quickPaste}
              onChange={(e) => setQuickPaste(e.target.value)}
              disabled={quickLoading}
            />
            <div className="storyforge-btn-row">
              <button type="button" className="btn btn-primary" onClick={() => handleQuickPaste(false)} disabled={quickLoading || batchRunning}>
                {quickLoading ? "Dönüştürülüyor…" : "⚡ Çat Dönüştür & Yayınla"}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => handleQuickPaste(true)} disabled={quickLoading || batchRunning}>
                Önce Önizle
              </button>
            </div>
          </div>
        )}

        {bulkMode === "paste" && (
          <div className="sf-mode-panel">
            <label className="storyforge-label">Toplu hikayeler (her birini --- ile ayır)</label>
            <textarea
              className="storyforge-textarea sf-paste-area"
              rows={16}
              placeholder={"BAŞLIK: İlk Hikaye\nHikaye metni burada…\n\n---\n\nBAŞLIK: İkinci Hikaye\nİkinci hikaye metni…"}
              value={bulkPaste}
              onChange={(e) => setBulkPaste(e.target.value)}
              disabled={batchRunning}
            />
            {pastePreview?.count > 0 && (
              <p className="sf-preview-count">
                <strong>{pastePreview.count}</strong> hikaye algılandı
                {pastePreview.preview?.slice(0, 3).map((p, i) => (
                  <span key={i} className="sf-dim"> · {p.title} ({p.words} kelime)</span>
                ))}
              </p>
            )}
            <button type="button" className="btn btn-primary" onClick={handlePasteRun} disabled={batchRunning || !bulkPaste.trim()}>
              {batchRunning ? "Kuyrukta işleniyor…" : `📋 ${pastePreview?.count || "?"} Hikayeyi Çat Yayınla`}
            </button>
          </div>
        )}

        {bulkMode === "file" && (
          <div className="sf-mode-panel">
            <div
              className="sf-dropzone"
              onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add("drag"); }}
              onDragLeave={(e) => e.currentTarget.classList.remove("drag")}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove("drag");
                const f = e.dataTransfer.files?.[0];
                if (f) handleFileDrop(f);
              }}
            >
              <p>{importUploading ? "Dosya okunuyor…" : "Dosyayı sürükle-bırak veya seç"}</p>
              <p className="sf-dim">TXT · Word (.docx) · JSONL · CSV · JSON</p>
              <label className="btn btn-secondary storyforge-file-btn">
                Dosya Seç
                <input
                  type="file"
                  accept=".txt,.docx,.jsonl,.ndjson,.csv,.json,text/plain"
                  onChange={(e) => handleFileDrop(e.target.files?.[0])}
                  disabled={importUploading || batchRunning}
                  hidden
                />
              </label>
            </div>
            {importInfo && (
              <div className="sf-import-summary">
                <span>✅ <strong>{importInfo.count}</strong> hikaye yüklendi</span>
                <span className="sf-dim">ID: {importId}</span>
              </div>
            )}
            {importInfo?.preview?.length > 0 && (
              <ul className="storyforge-photo-list">
                {importInfo.preview.map((p, i) => (
                  <li key={i}>{p.title} <span className="sf-dim">({p.content?.split?.(" ")?.length || p.words || "?"} kelime)</span></li>
                ))}
              </ul>
            )}
            <details className="sf-advanced">
              <summary>Gelişmiş (offset / limit / gecikme)</summary>
              <div className="storyforge-meta-row">
                <div>
                  <label className="storyforge-label">Offset</label>
                  <input type="number" min={0} className="storyforge-input" value={bulkOffset} onChange={(e) => setBulkOffset(Number(e.target.value))} />
                </div>
                <div>
                  <label className="storyforge-label">Limit (0=hepsi)</label>
                  <input type="number" min={0} className="storyforge-input" value={bulkLimit} onChange={(e) => setBulkLimit(Number(e.target.value))} />
                </div>
                <div>
                  <label className="storyforge-label">Gecikme (sn)</label>
                  <input type="number" min={0} step={0.5} className="storyforge-input" value={bulkDelay} onChange={(e) => setBulkDelay(Number(e.target.value))} />
                </div>
              </div>
            </details>
            <button type="button" className="btn btn-primary" onClick={handleBulkRewrite} disabled={batchRunning || !importId}>
              {batchRunning ? "Arka planda işleniyor…" : "📁 Yayınlamayı Başlat"}
            </button>
          </div>
        )}

        {rules && (
          <details className="storyforge-rules">
            <summary>SEO / GEO Kuralları (tüm modlar)</summary>
            <div className="storyforge-meta-row">
              <div>
                <label className="storyforge-label">Şehir</label>
                <input className="storyforge-input" value={rules.city || ""} onChange={(e) => updateRuleField("city", e.target.value)} />
              </div>
              <div>
                <label className="storyforge-label">Site URL</label>
                <input className="storyforge-input" value={rules.site_url || ""} onChange={(e) => updateRuleField("site_url", e.target.value)} />
              </div>
              <div>
                <label className="storyforge-label">Başlık şablonu</label>
                <input className="storyforge-input" value={rules.title_template || ""} onChange={(e) => updateRuleField("title_template", e.target.value)} placeholder="{location} {keyword} Hikayesi – Kuşadası" />
              </div>
            </div>
            <label className="storyforge-label">Lokasyonlar</label>
            <textarea className="storyforge-textarea" rows={3} value={(rules.locations || []).join("\n")} onChange={(e) => updateRuleList("locations", e.target.value)} />
            <label className="storyforge-label">Anahtar kelimeler</label>
            <textarea className="storyforge-textarea" rows={2} value={(rules.keywords || []).join("\n")} onChange={(e) => updateRuleList("keywords", e.target.value)} />
            <div className="storyforge-meta-row">
              <div>
                <label className="storyforge-label">Min kelime (bağlaç hariç)</label>
                <input type="number" min={300} className="storyforge-input" value={rules.min_words || 500} onChange={(e) => updateRuleField("min_words", Number(e.target.value))} />
              </div>
              <div>
                <label className="storyforge-label">Max kelime</label>
                <input type="number" min={800} className="storyforge-input" value={rules.max_words || 1800} onChange={(e) => updateRuleField("max_words", Number(e.target.value))} />
              </div>
              <div className="storyforge-check">
                <label>
                  <input type="checkbox" checked={rules.auto_category !== false} onChange={(e) => updateRuleField("auto_category", e.target.checked)} />
                  {" "}Otomatik kategori (ana+alt)
                </label>
              </div>
            </div>
            <label className="storyforge-label">Özel kurallar</label>
            <textarea className="storyforge-textarea" rows={2} value={rules.custom_rules || ""} onChange={(e) => updateRuleField("custom_rules", e.target.value)} />
            <button type="button" className="btn btn-secondary" onClick={handleSaveRules} disabled={rulesSaving}>
              {rulesSaving ? "Kaydediliyor…" : "Kuralları Kaydet"}
            </button>
          </details>
        )}
      </section>

      <section className="storyforge-auto">
        <h3>Otomatik Üretim &amp; Yayın</h3>
        <div className="storyforge-meta-row">
          <div>
            <label className="storyforge-label" htmlFor="sf-count">Adet</label>
            <input
              id="sf-count"
              type="number"
              min={1}
              max={200}
              className="storyforge-input"
              value={genCount}
              onChange={(e) => setGenCount(Number(e.target.value))}
              disabled={batchRunning}
            />
          </div>
          <div>
            <label className="storyforge-label" htmlFor="sf-cat-auto">Kategori</label>
            {renderCategorySelect("sf-cat-auto", batchRunning)}
          </div>
          <div className="storyforge-check">
            <label>
              <input
                type="checkbox"
                checked={autoPublish}
                onChange={(e) => setAutoPublish(e.target.checked)}
                disabled={batchRunning}
              />
              {" "}Otomatik yayınla
            </label>
          </div>
        </div>
        <div className="storyforge-btn-row">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleAutoGenerate}
            disabled={batchRunning}
          >
            {batchRunning ? "Çalışıyor…" : `${genCount} Hikaye Üret & Yayınla`}
          </button>
        </div>

        <label className="storyforge-label" htmlFor="sf-batch">Toplu URL (her satır bir link)</label>
        <textarea
          id="sf-batch"
          className="storyforge-textarea"
          rows={4}
          placeholder="https://www.literotica.com/s/...&#10;https://..."
          value={batchUrls}
          onChange={(e) => setBatchUrls(e.target.value)}
          disabled={batchRunning}
        />
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleBatchUrls}
          disabled={batchRunning}
        >
          URL Toplu İşle &amp; Yayınla
        </button>
      </section>

      {jobs.length > 0 && (
        <section className="storyforge-jobs">
          <h3>Son İşler</h3>
          <ul>
            {jobs.map((j) => (
              <li key={j.id}>
                <strong>{j.type}</strong> — {j.status}: {j.done}/{j.total}
                {j.published > 0 && ` (${j.published} yayın)`}
                {j.failed > 0 && ` (${j.failed} hata)`}
                {j.status === "completed" && (j.results || []).filter((r) => r.link).length > 0 && (
                  <ul className="sf-job-links">
                    {(j.results || []).filter((r) => r.link).slice(-5).map((r, i) => (
                      <li key={i}>
                        <a href={r.link} target="_blank" rel="noopener noreferrer">{r.title || r.link}</a>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {!hideManualUrl && (
        <>
          <hr className="storyforge-divider" />
          <section className="storyforge-manual">
            <h3>Tekil URL (manuel onay)</h3>
            <div className="storyforge-fetch">
              <label className="storyforge-label" htmlFor="sf-url">Hikaye URL</label>
              <div className="storyforge-url-row">
                <input
                  id="sf-url"
                  type="url"
                  className="storyforge-input"
                  placeholder="https://www.literotica.com/s/..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={loading}
                />
                <button type="button" className="btn btn-primary" onClick={handleFetch} disabled={loading}>
                  {loading ? "Çekiliyor…" : "Getir ve Dönüştür"}
                </button>
              </div>
            </div>
          </section>
        </>
      )}

      {hideManualUrl && (
        <p className="sf-dim sf-url-hint">
          URL&apos;den adım adım çekmek için üstteki <strong>Link Çekici</strong> sekmesini kullan.
        </p>
      )}

      {error && <p className="storyforge-error">{error}</p>}
      {message && (
        <p className="storyforge-ok">
          {message}
          {lastPublish?.link && message.includes("Yayınlandı") && (
            <> — <a href={lastPublish.link} target="_blank" rel="noopener noreferrer" className="sf-inline-link">{lastPublish.display_url || formatDisplayUrl(lastPublish.link)}</a></>
          )}
        </p>
      )}

      {pending.length > 0 && !rewritten && (
        <section className="storyforge-pending">
          <h3>Bekleyen ({pending.length})</h3>
          <ul>
            {pending.slice(0, 5).map((p) => (
              <li key={p.id}>
                {p.suggested_title || p.source_title} — {formatEngineName(p.engine) || p.engine}
              </li>
            ))}
          </ul>
        </section>
      )}

      {rewritten && (
        <div className="storyforge-editor">
          <div className="storyforge-meta-row">
            <div>
              <label className="storyforge-label" htmlFor="sf-title">Başlık</label>
              <input
                id="sf-title"
                className="storyforge-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div>
              <label className="storyforge-label" htmlFor="sf-lok">Lokasyon</label>
              <input
                id="sf-lok"
                className="storyforge-input"
                value={lokasyon}
                onChange={(e) => setLokasyon(e.target.value)}
                placeholder="Kuşadası Kadınlar Denizi"
              />
            </div>
            <div className="sf-cat-editor-pick">
              <label className="storyforge-label" htmlFor="sf-cat">Yayın kategorisi</label>
              {renderCategorySelect("sf-cat")}
            </div>
          </div>

          {(predictedCategories || publishedCategories) && (
            <div className="sf-cat-editor-preview">
              <strong>{publishedCategories ? "Yayınlandı:" : "Gideceği kategori:"}</strong>{" "}
              {formatCategoryPath(publishedCategories || predictedCategories)}
            </div>
          )}

          {engine && (
            <p className="storyforge-engine">
              Bu işlemde kullanılan motor: <strong>{formatEngineName(engine)}</strong>
              {engine !== formatEngineName(engine) && <span className="sf-dim"> ({engine})</span>}
            </p>
          )}

          {original && (
            <details className="storyforge-original">
              <summary>Orijinal metin (önizleme)</summary>
              <pre>{original.slice(0, 2000)}{original.length > 2000 ? "…" : ""}</pre>
            </details>
          )}

          <label className="storyforge-label" htmlFor="sf-content">Yeniden yazılan hikaye (düzenlenebilir)</label>
          <textarea
            id="sf-content"
            className="storyforge-textarea"
            rows={18}
            value={rewritten}
            onChange={(e) => setRewritten(e.target.value)}
          />

          <label className="storyforge-label" htmlFor="sf-excerpt">Özet / meta</label>
          <input
            id="sf-excerpt"
            className="storyforge-input"
            value={excerpt}
            onChange={(e) => setExcerpt(e.target.value)}
          />

          <button
            type="button"
            className="btn btn-primary storyforge-publish-btn"
            onClick={handlePublish}
            disabled={publishing}
          >
            {publishing ? "Yayınlanıyor…" : "Onayla ve WordPress'e Yayınla"}
          </button>
        </div>
      )}
    </div>
  );
}
