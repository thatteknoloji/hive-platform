import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

const DEPLOY_TARGETS = [
  { id: "cloudflare_pages", label: "Cloudflare Pages" },
  { id: "github_pages", label: "GitHub Pages" },
  { id: "vps", label: "VPS" },
];

const STATUS_LABEL = {
  draft: "Taslak",
  planned: "Planlandı",
  generated: "Üretildi",
  built: "Build alındı",
  exported: "Export hazır",
  deployed: "Cloudflare'de yayında",
};

export default function AstroFactory({ onNavigateQualityGate }) {
  const [tab, setTab] = useState("project");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [health, setHealth] = useState(null);
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [plan, setPlan] = useState(null);
  const [deployInfo, setDeployInfo] = useState(null);
  const [buildLog, setBuildLog] = useState("");
  const [cfStatus, setCfStatus] = useState(null);
  const [cfProjectName, setCfProjectName] = useState("");
  const [cfDeployments, setCfDeployments] = useState([]);
  const [cfDeployLog, setCfDeployLog] = useState("");
  const [cfDeployUrl, setCfDeployUrl] = useState("");
  const loadAutoPublisher = useCallback(async () => {
    try {
      const [h, s, q, j] = await Promise.all([
        API.get("/api/astro-auto/health"),
        API.get("/api/astro-auto/settings"),
        API.get("/api/astro-auto/queue"),
        API.get("/api/astro-auto/jobs?limit=15"),
      ]);
      setAutoHealth(h.data);
      setAutoSettings(s.data.settings);
      setAutoQueue(q.data.queue || []);
      setAutoJobs(j.data.jobs || []);
    } catch {
      setAutoHealth(null);
    }
  }, []);

  const saveAutoSettings = async (patch) => {
    setLoading(true);
    try {
      const res = await API.post("/api/astro-auto/settings", patch);
      setAutoSettings(res.data.settings);
      setMessage("Auto Publisher ayarları kaydedildi");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoSyncAll = async () => {
    if (!activeProject?.id) { setError("Önce bir proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-auto/sync-all", {
        project_id: activeProject.id,
        auto_deploy: autoSettings?.auto_deploy || false,
        auto_build: autoSettings?.auto_build !== false,
      });
      setMessage(`Sync tamam: ${res.data.summary?.created || 0} oluşturuldu, ${res.data.summary?.updated || 0} güncellendi`);
      await loadAutoPublisher();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoScan = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    try {
      const res = await API.post("/api/astro-auto/scan-missing", {
        project_id: activeProject.id,
        include_outdated: true,
      });
      setAutoScan(res.data);
      setMessage(`Tarama: ${res.data.missing?.length || 0} eksik, ${res.data.outdated?.length || 0} güncel değil`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoQueue = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    try {
      const res = await API.post("/api/astro-auto/queue-missing", { project_id: activeProject.id });
      setMessage(`${res.data.queued} öğe kuyruğa eklendi`);
      await loadAutoPublisher();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoProcess = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    try {
      const res = await API.post("/api/astro-auto/process-queue", {
        project_id: activeProject.id,
        auto_deploy: autoSettings?.auto_deploy || false,
        auto_build: autoSettings?.auto_build !== false,
      });
      setMessage(`Kuyruk işlendi — build: ${res.data.summary?.built ? "✓" : "—"}, deploy: ${res.data.summary?.deployed ? "✓" : "—"}`);
      await loadAutoPublisher();
      await refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoDeploy = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    try {
      const res = await API.post("/api/astro-auto/deploy", { project_id: activeProject.id });
      setMessage(`Deploy: ${res.data.url || res.data.deployment_url || "tamamlandı"}`);
      await loadAutoPublisher();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (tab === "auto") loadAutoPublisher(); }, [tab, loadAutoPublisher]);
  const [autoHealth, setAutoHealth] = useState(null);
  const [autoSettings, setAutoSettings] = useState(null);
  const [autoQueue, setAutoQueue] = useState([]);
  const [autoJobs, setAutoJobs] = useState([]);
  const [autoScan, setAutoScan] = useState(null);

  const [form, setForm] = useState({
    site_name: "Kuşadası Gece Hayatı",
    domain: "kusadasigecehayati.com",
    seed_keyword: "kuşadası gece hayatı",
    location: "Kuşadası",
    niche: "gece hayatı",
    language: "tr",
    main_site_url: "https://www.balkutusu.com",
    deploy_target: "cloudflare_pages",
    page_count: 10,
  });

  const loadCfStatus = useCallback(async () => {
    try {
      const res = await API.get("/api/astro-factory/cloudflare/status");
      setCfStatus(res.data);
    } catch {
      setCfStatus({ configured: false, token_present: false, account_id_present: false });
    }
  }, []);

  const loadCfDeployments = useCallback(async (projectId) => {
    if (!projectId) return;
    try {
      const res = await API.get(`/api/astro-factory/cloudflare/deployments/${projectId}`);
      setCfDeployments(res.data.deployments || []);
      const cf = res.data.cloudflare || {};
      if (cf.project_name) setCfProjectName(cf.project_name);
      if (cf.latest_url) setCfDeployUrl(cf.latest_url);
    } catch {
      setCfDeployments([]);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [h, pl] = await Promise.all([
        API.get("/api/astro-factory/health"),
        API.get("/api/astro-factory/projects"),
      ]);
      setHealth(h.data);
      setProjects(pl.data.projects || []);
      await loadCfStatus();
    } catch (e) {
      if (e.response?.status === 404) {
        setError("Astro Factory API yok — backend yeniden başlat: npm run stop && npm start");
      }
    }
  }, [loadCfStatus]);

  useEffect(() => { refresh(); }, [refresh]);

  const loadProject = async (id) => {
    try {
      const res = await API.get(`/api/astro-factory/project/${id}`);
      const p = res.data.project;
      setActiveProject(p);
      setPlan(p?.plan || null);
      setBuildLog(p?.build_log || "");
      setCfProjectName(p?.cloudflare?.project_name || `hive-${p?.slug || ""}`);
      setCfDeployUrl(p?.cloudflare?.latest_url || "");
      await loadCfDeployments(id);
      setTab("plan");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const handleCreate = async () => {
    if (!form.site_name.trim()) { setError("Site adı gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-factory/create-project", form);
      setActiveProject(res.data.project);
      setMessage(`Proje oluşturuldu — klasör: ${res.data.filesystem_path || res.data.project.path}`);
      await refresh();
      setTab("plan");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePlan = async () => {
    if (!activeProject?.id) { setError("Önce proje oluştur"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-factory/generate-plan", {
        project_id: activeProject.id,
        seed_keyword: form.seed_keyword || activeProject.seed_keyword,
        location: form.location,
        niche: form.niche,
        page_count: form.page_count,
        domain: form.domain || activeProject.domain,
      });
      setPlan(res.data.plan);
      setMessage(`Plan hazır — Talon: ${res.data.plan?.talon_meta?.favorites || 0} favori, ${res.data.plan?.talon_meta?.generated || 0} üretim`);
      await loadProject(activeProject.id);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePages = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-factory/generate-pages", { project_id: activeProject.id });
      setMessage(
        `Üretildi: ${res.data.geo_count} GEO, ${res.data.faq_count} SSS, ${res.data.blog_count} blog → ${res.data.path}`
      );
      await loadProject(activeProject.id);
      setTab("build");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleQualityGate = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    setError("");
    setQgReport(null);
    try {
      const res = await API.post("/api/seo-quality-gate/analyze-project", {
        project_id: activeProject.id,
        target_keyword: form.seed_keyword || activeProject.seed_keyword,
        main_site_url: form.main_site_url || activeProject.main_site_url,
        strict_mode: true,
      });
      setQgReport(res.data);
      const st = res.data.status;
      setMessage(
        `SEO GEO AEO Gate: ${res.data.overall_score}/100 — ${st.toUpperCase()} ` +
        `(SEO ${res.data.seo_score} · GEO ${res.data.geo_score} · AEO ${res.data.aeo_score})`
      );
      if (st === "fail") {
        setError("Kalite kapısı FAIL — deploy önerilmez (overall < 70 veya risk > 60)");
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBuild = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    setError("");
    setBuildLog("");
    try {
      const res = await API.post("/api/astro-factory/build", { project_id: activeProject.id });
      setBuildLog(res.data.build_log || "");
      if (res.data.dist_exists) {
        setMessage(`Build OK — dist: ${res.data.dist}`);
      } else {
        setMessage("Build tamamlandı ama dist doğrulanamadı");
      }
      await loadProject(activeProject.id);
    } catch (e) {
      const d = e.response?.data;
      const detail = d?.detail;
      const log = (typeof detail === "object" && detail?.build_log) ? detail.build_log : (d?.build_log || "");
      setBuildLog(log || (typeof detail === "string" ? detail : e.message));
      setError(
        typeof detail === "object" ? (detail?.error || "Build başarısız")
          : (typeof detail === "string" ? detail : e.message)
      );
      await loadProject(activeProject.id);
    } finally {
      setLoading(false);
    }
  };

  const handleCfCreate = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-factory/cloudflare/create-project", {
        project_id: activeProject.id,
        cloudflare_project_name: cfProjectName.trim(),
      });
      setMessage(
        res.data.already_existed
          ? `Cloudflare projesi zaten var: ${res.data.cloudflare?.project_name}`
          : `Cloudflare Pages projesi oluşturuldu: ${res.data.cloudflare?.project_name}`
      );
      await loadProject(activeProject.id);
    } catch (e) {
      const d = e.response?.data?.detail;
      setError(typeof d === "string" ? d : (d?.error || e.message));
    } finally {
      setLoading(false);
    }
  };

  const handleCfDeploy = async () => {
    if (!activeProject?.id) return;
    if (!activeProject.dist_exists) {
      setError("Build alınmamış. Önce build çalıştır.");
      return;
    }
    setLoading(true);
    setError("");
    setCfDeployLog("");
    try {
      const res = await API.post("/api/astro-factory/cloudflare/deploy", {
        project_id: activeProject.id,
      });
      setCfDeployLog(res.data.log || "");
      setCfDeployUrl(res.data.url || res.data.cloudflare?.latest_url || "");
      setMessage(`Cloudflare deploy OK → ${res.data.url || "URL logda"}`);
      await loadProject(activeProject.id);
      await loadCfDeployments(activeProject.id);
    } catch (e) {
      const d = e.response?.data?.detail;
      const log = (typeof d === "object" && d?.log) ? d.log : "";
      setCfDeployLog(log);
      setError(typeof d === "object" ? (d?.error || "Deploy başarısız") : (d || e.message));
      await loadCfDeployments(activeProject.id);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-factory/export", { project_id: activeProject.id });
      setDeployInfo(res.data.deploy_instructions);
      setMessage(`ZIP: ${res.data.export_path}`);
      await loadProject(activeProject.id);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Projeyi ve dosyalarını sil?")) return;
    setLoading(true);
    try {
      await API.delete(`/api/astro-factory/project/${id}`);
      if (activeProject?.id === id) { setActiveProject(null); setPlan(null); setBuildLog(""); }
      setMessage("Proje silindi");
      await refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const TABS = [
    { id: "project", label: "1. Proje" },
    { id: "plan", label: "2. Plan" },
    { id: "content", label: "3. İçerik" },
    { id: "build", label: "4. Build & Export" },
    { id: "auto", label: "⚡ Auto Publisher" },
    { id: "list", label: `Projeler (${projects.length})` },
  ];

  return (
    <div className="category-hub astro-factory">
      <header className="ch-header">
        <h2>🚀 Astro Site Factory</h2>
        <p className="ch-sub">
          Gerçek Astro projesi — filesystem, npm build, ZIP export
          {health?.template_exists ? (
            <span className="sf-ok"> · Şablon OK</span>
          ) : (
            <span className="ch-warn"> · Şablon eksik</span>
          )}
          {health?.npm?.available ? (
            <span className="sf-ok"> · npm {health.npm.version}</span>
          ) : (
            <span className="ch-warn"> · npm yok</span>
          )}
        </p>
      </header>

      {activeProject && (
        <div className="ch-selected-head">
          <h3>📍 {activeProject.site_name}</h3>
          <span className="sf-dim">
            #{activeProject.id} · {STATUS_LABEL[activeProject.status] || activeProject.status}
          </span>
          <div className="sf-dim">
            Path: <code>{activeProject.filesystem_path || activeProject.path}</code>
          </div>
          <div className={activeProject.dist_exists ? "sf-ok" : "sf-warn"}>
            dist: {activeProject.dist_exists ? "✓ hazır" : "○ yok — Build çalıştır"}
          </div>
        </div>
      )}

      <div className="ch-tabs">
        {TABS.map((t) => (
          <button key={t.id} type="button" className={`ch-tab ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "project" && (
        <div className="ch-panel">
          <h4>Proje bilgileri</h4>
          <div className="storyforge-meta-row">
            <div>
              <label className="storyforge-label">Site adı *</label>
              <input className="storyforge-input" value={form.site_name} onChange={(e) => setForm({ ...form, site_name: e.target.value })} />
            </div>
            <div>
              <label className="storyforge-label">Domain</label>
              <input className="storyforge-input" value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} placeholder="kusadasigecehayati.com" />
            </div>
          </div>
          <div className="storyforge-meta-row">
            <div>
              <label className="storyforge-label">Ana keyword *</label>
              <input className="storyforge-input" value={form.seed_keyword} onChange={(e) => setForm({ ...form, seed_keyword: e.target.value })} />
            </div>
            <div>
              <label className="storyforge-label">Lokasyon</label>
              <input className="storyforge-input" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
            </div>
          </div>
          <div className="storyforge-meta-row">
            <div>
              <label className="storyforge-label">Niş</label>
              <input className="storyforge-input" value={form.niche} onChange={(e) => setForm({ ...form, niche: e.target.value })} />
            </div>
            <div>
              <label className="storyforge-label">Ana site (main_site_url)</label>
              <input className="storyforge-input" value={form.main_site_url} onChange={(e) => setForm({ ...form, main_site_url: e.target.value })} />
            </div>
          </div>
          <div className="storyforge-meta-row">
            <div>
              <label className="storyforge-label">Yayın hedefi</label>
              <select className="storyforge-input" value={form.deploy_target} onChange={(e) => setForm({ ...form, deploy_target: e.target.value })}>
                {DEPLOY_TARGETS.map((d) => <option key={d.id} value={d.id}>{d.label}</option>)}
              </select>
            </div>
            <div>
              <label className="storyforge-label">Sayfa sayısı</label>
              <input type="number" className="storyforge-input" min={5} max={30} value={form.page_count} onChange={(e) => setForm({ ...form, page_count: Number(e.target.value) })} />
            </div>
          </div>
          <button type="button" className="btn btn-primary ch-btn-create" onClick={handleCreate} disabled={loading}>
            {loading ? "…" : "✅ Proje Oluştur (gerçek klasör)"}
          </button>
        </div>
      )}

      {tab === "plan" && (
        <div className="ch-panel">
          <h4>Site haritası</h4>
          <button type="button" className="btn btn-primary" onClick={handlePlan} disabled={loading || !activeProject}>
            {loading ? "…" : "🗺 Plan Üret (Talon)"}
          </button>
          {plan && (
            <div className="ch-preview-box">
              <strong>{plan.site_name}</strong>
              <p className="sf-dim">GEO {plan.geo_pages?.length} · SSS {plan.faq_pages?.length} · Blog {plan.blog_posts?.length}</p>
              <pre className="ch-preview-snippet">{JSON.stringify(plan.talon_meta, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {tab === "content" && (
        <div className="ch-panel">
          <h4>İçerik + Astro dosyaları</h4>
          <p className="sf-dim">pages.json, faqs.json, blog.json, robots, sitemap, schema — gerçek dosya yazımı</p>
          <button type="button" className="btn btn-primary" onClick={handleGeneratePages} disabled={loading || !activeProject}>
            {loading ? "Üretiliyor…" : "📁 Sayfaları Üret"}
          </button>
        </div>
      )}

      {tab === "build" && (
        <div className="ch-panel">
          <h4>Build & Export</h4>
          <div className="ch-create-actions">
            <button type="button" className="btn btn-secondary" onClick={handleBuild} disabled={loading || !activeProject}>
              {loading ? "…" : "🔨 npm install && npm run build"}
            </button>
            <button type="button" className="btn btn-primary" onClick={handleExport} disabled={loading || !activeProject}>
              📦 ZIP Export
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleQualityGate}
              disabled={loading || !activeProject}
            >
              🛡️ SEO GEO AEO Gate Analizi
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAutoScan}
              disabled={loading || !activeProject}
            >
              🤖 Auto Publisher ile eksikleri tara
            </button>
          </div>
          {qgReport && (
            <div className="ch-preview-box" style={{ marginTop: "0.75rem" }}>
              <strong>Gate: {qgReport.overall_score}/100 — {qgReport.status?.toUpperCase()}</strong>
              <p className="sf-dim">
                SEO {qgReport.seo_score} · GEO {qgReport.geo_score} · AEO {qgReport.aeo_score} ·
                Entity {qgReport.entity_score} · Risk {qgReport.risk_score}
              </p>
              <p className="sf-dim">
                Critical: {qgReport.critical_issues?.length || 0} · Warnings: {qgReport.warnings?.length || 0}
                {qgReport.deploy_allowed === false && " · Deploy kapalı"}
                {qgReport.geo_deploy_allowed === false && " · GEO deploy kapalı"}
              </p>
              {onNavigateQualityGate && (
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => onNavigateQualityGate(activeProject?.id)}
                >
                  Detaylı raporu aç →
                </button>
              )}
            </div>
          )}
          {(buildLog || activeProject?.build_log) && (
            <div className="ch-preview-box">
              <strong>Build log</strong>
              <pre className="ch-preview-snippet" style={{ maxHeight: 280, overflow: "auto" }}>
                {buildLog || activeProject.build_log}
              </pre>
            </div>
          )}
          {deployInfo && (
            <div className="ch-created-log">
              <h4>ZIP Deploy notları</h4>
              {Object.entries(deployInfo).map(([k, v]) => (
                <pre key={k} className="ch-preview-snippet">{k}: {v}</pre>
              ))}
            </div>
          )}

          <hr className="sf-divider" />
          <h4>☁️ Cloudflare Pages Auto Deploy</h4>
          <div className="ch-preview-box">
            <p className={cfStatus?.configured ? "sf-ok" : "ch-warn"}>
              Cloudflare env: {cfStatus?.configured ? "✓ yapılandırıldı" : "○ eksik"}
              {cfStatus && (
                <span className="sf-dim">
                  {" "}· token:{cfStatus.token_present ? "✓" : "—"}
                  {" "}· account:{cfStatus.account_id_present ? "✓" : "—"}
                </span>
              )}
            </p>
            {!cfStatus?.configured && (
              <p className="sf-dim">backend/.env → CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID</p>
            )}
          </div>
          <div className="storyforge-meta-row">
            <div>
              <label className="storyforge-label">Cloudflare project name</label>
              <input
                className="storyforge-input"
                value={cfProjectName}
                onChange={(e) => setCfProjectName(e.target.value)}
                placeholder="hive-kusadasi-gece-hayati"
              />
            </div>
          </div>
          <div className="ch-create-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleCfCreate}
              disabled={loading || !activeProject || !cfStatus?.configured}
            >
              Create Pages Project
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleCfDeploy}
              disabled={loading || !activeProject || !cfStatus?.configured || !activeProject?.dist_exists}
            >
              {loading ? "Deploy…" : "🚀 Deploy to Cloudflare Pages"}
            </button>
          </div>
          {cfDeployUrl && (
            <p className="storyforge-ok">
              Deployment URL:{" "}
              <a href={cfDeployUrl} target="_blank" rel="noopener noreferrer">{cfDeployUrl}</a>
            </p>
          )}
          {(cfDeployLog || cfDeployments[0]?.log) && (
            <div className="ch-preview-box">
              <strong>Son deploy log</strong>
              <pre className="ch-preview-snippet" style={{ maxHeight: 220, overflow: "auto" }}>
                {cfDeployLog || cfDeployments[0]?.log}
              </pre>
            </div>
          )}
          {cfDeployments.length > 0 && (
            <div className="ch-created-log">
              <strong>Deploy geçmişi</strong>
              <ul className="ch-queue-list">
                {cfDeployments.slice(0, 8).map((d, i) => (
                  <li key={d.deployment_id || i}>
                    <span className={d.status === "success" ? "sf-ok" : "ch-warn"}>{d.status}</span>
                    {" · "}{d.created_at}
                    {d.url && (
                      <> · <a href={d.url} target="_blank" rel="noopener noreferrer">{d.url}</a></>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {tab === "auto" && (
        <div className="ch-panel">
          <h4>⚡ Astro Auto Publisher / Site Sync Engine</h4>
          <p className="ch-sub">Gerçek tarama · gerçek Astro data · gerçek build · gerçek Cloudflare deploy</p>
          {!activeProject && <p className="ch-warn">Önce bir proje seçin (Projeler sekmesi)</p>}

          <div className="storyforge-meta-row" style={{ marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <button type="button" className="btn btn-primary" disabled={loading || !activeProject} onClick={handleAutoSyncAll}>
              {loading ? "…" : "🔄 Sync All"}
            </button>
            <button type="button" className="btn btn-outline" disabled={loading || !activeProject} onClick={handleAutoScan}>Scan Missing</button>
            <button type="button" className="btn btn-outline" disabled={loading || !activeProject} onClick={handleAutoQueue}>Queue Missing</button>
            <button type="button" className="btn btn-outline" disabled={loading || !activeProject} onClick={handleAutoProcess}>Process Queue</button>
            <button type="button" className="btn btn-outline" disabled={loading || !activeProject} onClick={handleAutoDeploy}>Deploy CF</button>
          </div>

          {autoHealth && (
            <p className="sf-dim">
              Kuyruk: {autoHealth.queue_size} · CF: {autoHealth.cloudflare_configured ? "✓" : "—"} · Scheduler: {autoHealth.scheduler_active ? "aktif" : "—"}
              {autoHealth.last_deploy_url && <> · Son deploy: <a href={autoHealth.last_deploy_url} target="_blank" rel="noreferrer">{autoHealth.last_deploy_url}</a></>}
            </p>
          )}

          {autoSettings && (
            <div className="ch-panel" style={{ marginTop: "1rem", background: "rgba(0,0,0,0.15)" }}>
              <h5>Ayarlar</h5>
              <div style={{ display: "grid", gap: "0.5rem", maxWidth: 480 }}>
                <label><input type="checkbox" checked={!!autoSettings.auto_build} onChange={(e) => saveAutoSettings({ auto_build: e.target.checked })} /> Auto Build</label>
                <label><input type="checkbox" checked={!!autoSettings.auto_deploy} onChange={(e) => saveAutoSettings({ auto_deploy: e.target.checked })} /> Auto Deploy</label>
                <p className="ch-warn" style={{ fontSize: "0.8rem", margin: 0 }}>Quality Gate fail olan içerikler deploy edilmez.</p>
                <label><input type="checkbox" checked={!!autoSettings.require_quality_gate_pass} onChange={(e) => saveAutoSettings({ require_quality_gate_pass: e.target.checked })} /> Quality Gate zorunlu</label>
                <label>Min skor <input type="number" min={0} max={100} value={autoSettings.min_quality_score} onChange={(e) => saveAutoSettings({ min_quality_score: Number(e.target.value) })} style={{ width: 70, marginLeft: 8 }} /></label>
                <label><input type="checkbox" checked={!!autoSettings.enabled} onChange={(e) => saveAutoSettings({ enabled: e.target.checked, target_project_id: activeProject?.id || "" })} /> Otomatik tarama ({autoSettings.interval_minutes} dk)</label>
              </div>
              <div style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
                <strong>Kaynaklar:</strong>
                {Object.entries(autoSettings.sources || {}).map(([k, v]) => (
                  <label key={k} style={{ marginLeft: 12 }}>
                    <input type="checkbox" checked={!!v} onChange={(e) => saveAutoSettings({ sources: { ...autoSettings.sources, [k]: e.target.checked } })} /> {k}
                  </label>
                ))}
              </div>
            </div>
          )}

          {autoScan && (
            <div className="ch-created-log" style={{ marginTop: "1rem" }}>
              <strong>Son tarama</strong>
              <ul className="ch-queue-list">
                <li>Eksik: {autoScan.missing?.length || 0}</li>
                <li>Güncel değil: {autoScan.outdated?.length || 0}</li>
                <li>Sync OK: {autoScan.synced?.length || autoScan.already_synced?.length || 0}</li>
                <li>Gate engeli: {autoScan.blocked?.length || autoScan.blocked_by_quality?.length || 0}</li>
              </ul>
            </div>
          )}

          {autoQueue.length > 0 && (
            <div style={{ marginTop: "1rem", overflowX: "auto" }}>
              <strong>Kuyruk ({autoQueue.length})</strong>
              <table style={{ width: "100%", fontSize: "0.8rem", marginTop: 8 }}>
                <thead><tr><th>Kaynak</th><th>Başlık</th><th>Slug</th><th>Tip</th><th>Durum</th></tr></thead>
                <tbody>
                  {autoQueue.slice(0, 20).map((q, i) => (
                    <tr key={i}><td>{q.source}</td><td>{q.title}</td><td>{q.slug}</td><td>{q.type}</td><td>{q.status}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {autoJobs.length > 0 && (
            <div className="ch-created-log" style={{ marginTop: "1rem" }}>
              <strong>Job geçmişi</strong>
              <ul className="ch-queue-list">
                {autoJobs.slice(0, 8).map((j) => (
                  <li key={j.job_id}>
                    <span className={j.status === "completed" ? "sf-ok" : j.status === "failed" ? "ch-warn" : ""}>{j.status}</span>
                    {" · "}{j.job_id} · {j.type}
                    {j.summary && <> · +{j.summary.created || 0} / ~{j.summary.updated || 0}</>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {tab === "list" && (
        <div className="ch-panel">
          <h4>Projeler</h4>
          <ul className="ch-queue-list">
            {projects.map((p) => (
              <li key={p.id}>
                <button type="button" className="ch-link-btn" onClick={() => loadProject(p.id)}>{p.site_name}</button>
                <span className="sf-dim"> · {STATUS_LABEL[p.status]} · dist:{p.dist_exists ? "✓" : "—"}</span>
                <button type="button" className="btn btn-outline btn-small" onClick={() => handleDelete(p.id)}>Sil</button>
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
