import React, { useState, useEffect, useCallback, useRef } from "react";
import API from "../api";

const STEPS = [
  { id: "upload", num: 1, label: "Dosya Yükle" },
  { id: "signals", num: 2, label: "Sinyaller" },
  { id: "plan", num: 3, label: "İçerik Planı" },
  { id: "pages", num: 4, label: "WordPress Yayın" },
  { id: "publish", num: 5, label: "Yayın & Rapor" },
];

const ACCEPT = ".docx,.csv,.xlsx,.xls,.json,.txt,.md";

const S = {
  page: { maxWidth: 1100, margin: "0 auto" },
  hero: {
    background: "linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(16,185,129,0.08) 100%)",
    border: "1px solid var(--border)",
    borderRadius: 14,
    padding: "1.25rem 1.5rem",
    marginBottom: "1.25rem",
  },
  card: {
    background: "var(--bg-secondary, rgba(255,255,255,0.03))",
    border: "1px solid var(--border)",
    borderRadius: 12,
    padding: "1.25rem",
    marginBottom: "1rem",
  },
  statGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))",
    gap: "0.75rem",
    marginBottom: "1.25rem",
  },
  stat: (accent) => ({
    background: "var(--bg-secondary, rgba(255,255,255,0.03))",
    border: `1px solid ${accent ? "rgba(99,102,241,0.35)" : "var(--border)"}`,
    borderRadius: 10,
    padding: "0.85rem 0.5rem",
    textAlign: "center",
  }),
  dropzone: (active) => ({
    border: `2px dashed ${active ? "#6366f1" : "var(--border)"}`,
    borderRadius: 12,
    padding: "2rem 1.5rem",
    textAlign: "center",
    cursor: "pointer",
    background: active ? "rgba(99,102,241,0.06)" : "transparent",
    transition: "all 0.2s",
  }),
  stepBar: {
    display: "flex",
    gap: 4,
    marginBottom: "1.25rem",
    flexWrap: "wrap",
  },
  step: (active, done) => ({
    flex: "1 1 120px",
    padding: "0.55rem 0.75rem",
    borderRadius: 8,
    fontSize: "0.78rem",
    fontWeight: active ? 600 : 400,
    textAlign: "center",
    border: `1px solid ${active ? "#6366f1" : done ? "rgba(16,185,129,0.4)" : "var(--border)"}`,
    background: active ? "rgba(99,102,241,0.15)" : done ? "rgba(16,185,129,0.08)" : "transparent",
    color: active ? "inherit" : done ? "#10b981" : "var(--text-muted)",
    cursor: "pointer",
  }),
  btnPrimary: {
    padding: "0.55rem 1.25rem",
    borderRadius: 8,
    fontWeight: 600,
    border: "none",
    cursor: "pointer",
  },
  fileChip: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "4px 10px",
    borderRadius: 20,
    fontSize: "0.78rem",
    background: "rgba(99,102,241,0.12)",
    border: "1px solid rgba(99,102,241,0.25)",
    margin: "4px",
  },
  alertErr: {
    padding: "0.75rem 1rem",
    borderRadius: 8,
    background: "rgba(248,113,113,0.12)",
    border: "1px solid rgba(248,113,113,0.35)",
    color: "#fca5a5",
    marginBottom: "1rem",
    fontSize: "0.88rem",
  },
  alertOk: {
    padding: "0.75rem 1rem",
    borderRadius: 8,
    background: "rgba(16,185,129,0.1)",
    border: "1px solid rgba(16,185,129,0.3)",
    color: "#6ee7b7",
    marginBottom: "1rem",
    fontSize: "0.88rem",
  },
  alertWarn: {
    padding: "0.75rem 1rem",
    borderRadius: 8,
    background: "rgba(251,191,36,0.1)",
    border: "1px solid rgba(251,191,36,0.3)",
    color: "#fcd34d",
    marginBottom: "1rem",
    fontSize: "0.88rem",
  },
};

function apiError(e, fallback = "İşlem başarısız") {
  const status = e?.response?.status;
  if (status === 404) {
    return "Backend eski sürümde çalışıyor (404 — place-seo route yok). Terminalde: bash scripts/stop-hive.sh && bash scripts/start-hive.sh";
  }
  if (status === 401) {
    return "API key hatası (401). backend/.env içindeki HIVE_API_KEY ile frontend/src/apiConfig.js eşleşmeli.";
  }
  if (!e?.response && e?.message?.includes("Network")) {
    return "Backend kapalı — bash scripts/start-hive.sh ile başlatın.";
  }
  return e?.hiveMessage || e?.response?.data?.detail || e?.message || fallback;
}

