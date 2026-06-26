import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";


const STEPS = [
  { id: "clone", label: "Owned Site Clone" },
  { id: "variant", label: "Domain Variant" },
  { id: "blueprint", label: "Competitor Blueprint" },
  { id: "template", label: "Original Template" },
  { id: "deploy", label: "Build & Deploy" },
  { id: "jobs", label: "Job History" },
];

const DOMAIN_ROLES = [
  { id: "faq_center", label: "SSS Merkezi" },
  { id: "blog_center", label: "Blog Rehberi" },
  { id: "entity_center", label: "Entity Bilgi Merkezi" },
  { id: "geo_support", label: "GEO Destek" },
  { id: "brand_support", label: "Marka Destek" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : e?.message || "Hata";
}

export default function SiteReplicator() {
  const [step, setStep] = useState("clone");
  const [health, setHealth] = useState(null);
  const [projects, setProjects] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [blueprint, setBlueprint] = useState(null);
  const [lastJob, setLastJob] = useState(null);

  const [cloneForm, setCloneForm] = useState({
    source_project_id: "",
    target_domain: "",
    target_site_name: "Balkutusu Rehber",
    content_strategy: "rewrite_all",
    theme_variation: true,
    auto_build: true,
    auto_deploy: false,
  });
  const [variantForm, setVariantForm] = useState({
    base_project_id: "",
    domain_role: "faq_center",
    target_domain: "",
    main_site_url: "",
  });
  const [competitorUrl, setCompetitorUrl] = useState("");
  const [templateForm, setTemplateForm] = useState({
    blueprint_id: "",
    target_domain: "",
    site_name: "",
    auto_build: false,
  });
  const [deployProjectId, setDeployProjectId] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [h, pl, jl] = await Promise.all([
        API.get("/api/site-replicator/health"),
        API.get("/api/astro-factory/projects"),
        API.get("/api/site-replicator/jobs?limit=20"),
      ]);
      setHealth(h.data);
      setProjects(pl.data.projects || []);
      setJobs(jl.data.jobs || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleClone = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/site-replicator/clone-owned-site", cloneForm);
      setLastJob(res.data.job);
      setMessage(`Klon tamam: ${res.data.summary?.target_project_id} · build: ${res.data.summary?.built ? "✓" : "—"}`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleVariant = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/site-replicator/create-domain-variant", variantForm);
      setLastJob(res.data.job);
      setMessage(`Varyant: ${res.data.summary?.target_project_id} (${variantForm.domain_role})`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleBlueprint = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/site-replicator/analyze-competitor-blueprint", { url: competitorUrl });
      setBlueprint(res.data);
      setTemplateForm((f) => ({ ...f, blueprint_id: res.data.blueprint_id }));
      setMessage("Blueprint çıkarıldı — içerik kopyalanmadı");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleTemplate = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/site-replicator/generate-original-template", {
        ...templateForm,
        main_site_url: "",
      });
      setLastJob(res.data.job);
      setDeployProjectId(res.data.summary?.project_id || "");
      setMessage(`Özgün template: ${res.data.summary?.project_id}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleBuild = async () => {
    if (!deployProjectId) return;
    setLoading(true);
    try {
      await API.post("/api/site-replicator/build", { project_id: deployProjectId });
      setMessage("Build tamamlandı");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleDeploy = async () => {
    if (!deployProjectId) return;
    setLoading(true);
    try {
      const res = await API.post("/api/site-replicator/deploy-cloudflare", { project_id: deployProjectId });
      setMessage(`Deploy: ${res.data.url || res.data.deployment_url || "OK"}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="hive-page">
      <div className="hive-hero">
        <h2>🧬 Site Replicator & Blueprint Engine</h2>
        <p>Owned site tam klon · domain varyant · rakip yapı analizi (içerik/asset kopyası yok)</p>
        {health && (
          <p className="hive-hero-meta">
            CF: {health.cloudflare_configured ? "✓" : "—"} · Jobs: {health.job_count}
          </p>
        )}
      </div>

      <div className="hive-warn">
        Rakip sitelerden HTML/CSS/görsel/marka birebir kopyalanmaz. Sadece yapısal blueprint çıkarılır.
        Kendi Astro siteleriniz tam klonlanabilir (rewrite_all ile içerik yeniden yazılır).
      </div>

      {error && <div className="hive-alert-err">{error}</div>}
      {message && <div className="hive-alert-ok">{message}</div>}

      <div className="hive-tabs">
        {STEPS.map((s) => (
          <button key={s.id} type="button" className={`hive-tab ${step === s.id ? "active" : ""}`} onClick={() => setStep(s.id)}>{s.label}</button>
        ))}
      </div>

      {step === "clone" && (
        <div className="hive-card">
          <h3>Owned Site Clone</h3>
          <label>Kaynak proje
            <select value={cloneForm.source_project_id} onChange={(e) => setCloneForm({ ...cloneForm, source_project_id: e.target.value })} className="hive-input">
              <option value="">— seç —</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.site_name} ({p.id})</option>)}
            </select>
          </label>
          <label>Hedef domain<input value={cloneForm.target_domain} onChange={(e) => setCloneForm({ ...cloneForm, target_domain: e.target.value })} className="hive-input" /></label>
          <label>Site adı<input value={cloneForm.target_site_name} onChange={(e) => setCloneForm({ ...cloneForm, target_site_name: e.target.value })} className="hive-input" /></label>
          <label><input type="checkbox" checked={cloneForm.theme_variation} onChange={(e) => setCloneForm({ ...cloneForm, theme_variation: e.target.checked })} /> Tema varyasyonu (CSS accent)</label>
          <label><input type="checkbox" checked={cloneForm.auto_build} onChange={(e) => setCloneForm({ ...cloneForm, auto_build: e.target.checked })} /> Auto Build</label>
          <label><input type="checkbox" checked={cloneForm.auto_deploy} onChange={(e) => setCloneForm({ ...cloneForm, auto_deploy: e.target.checked })} /> Auto Deploy CF</label>
          <button type="button" className="btn-primary" disabled={loading || !cloneForm.source_project_id} onClick={handleClone}>
            {loading ? "Klonlanıyor…" : "Klonla & Yeniden Yaz"}
          </button>
        </div>
      )}

      {step === "variant" && (
        <div className="hive-card">
          <h3>Domain Variant</h3>
          <label>Base proje
            <select value={variantForm.base_project_id} onChange={(e) => setVariantForm({ ...variantForm, base_project_id: e.target.value })} className="hive-input">
              <option value="">— seç —</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.site_name}</option>)}
            </select>
          </label>
          <label>Rol
            <select value={variantForm.domain_role} onChange={(e) => setVariantForm({ ...variantForm, domain_role: e.target.value })} className="hive-input">
              {DOMAIN_ROLES.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
            </select>
          </label>
          <label>Hedef domain<input value={variantForm.target_domain} onChange={(e) => setVariantForm({ ...variantForm, target_domain: e.target.value })} className="hive-input" /></label>
          <button type="button" className="btn-primary" disabled={loading || !variantForm.base_project_id} onClick={handleVariant}>Varyant Oluştur</button>
        </div>
      )}

      {step === "blueprint" && (
        <div className="hive-card">
          <h3>Competitor Blueprint (yapı only)</h3>
          <label>Rakip URL<input value={competitorUrl} onChange={(e) => setCompetitorUrl(e.target.value)} placeholder="https://example.com" className="hive-input" /></label>
          <button type="button" className="btn-primary" disabled={loading || !competitorUrl} onClick={handleBlueprint}>Blueprint Analiz Et</button>
          {blueprint?.blueprint && (
            <pre style={{ marginTop: "1rem", fontSize: "0.75rem", overflow: "auto", maxHeight: 280 }}>
              {JSON.stringify(blueprint.blueprint, null, 2)}
            </pre>
          )}
          {blueprint?.compliance && (
            <p style={{ fontSize: "0.82rem" }}>
              copied_content: {String(blueprint.compliance.copied_content)} · blueprint_only: {String(blueprint.compliance.blueprint_only)}
            </p>
          )}
        </div>
      )}

      {step === "template" && (
        <div className="hive-card">
          <h3>Original Template (blueprint + özgün içerik)</h3>
          <label>Blueprint ID<input value={templateForm.blueprint_id} onChange={(e) => setTemplateForm({ ...templateForm, blueprint_id: e.target.value })} className="hive-input" /></label>
          <label>Hedef domain<input value={templateForm.target_domain} onChange={(e) => setTemplateForm({ ...templateForm, target_domain: e.target.value })} className="hive-input" /></label>
          <label>Site adı<input value={templateForm.site_name} onChange={(e) => setTemplateForm({ ...templateForm, site_name: e.target.value })} className="hive-input" /></label>
          <button type="button" className="btn-primary" disabled={loading || !templateForm.blueprint_id} onClick={handleTemplate}>Özgün Template Üret</button>
        </div>
      )}

      {step === "deploy" && (
        <div className="hive-card">
          <h3>Build & Deploy</h3>
          <label>Project ID<input value={deployProjectId} onChange={(e) => setDeployProjectId(e.target.value)} className="hive-input" /></label>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" disabled={loading || !deployProjectId} onClick={handleBuild}>Build</button>
            <button type="button" className="btn-primary" disabled={loading || !deployProjectId} onClick={handleDeploy}>Cloudflare Deploy</button>
          </div>
        </div>
      )}

      {step === "jobs" && (
        <div className="hive-card">
          <h3>Job History</h3>
          <ul style={{ fontSize: "0.82rem", paddingLeft: "1.2rem" }}>
            {jobs.map((j) => (
              <li key={j.job_id}>
                <strong>{j.type}</strong> · {j.status} · {j.job_id}
                {j.summary?.target_project_id && <> → {j.summary.target_project_id}</>}
              </li>
            ))}
          </ul>
          {lastJob && (
            <pre style={{ fontSize: "0.72rem", marginTop: "1rem", overflow: "auto", maxHeight: 200 }}>
              {JSON.stringify(lastJob.summary, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