function StatBox({ label, value, highlight }) {
  const v = value ?? 0;
  return (
    <div className={`hive-stat ${highlight && v > 0 ? "hive-stat-accent" : ""}`}>
      <div className="hive-stat-label">{label}</div>
      <div className="hive-stat-value">{v}</div>
    </div>
  );
}

export default function PlaceSEOPipeline() {
  const [step, setStep] = useState("upload");
  const [backendOk, setBackendOk] = useState(null);
  const [health, setHealth] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState(null);
  const [mainSiteUrl, setMainSiteUrl] = useState("https://www.balkutusu.com");
  const [pendingFiles, setPendingFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [published, setPublished] = useState(null);
  const [forcePublish, setForcePublish] = useState(false);
  const fileRef = useRef(null);

  const loadJob = useCallback(async (id) => {
    if (!id) return null;
    const res = await API.get(`/api/place-seo/job/${id}`);
    setJob(res.data.job);
    return res.data.job;
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [h, jl] = await Promise.all([
        API.get("/api/place-seo/health"),
        API.get("/api/place-seo/jobs?limit=20"),
      ]);
      setBackendOk(true);
      setHealth(h.data);
      setJobs(jl.data.jobs || []);
      setError("");
    } catch (e) {
      setBackendOk(false);
      setError(apiError(e));
    }
  }, []);

  const handleConnectWordPress = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/place-seo/connect-wordpress");
      setMessage(`WordPress bağlandı: ${res.data.url || ""}`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const stored = sessionStorage.getItem("place_seo_job_id");
    if (stored) setJobId(stored);
  }, [refresh]);

  useEffect(() => {
    if (jobId && backendOk) {
      loadJob(jobId).catch((e) => setError(apiError(e)));
    }
  }, [jobId, backendOk, loadJob]);

  useEffect(() => {
    if (jobId) sessionStorage.setItem("place_seo_job_id", jobId);
  }, [jobId]);

  const addFiles = (fileList) => {
    const arr = Array.from(fileList || []);
    if (!arr.length) return;
    setPendingFiles((prev) => {
      const names = new Set(prev.map((f) => f.name + f.size));
      return [...prev, ...arr.filter((f) => !names.has(f.name + f.size))];
    });
  };

  const removeFile = (idx) => setPendingFiles((prev) => prev.filter((_, i) => i !== idx));

  const handleBatchUpload = async () => {
    if (!pendingFiles.length) {
      setError("En az 1 dosya seçin");
      return;
    }
    if (!mainSiteUrl.trim()) {
      setError("Ana site URL zorunlu");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    const fd = new FormData();
    pendingFiles.forEach((f) => fd.append("files", f));
    fd.append("main_site_url", mainSiteUrl.trim());
    fd.append("auto_pipeline", "true");
    try {
      const res = await API.post("/api/place-seo/upload-batch", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setJobId(res.data.job_id);
      setPendingFiles([]);
      setMessage(`${res.data.file_count} dosya işlendi → sinyaller ve plan hazır (Job: ${res.data.job_id})`);
      await loadJob(res.data.job_id);
      await refresh();
      setStep("plan");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const requireJob = () => {
    if (!jobId) {
      setError("Önce dosya yükleyin — Job oluşturulmadan bu adım çalışmaz.");
      setStep("upload");
      return false;
    }
    return true;
  };

  const handlePublishType = async (type) => {
    if (!requireJob()) return;
    setLoading(true);
    setError("");
    const endpoints = {
      category: "/api/place-seo/create-category-pages",
      geo: "/api/place-seo/create-geo-pages",
      faq: "/api/place-seo/create-faq-pages",
    };
    try {
      const res = await API.post(endpoints[type], {
        job_id: jobId,
        main_site_url: mainSiteUrl,
        dry_run: false,
        force: forcePublish,
      });
      setPublished({ type, items: res.data.created || [], errors: res.data.previews || [] });
      setMessage(`${type.toUpperCase()}: ${res.data.published_count || 0} sayfa WordPress'te yayında`);
      await loadJob(jobId);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handlePublishAll = async () => {
    if (!requireJob()) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/place-seo/publish-all", {
        job_id: jobId,
        main_site_url: mainSiteUrl,
        run_gate: true,
        force: forcePublish,
        include_astro: true,
      });
      const rep = res.data.publish_report || {};
      setPublished({ type: "all", items: res.data.created || [], errors: res.data.errors || [] });
      setMessage(`Yayın tamamlandı: ${rep.total_published || 0} sayfa canlı · ${(rep.live_links || []).length} link`);
      await loadJob(jobId);
      setStep("publish");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleAstro = async () => {
    if (!requireJob()) return;
    setLoading(true);
    try {
      const res = await API.post("/api/place-seo/create-astro-support-site", {
        job_id: jobId,
        main_site_url: mainSiteUrl,
      });
      setMessage(`Astro destek sitesi oluşturuldu: ${res.data.project_id}`);
      await loadJob(jobId);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleQualityGate = async () => {
    if (!requireJob()) return;
    setLoading(true);
    try {
      const res = await API.post("/api/place-seo/run-quality-gate", { job_id: jobId });
      setMessage(`Quality Gate: deploy_allowed = ${res.data.deploy_allowed}`);
      await loadJob(jobId);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!requireJob()) return;
    setLoading(true);
    try {
      const res = await API.post("/api/place-seo/export-report", { job_id: jobId });
      setMessage(`Rapor kaydedildi: ${res.data.report_path}`);
      await loadJob(jobId);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const signals = job?.signals || {};
  const plan = job?.plan || {};
  const summary = plan.summary || {};
  const stepDone = {
    upload: !!jobId,
    signals: !!signals.confidence,
    plan: !!plan.category_pages?.length,
    pages: !!(published?.items?.length || job?.publish_report?.total_published),
    publish: !!(job?.publish_report || job?.status === "published"),
  };

  return (
    <div className="hive-page modul-sayfa" style={{ padding: "1.25rem 1.5rem 2rem" }}>
      <div className="hive-hero">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h2>📍 Mekan SEO Content Pipeline</h2>
            <p style={{ maxWidth: 560 }}>
              Mekan rehber dosyalarından SEO/GEO/AEO içerik planı. <strong style={{ color: "#10b981" }}>Listing Hub ilanı oluşturulmaz.</strong>
            </p>
          </div>
          {backendOk === true && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
              <span style={{ fontSize: "0.75rem", padding: "4px 10px", borderRadius: 20, background: "rgba(16,185,129,0.15)", color: "#6ee7b7" }}>
                API bağlı · {health?.jobs_count ?? 0} job
              </span>
              <span style={{ fontSize: "0.72rem", color: health?.wordpress_connected ? "#6ee7b7" : "#fca5a5" }}>
                WordPress: {health?.wordpress_connected
                  ? `✓ ${health.wordpress_url || "bağlı"}`
                  : "✗ bağlı değil"}
              </span>
              {!health?.wordpress_connected && (
                <button type="button" className="btn-link" disabled={loading} onClick={handleConnectWordPress} style={{ fontSize: "0.72rem" }}>
                  .env ile bağlan
                </button>
              )}
            </div>
          )}
          {backendOk === false && (
            <span style={{ fontSize: "0.75rem", padding: "4px 10px", borderRadius: 20, background: "rgba(248,113,113,0.15)", color: "#fca5a5" }}>
              API offline
            </span>
          )}
        </div>
      </div>

      {backendOk === false && (
        <div className="hm-alert hm-alert-warn">
          Backend yeni modül route&apos;larını yüklemedi (eski process çalışıyor olabilir). Terminalde:{" "}
          <code style={{ fontSize: "0.8rem" }}>bash scripts/stop-hive.sh && bash scripts/start-hive.sh</code>
        </div>
      )}

      <div className="hive-stat-grid">
        <StatBox label="Güven" value={signals.confidence} highlight />
        <StatBox label="Entity" value={(signals.entities || []).length} highlight />
        <StatBox label="Kategori" value={summary.category_page_count} />
        <StatBox label="GEO" value={summary.geo_page_count} />
        <StatBox label="SSS" value={summary.faq_page_count} />
        <StatBox label="Blog" value={summary.blog_count} />
      </div>

      <div className="hive-card" style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "flex-end" }}>
        <label style={{ flex: "1 1 280px" }}>
          <span className="hive-stat-label" style={{ display: "block", marginBottom: 4 }}>Ana Site URL</span>
          <input className="hive-input" value={mainSiteUrl} onChange={(e) => setMainSiteUrl(e.target.value)} />
        </label>
        <label style={{ flex: "1 1 200px" }}>
          <span className="hive-stat-label" style={{ display: "block", marginBottom: 4 }}>Mevcut Job</span>
          <select className="hive-input" value={jobId} onChange={(e) => setJobId(e.target.value)}>
            <option value="">— Seçin veya yeni yükleyin —</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.id} · {j.status} · {j.filename || "?"}
              </option>
            ))}
          </select>
        </label>
        {jobId && (
          <div className="hive-muted">
            Durum: <strong>{job?.status || "—"}</strong>
            {(job?.filenames || []).length > 1 && <> · {job.filenames.length} dosya</>}
          </div>
        )}
      </div>

      <div className="hive-step-bar">
        {STEPS.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`hive-step ${step === s.id ? "active" : ""} ${stepDone[s.id] ? "done" : ""}`}
            onClick={() => setStep(s.id)}
          >
            {stepDone[s.id] ? "✓ " : `${s.num}. `}{s.label}
          </button>
        ))}
      </div>

      {error && <div className="hive-alert-err">{error}</div>}
      {message && <div className="hive-alert-ok">{message}</div>}

      {step === "upload" && (
        <div className="hive-card">
          <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Çoklu Dosya Yükle</h3>
          <div
            style={S.dropzone(dragOver)}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}
            onClick={() => fileRef.current?.click()}
          >
            <div style={{ fontSize: "2rem", marginBottom: 8 }}>📁</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Dosyaları sürükleyin veya tıklayın</div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              DOCX · CSV · XLSX · JSON · TXT · MD — birden fazla dosya seçilebilir
            </div>
            <input
              ref={fileRef}
              type="file"
              multiple
              accept={ACCEPT}
              style={{ display: "none" }}
              onChange={(e) => addFiles(e.target.files)}
            />
          </div>

          {pendingFiles.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 6 }}>
                {pendingFiles.length} dosya seçildi
              </div>
              <div style={{ display: "flex", flexWrap: "wrap" }}>
                {pendingFiles.map((f, i) => (
                  <span key={`${f.name}-${i}`} style={S.fileChip}>
                    {f.name}
                    <button type="button" onClick={() => removeFile(i)} style={{ background: "none", border: "none", cursor: "pointer", opacity: 0.7 }}>×</button>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginTop: "1.25rem", display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn-primary"
              disabled={loading || !pendingFiles.length || backendOk === false}
              onClick={handleBatchUpload}
              style={S.btnPrimary}
            >
              {loading ? "İşleniyor…" : "Yükle & Pipeline Başlat"}
            </button>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", alignSelf: "center" }}>
              Parse → sinyal → içerik planı otomatik
            </span>
          </div>
        </div>
      )}

      {step === "signals" && (
        <div className="hive-card">
          <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Çıkarılan Sinyaller</h3>
          {!jobId ? (
            <p style={{ color: "var(--text-muted)" }}>Henüz job yok — önce dosya yükleyin.</p>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.88rem" }}>
              <div>
                <strong style={{ display: "block", marginBottom: 6, color: "var(--text-muted)", fontSize: "0.75rem" }}>KATEGORİLER</strong>
                {(signals.categories || []).join(", ") || "—"}
              </div>
              <div>
                <strong style={{ display: "block", marginBottom: 6, color: "var(--text-muted)", fontSize: "0.75rem" }}>LOKASYONLAR</strong>
                {(signals.locations || []).join(", ") || "—"}
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <strong style={{ display: "block", marginBottom: 6, color: "var(--text-muted)", fontSize: "0.75rem" }}>ENTITY (mekan sinyalleri — listing değil)</strong>
                {(signals.entities || []).slice(0, 15).join(" · ") || "—"}
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <strong style={{ display: "block", marginBottom: 6, color: "var(--text-muted)", fontSize: "0.75rem" }}>SSS ADAYLARI</strong>
                <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
                  {(signals.faq_candidates || []).slice(0, 6).map((q, i) => <li key={i}>{q}</li>)}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {step === "plan" && (
        <div className="hive-card">
          <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>İçerik Planı Önizleme</h3>
          {!plan.category_pages?.length ? (
            <p style={{ color: "var(--text-muted)" }}>Plan henüz yok — dosya yükleyince otomatik oluşur.</p>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
              {[
                { title: "Kategori Sayfaları", items: plan.category_pages, key: "title" },
                { title: "GEO Sayfalar", items: plan.geo_pages, key: "title" },
                { title: "SSS", items: plan.faq_pages, key: "question" },
                { title: "Blog", items: plan.blog_posts, key: "title" },
              ].map((col) => (
                <div key={col.title} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "0.75rem" }}>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 8 }}>{col.title} ({col.items?.length || 0})</div>
                  <ul style={{ margin: 0, paddingLeft: "1rem", fontSize: "0.78rem", maxHeight: 200, overflow: "auto" }}>
                    {(col.items || []).slice(0, 12).map((p) => (
                      <li key={p.slug} style={{ marginBottom: 4 }}>{p[col.key] || p.title}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {step === "pages" && (
        <div className="hive-card">
          <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>WordPress&apos;e Gerçek Yayın</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "0 0 1rem" }}>
            Kategori, GEO ve SSS sayfaları publish statüsünde WordPress&apos;e gider. IndexNow ping atılır.
          </p>
          {!health?.wordpress_connected && (
            <div className="hive-alert-err" style={{ marginBottom: "1rem" }}>
              WordPress bağlı değil — backend/.env içinde WP_URL, WP_USERNAME, WP_APP_PASSWORD gerekli.
              {health?.wordpress_error && (
                <div style={{ marginTop: 6, fontSize: "0.82rem", opacity: 0.9 }}>{health.wordpress_error}</div>
              )}
              <button type="button" className="btn btn-secondary" disabled={loading} onClick={handleConnectWordPress} style={{ marginTop: 8 }}>
                WordPress&apos;e Bağlan (.env)
              </button>
            </div>
          )}
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "1rem", fontSize: "0.85rem" }}>
            <input type="checkbox" checked={forcePublish} onChange={(e) => setForcePublish(e.target.checked)} />
            Quality Gate engelini atla (force)
          </label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: "1rem" }}>
            <button type="button" className="btn-primary" disabled={loading || !jobId || !health?.wordpress_connected} onClick={handlePublishAll} style={S.btnPrimary}>
              {loading ? "Yayınlanıyor…" : "Tümünü Yayınla (Gate + WP + Astro)"}
            </button>
            {[
              { id: "category", label: "Kategori" },
              { id: "geo", label: "GEO" },
              { id: "faq", label: "SSS" },
            ].map((b) => (
              <button key={b.id} type="button" disabled={loading || !jobId || !health?.wordpress_connected} onClick={() => handlePublishType(b.id)}>
                {b.label} Yayınla
              </button>
            ))}
          </div>
          {(published?.items?.length > 0 || job?.publish_report?.live_links?.length > 0) && (
            <div>
              <strong style={{ fontSize: "0.85rem" }}>Canlı yayınlanan sayfalar</strong>
              <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.2rem", fontSize: "0.82rem" }}>
                {(published?.items || []).map((p) => (
                  <li key={p.slug}>
                    {p.title}
                    {p.link && <> · <a href={p.link} target="_blank" rel="noreferrer">{p.link}</a></>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {step === "publish" && (
        <div style={{ display: "grid", gap: "1rem" }}>
          <div className="hive-card">
            <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Astro Destek Sitesi</h3>
            <button type="button" className="btn-primary" disabled={loading || !jobId} onClick={handleAstro} style={S.btnPrimary}>
              Rehber Sitesi Oluştur
            </button>
            {job?.astro_project_id && (
              <p style={{ marginTop: 8, fontSize: "0.85rem" }}>Proje: <code>{job.astro_project_id}</code></p>
            )}
          </div>
          <div className="hive-card">
            <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Quality Gate</h3>
            <button type="button" disabled={loading || !jobId} onClick={handleQualityGate}>Quality Gate Çalıştır</button>
            {job?.quality_gate && (
              <div style={{ marginTop: 12, fontSize: "0.85rem" }}>
                deploy_allowed: <strong style={{ color: job.deploy_allowed ? "#10b981" : "#f87171" }}>{String(job.deploy_allowed)}</strong>
              </div>
            )}
          </div>
          <div className="hive-card">
            <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Link Planı</h3>
            {plan.main_site_link_plan?.length ? (
              <pre style={{ fontSize: "0.72rem", maxHeight: 200, overflow: "auto", margin: 0 }}>
                {JSON.stringify(plan.main_site_link_plan.slice(0, 8), null, 2)}
              </pre>
            ) : (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Plan oluşturulunca link planı burada görünür.</p>
            )}
          </div>
          <div className="hive-card">
            <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>Rapor Export</h3>
            <button type="button" className="btn-primary" disabled={loading || !jobId} onClick={handleExport} style={S.btnPrimary}>
              JSON Rapor İndir
            </button>
            {job?.report_path && <p style={{ marginTop: 8, fontSize: "0.8rem", opacity: 0.7 }}>{job.report_path}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
