import React, { useCallback, useEffect, useState } from "react";
import API from "../../api";
import {
  HiveShell,
  HiveAlert,
  HivePanel,
  HiveStatGrid,
  HiveBtn,
  HiveStatusBadge,
  HiveTable,
} from "../../components/HiveModuleUI";
import { sectorLabel, deployLabel } from "../../config/projectSectors";
import {
  personalityLabels,
  designDnaLabel,
  colorIdentityLabel,
  conversionGoalLabel,
} from "../../config/brandWizard";
import DesignPreview from "./DesignPreview";
import ProjectCmsEditor from "./ProjectCmsEditor";

function apiError(e) {
  return e?.response?.data?.detail || e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso.replace(" UTC", "Z")).toLocaleString("tr-TR");
  } catch {
    return iso;
  }
}

function liveSiteHref(liveUrl) {
  if (!liveUrl) return "#";
  const base =
    process.env.REACT_APP_API_URL ||
    (process.env.NODE_ENV === "development" ? "http://127.0.0.1:4001" : "");
  if (!base) return liveUrl;
  return `${base.replace(/\/$/, "")}${liveUrl.startsWith("/") ? liveUrl : `/${liveUrl}`}`;
}

function pageHref(slug) {
  return slug ? `/${slug}` : "/";
}

function sectionCount(page) {
  return (page.sections || []).length;
}

function blockCount(page) {
  return (page.sections || []).reduce((n, s) => n + (s.blocks || []).length, 0);
}

function blockContent(blk) {
  return blk?.content || blk?.props || {};
}

function findHeroBlock(page) {
  for (const sec of page.sections || []) {
    for (const blk of sec.blocks || []) {
      if (blk.type === "hero") return blk;
    }
  }
  return null;
}

function PagePreviewModal({ page, onClose }) {
  if (!page) return null;
  const hero = findHeroBlock(page);
  const heroContent = blockContent(hero);
  return (
    <div className="hive-page-preview-backdrop" onClick={onClose} role="presentation">
      <div className="hive-page-preview-modal" onClick={(e) => e.stopPropagation()}>
        <div className="hive-page-preview-header">
          <h3>Page Preview</h3>
          <HiveBtn onClick={onClose}>Kapat</HiveBtn>
        </div>
        <dl className="hive-review-list">
          <dt>Başlık</dt><dd>{page.title}</dd>
          <dt>Slug</dt><dd><code>{pageHref(page.slug)}</code></dd>
          <dt>Tip</dt><dd>{page.type}</dd>
          <dt>Schema</dt><dd>{page.seo?.schema_type || "—"}</dd>
          <dt>Keyword</dt><dd>{page.seo?.target_keyword || "—"}</dd>
        </dl>
        {hero && (
          <div className="hive-page-preview-hero">
            <div className="hive-brand-review-label">Hero</div>
            <p className="hive-page-preview-eyebrow">{heroContent.eyebrow || heroContent.headline || "—"}</p>
            <h4>{heroContent.title || heroContent.headline || "—"}</h4>
            <p>{heroContent.subtitle || heroContent.subheadline || "—"}</p>
            <p>
              <strong>CTA:</strong>{" "}
              {heroContent.primary_cta || heroContent.cta_label || "—"}
              {heroContent.secondary_cta ? ` · ${heroContent.secondary_cta}` : ""}
            </p>
          </div>
        )}
        <div className="hive-brand-review-label" style={{ marginTop: 16 }}>Sections & Blocks</div>
        {(page.sections || []).map((sec) => (
          <div key={sec.id} className="hive-page-preview-section">
            <strong>{sec.type}</strong>
            <ul>
              {(sec.blocks || []).map((blk) => {
                const c = blockContent(blk);
                return (
                  <li key={blk.id}>
                    <code>{blk.type}</code>
                    {" — "}
                    {c.title || c.headline || c.primary_cta || blk.id}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ProjectDetail({ projectId, onNavigate }) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMsg, setActionMsg] = useState("");
  const [busy, setBusy] = useState("");
  const [previewPage, setPreviewPage] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [publishGate, setPublishGate] = useState(null);
  const [buildResult, setBuildResult] = useState(null);
  const [prepResult, setPrepResult] = useState(null);
  const [deployResult, setDeployResult] = useState(null);
  const [domainInput, setDomainInput] = useState("");
  const [includeWww, setIncludeWww] = useState(true);
  const [productionPlan, setProductionPlan] = useState(null);
  const [nginxPreview, setNginxPreview] = useState("");
  const [applyScript, setApplyScript] = useState(null);
  const [showApplyScript, setShowApplyScript] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.get(`/api/v3/projects/${projectId}`);
      setProject(res.data?.project || null);
    } catch (e) {
      setError(apiError(e));
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const runValidateBuild = async () => {
    setBusy("validate");
    setError("");
    setActionMsg("");
    try {
      const res = await API.post(`/api/v3/projects/${projectId}/export/astro/validate`);
      setValidationResult(res.data);
      setActionMsg(res.data?.valid ? "Build validation geçti." : "Build validation hatalar buldu.");
      await load();
    } catch (e) {
      setError(apiError(e));
      setValidationResult(null);
    } finally {
      setBusy("");
    }
  };
  const runCheckPublishGate = async () => {
    setBusy("gate");
    setError("");
    setActionMsg("");
    try {
      const res = await API.get(`/api/v3/projects/${projectId}/publish-gate`);
      setPublishGate(res.data?.astro || null);
      setActionMsg(res.data?.astro?.can_publish ? "Publish gate: Ready to publish." : "Publish gate: Not ready.");
      await load();
    } catch (e) {
      setError(apiError(e));
      setPublishGate(null);
    } finally {
      setBusy("");
    }
  };
  const runPreparePublish = async () => {
    setBusy("prep");
    setError("");
    setActionMsg("");
    try {
      const res = await API.post(`/api/v3/projects/${projectId}/publish/prepare`);
      setPrepResult(res.data);
      setActionMsg(res.data?.status === "ready" ? "Publish artifact hazır." : "Publish prep başarısız.");
      await load();
    } catch (e) {
      setError(apiError(e));
      setPrepResult(null);
    } finally {
      setBusy("");
    }
  };
  const runDeployHiveCloud = async () => {
    setBusy("deploy");
    setError("");
    setActionMsg("");
    try {
      const res = await API.post(`/api/v3/projects/${projectId}/deploy/hive-cloud`);
      setDeployResult(res.data);
      setActionMsg(res.data?.status === "deployed" ? "HIVE Cloud deploy tamamlandı." : "HIVE Cloud deploy başarısız.");
      await load();
    } catch (e) {
      setError(apiError(e));
      setDeployResult(null);
    } finally {
      setBusy("");
    }
  };
  const runBindDomain = async () => {
    setBusy("bind");
    setError("");
    setActionMsg("");
    try {
      const res = await API.post(`/api/v3/projects/${projectId}/domain/bind`, {
        domain: domainInput,
        include_www: includeWww,
      });
      setActionMsg(`Domain bağlandı: ${res.data?.domain}`);
      await load();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setBusy("");
    }
  };
  const runPlanProduction = async () => {
    setBusy("prodplan");
    setError("");
    setActionMsg("");
    try {
      const res = await API.post(`/api/v3/projects/${projectId}/deploy/production/plan`);
      setProductionPlan(res.data);
      setActionMsg(res.data?.status === "planned" ? "Production deploy planı hazır." : "Plan oluşturulamadı.");
      await load();
    } catch (e) {
      setError(apiError(e));
      setProductionPlan(null);
    } finally {
      setBusy("");
    }
  };
  const runNginxPreview = async () => {
    setBusy("nginx");
    setError("");
    setActionMsg("");
    try {
      const res = await API.get(`/api/v3/projects/${projectId}/deploy/production/nginx-preview`);
      setNginxPreview(res.data?.config || "");
      setActionMsg("Nginx config preview hazır.");
    } catch (e) {
      setError(apiError(e));
      setNginxPreview("");
    } finally {
      setBusy("");
    }
  };
  const runGenerateApplyScript = async () => {
    setBusy("applyscript");
    setError("");
    setActionMsg("");
    try {
      const res = await API.post(`/api/v3/projects/${projectId}/deploy/production/apply-script`);
      setApplyScript(res.data);
      setShowApplyScript(true);
      setActionMsg("Apply script hazır — çalıştırmadan önce inceleyin.");
      await load();
    } catch (e) {
      setError(apiError(e));
      setApplyScript(null);
    } finally {
      setBusy("");
    }
  };
  const copyApplyScript = async () => {
    const text = applyScript?.script || "";
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setActionMsg("Script panoya kopyalandı.");
    } catch {
      setError("Script kopyalanamadı.");
    }
  };
  const runAstroBuild = async () => {
    setBusy("build");
    setError("");
    setActionMsg("");
    try {
      const res = await API.post(`/api/v3/projects/${projectId}/export/astro/build`);
      setBuildResult(res.data);
      setActionMsg(res.data?.status === "built" ? "Astro build tamamlandı." : "Astro build başarısız.");
      await load();
    } catch (e) {
      setError(apiError(e));
      setBuildResult(null);
    } finally {
      setBusy("");
    }
  };
  const runAction = async (key, fn) => {
    setBusy(key);
    setError("");
    setActionMsg("");
    try {
      await fn();
      setActionMsg("İşlem tamamlandı.");
      await load();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setBusy("");
    }
  };

  if (loading) {
    return (
      <HiveShell title="Proje" subtitle="Yükleniyor...">
        <HivePanel>Yükleniyor...</HivePanel>
      </HiveShell>
    );
  }

  if (!project) {
    return (
      <HiveShell
        title="Proje bulunamadı"
        actions={<HiveBtn onClick={() => onNavigate("/projects")}>← Projeler</HiveBtn>}
      >
        {error && <HiveAlert type="error">{error}</HiveAlert>}
      </HiveShell>
    );
  }

  const d = project.design || {};
  const theme = project.theme || {};
  const site = project.site || {};
  const pages = project.pages || [];
  const navigation = project.navigation || [];
  const hasSite = Boolean(site.site_id);
  const isV2 = d.wizard_version >= 2;

  const astroExport = project.metadata?.astro_export || {};
  const hasAstroExport = Boolean(astroExport.export_path);
  const astroValidation = project.metadata?.astro_export_validation || {};
  const hasValidation = Boolean(astroValidation.validated_at);
  const storedPublishGate = project.metadata?.astro_publish_gate || {};
  const activePublishGate = publishGate || (storedPublishGate.checked_at ? storedPublishGate : null);
  const canRunBuild = activePublishGate?.can_publish === true;
  const astroBuild = buildResult || project.metadata?.astro_build || {};
  const hasBuildInfo = Boolean(astroBuild.status);
  const canPreparePublish = astroBuild.status === "built";
  const publishArtifact = prepResult || project.metadata?.astro_publish_artifact || {};
  const hasPrepInfo = Boolean(publishArtifact.status);
  const canDeployHiveCloud = publishArtifact.status === "ready";
  const hiveCloudDeploy = deployResult || project.metadata?.hive_cloud_deploy || {};
  const hasDeployInfo = Boolean(hiveCloudDeploy.status);
  const domainBinding = project.metadata?.domain_binding || {};
  const hasDomainBinding = domainBinding.status === "configured" && Boolean(domainBinding.domain);
  const productionDeploy = productionPlan || project.metadata?.hive_production_deploy || {};
  const hasProductionPlan = Boolean(productionDeploy.status);
  const canPlanProduction = hiveCloudDeploy.status === "deployed" && hasDomainBinding;
  const canGenerateApplyScript = productionDeploy.status === "planned";
  const applyScriptMeta = applyScript || project.metadata?.hive_production_apply_script || {};
  const hasApplyScript = applyScriptMeta.status === "script_ready";

  const stats = [
    { label: "SEO Score", value: project.seo_score ?? 0 },
    { label: "GEO Score", value: project.geo_score ?? 0 },
    { label: "Pages", value: project.pages_count ?? pages.length ?? 0 },
    { label: "Content", value: project.content_count ?? 0 },
    { label: "Publishers", value: project.publishers_count ?? 0 },
    { label: "Integrations", value: project.integrations_count ?? 0 },
  ];

  return (
    <HiveShell
      title={project.name}
      subtitle={`${sectorLabel(project.sector)} · ${project.domain || "domain henüz bağlanmadı"}`}
      actions={(
        <>
          <HiveStatusBadge status={project.status} />
          {!hasSite && (
            <HiveBtn disabled={!!busy} onClick={() => runAction("retro", () => API.post(`/api/v3/projects/${projectId}/retro-seed`))}>
              Skeleton Oluştur
            </HiveBtn>
          )}
          <HiveBtn disabled={!!busy} onClick={() => runAction("fill", () => API.post(`/api/v3/projects/${projectId}/fill-blocks`, { use_llm: false }))}>
            Blokları Doldur
          </HiveBtn>
          <HiveBtn
            variant="primary"
            disabled={!!busy || !hasSite}
            onClick={() => runAction("astro", () => API.post(`/api/v3/projects/${projectId}/export/astro`))}
          >
            Generate Astro Site
          </HiveBtn>
          <HiveBtn disabled={!!busy} onClick={() => runAction("export", () => API.post(`/api/v3/projects/${projectId}/export-astro`, { build: false }))}>
            Legacy Export
          </HiveBtn>
          <HiveBtn onClick={() => onNavigate("/projects")}>← Projeler</HiveBtn>
        </>
      )}
    >
      {error && <HiveAlert type="error">{error}</HiveAlert>}
      {actionMsg && <HiveAlert type="ok">{actionMsg}</HiveAlert>}

      <HiveStatGrid stats={stats} />

      {hasSite && (
        <HivePanel title="Site Export" style={{ marginTop: 16 }}>
          <p style={{ margin: "0 0 12px", opacity: 0.85 }}>
            Export dosyaları üretir; Run Build yalnızca publish gate açıkken npm install/build çalıştırır.
          </p>
          <div className="hive-export-actions" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <HiveBtn
              variant="primary"
              disabled={!!busy}
              onClick={() => runAction("astro", () => API.post(`/api/v3/projects/${projectId}/export/astro`))}
            >
              {busy === "astro" ? "Üretiliyor..." : "Generate Astro Site"}
            </HiveBtn>
            <HiveBtn
              disabled={!!busy || !hasAstroExport}
              onClick={runValidateBuild}
            >
              {busy === "validate" ? "Doğrulanıyor..." : "Validate Build"}
            </HiveBtn>
            <HiveBtn
              disabled={!!busy || !hasAstroExport}
              onClick={runCheckPublishGate}
            >
              {busy === "gate" ? "Kontrol ediliyor..." : "Check Publish Gate"}
            </HiveBtn>
            <HiveBtn
              variant="primary"
              disabled={!!busy || !canRunBuild}
              onClick={runAstroBuild}
            >
              {busy === "build" ? "Build çalışıyor..." : "Run Build"}
            </HiveBtn>
            <HiveBtn
              disabled={!!busy || !canPreparePublish}
              onClick={runPreparePublish}
            >
              {busy === "prep" ? "Hazırlanıyor..." : "Prepare Publish"}
            </HiveBtn>
            <HiveBtn
              variant="primary"
              disabled={!!busy || !canDeployHiveCloud}
              onClick={runDeployHiveCloud}
            >
              {busy === "deploy" ? "Deploy ediliyor..." : "Deploy to HIVE Cloud"}
            </HiveBtn>
          </div>
          {hasAstroExport && (
            <dl className="hive-review-list" style={{ marginTop: 16 }}>
              <dt>export_path</dt><dd><code>{astroExport.export_path}</code></dd>
              <dt>files_count</dt><dd>{astroExport.files_count ?? "—"}</dd>
              <dt>entry</dt><dd><code>{astroExport.entry || "—"}</code></dd>
              <dt>generated_at</dt><dd>{formatDate(astroExport.generated_at)}</dd>
            </dl>
          )}
          {(hasValidation || validationResult) && (
            <div className="hive-validation-summary" style={{ marginTop: 16 }}>
              <div className="hive-validation-badges">
                <span className={`hive-val-badge ${(validationResult?.valid ?? astroValidation.valid) ? "ok" : "err"}`}>
                  {(validationResult?.valid ?? astroValidation.valid) ? "VALID" : "INVALID"}
                </span>
                <span className="hive-val-badge warn">
                  errors: {validationResult?.errors_count ?? astroValidation.errors_count ?? 0}
                </span>
                <span className="hive-val-badge info">
                  warnings: {validationResult?.warnings_count ?? astroValidation.warnings_count ?? 0}
                </span>
              </div>
              <p style={{ margin: "8px 0 0", opacity: 0.8, fontSize: 13 }}>
                validated_at: {formatDate(validationResult?.validated_at || astroValidation.validated_at)}
              </p>
            </div>
          )}
          {(validationResult?.checks || []).length > 0 && (
            <HiveTable
              columns={["Check", "OK", "Severity", "Message"]}
              rows={(validationResult.checks || []).map((c) => [
                c.name,
                c.ok ? "✓" : "✗",
                c.severity,
                c.message || "—",
              ])}
              emptyText="Check yok"
            />
          )}
          {activePublishGate && (
            <div className="hive-publish-gate" style={{ marginTop: 16 }}>
              <div className="hive-brand-review-label">Publish Gate</div>
              <div className="hive-validation-badges" style={{ marginTop: 8 }}>
                <span className={`hive-val-badge ${activePublishGate.can_publish ? "ok" : "err"}`}>
                  {activePublishGate.can_publish ? "Ready to publish" : "Not ready"}
                </span>
              </div>
              {(activePublishGate.reasons || []).length > 0 && (
                <ul className="hive-publish-gate-reasons">
                  {activePublishGate.reasons.map((r) => (
                    <li key={r}><code>{r}</code></li>
                  ))}
                </ul>
              )}
              <p style={{ margin: "8px 0 0", opacity: 0.8, fontSize: 13 }}>
                checked_at: {formatDate(activePublishGate.checked_at)}
              </p>
            </div>
          )}
          {hasBuildInfo && (
            <div className="hive-astro-build" style={{ marginTop: 16 }}>
              <div className="hive-brand-review-label">Astro Build</div>
              <div className="hive-validation-badges" style={{ marginTop: 8 }}>
                <span className={`hive-val-badge ${astroBuild.status === "built" ? "ok" : "err"}`}>
                  {astroBuild.status || "—"}
                </span>
              </div>
              <dl className="hive-review-list" style={{ marginTop: 12 }}>
                {astroBuild.dist_path && <><dt>dist_path</dt><dd><code>{astroBuild.dist_path}</code></dd></>}
                {astroBuild.built_at && <><dt>built_at</dt><dd>{formatDate(astroBuild.built_at)}</dd></>}
                {astroBuild.error && <><dt>error</dt><dd><code>{astroBuild.error}</code></dd></>}
              </dl>
              {(astroBuild.commands || []).length > 0 && (
                <HiveTable
                  columns={["Command", "Exit", "Duration (ms)"]}
                  rows={(astroBuild.commands || []).map((c) => [
                    c.cmd,
                    c.exit_code,
                    c.duration_ms,
                  ])}
                  emptyText="Komut yok"
                />
              )}
              {(astroBuild.stderr_tail || buildResult?.stderr_tail) && (
                <pre className="hive-build-log">{astroBuild.stderr_tail || buildResult?.stderr_tail}</pre>
              )}
              {(astroBuild.stdout_tail || buildResult?.stdout_tail) && (
                <pre className="hive-build-log">{astroBuild.stdout_tail || buildResult?.stdout_tail}</pre>
              )}
            </div>
          )}
          {hasPrepInfo && (
            <div className="hive-publish-artifact" style={{ marginTop: 16 }}>
              <div className="hive-brand-review-label">Publish Artifact</div>
              <div className="hive-validation-badges" style={{ marginTop: 8 }}>
                <span className={`hive-val-badge ${publishArtifact.status === "ready" ? "ok" : "err"}`}>
                  {publishArtifact.status || "—"}
                </span>
              </div>
              <dl className="hive-review-list" style={{ marginTop: 12 }}>
                {publishArtifact.artifact_path && <><dt>artifact_path</dt><dd><code>{publishArtifact.artifact_path}</code></dd></>}
                {publishArtifact.files_count != null && <><dt>files_count</dt><dd>{publishArtifact.files_count}</dd></>}
                {publishArtifact.total_size_bytes != null && (
                  <><dt>total_size</dt><dd>{(publishArtifact.total_size_bytes / 1024).toFixed(1)} KB</dd></>
                )}
                {publishArtifact.entry && <><dt>entry</dt><dd><code>{publishArtifact.entry}</code></dd></>}
                {publishArtifact.prepared_at && <><dt>prepared_at</dt><dd>{formatDate(publishArtifact.prepared_at)}</dd></>}
                {publishArtifact.error && <><dt>error</dt><dd><code>{publishArtifact.error}</code></dd></>}
              </dl>
            </div>
          )}
          {hasDeployInfo && (
            <div className="hive-cloud-deploy" style={{ marginTop: 16 }}>
              <div className="hive-brand-review-label">HIVE Cloud Deploy</div>
              <div className="hive-validation-badges" style={{ marginTop: 8 }}>
                <span className={`hive-val-badge ${hiveCloudDeploy.status === "deployed" ? "ok" : "err"}`}>
                  {hiveCloudDeploy.status || "—"}
                </span>
              </div>
              <dl className="hive-review-list" style={{ marginTop: 12 }}>
                {hiveCloudDeploy.live_url && (
                  <>
                    <dt>live_url</dt>
                    <dd>
                      <a href={liveSiteHref(hiveCloudDeploy.live_url)} target="_blank" rel="noopener noreferrer">
                        {hiveCloudDeploy.live_url}
                      </a>
                    </dd>
                  </>
                )}
                {hiveCloudDeploy.deploy_path && <><dt>deploy_path</dt><dd><code>{hiveCloudDeploy.deploy_path}</code></dd></>}
                {hiveCloudDeploy.files_count != null && <><dt>files_count</dt><dd>{hiveCloudDeploy.files_count}</dd></>}
                {hiveCloudDeploy.deployed_at && <><dt>deployed_at</dt><dd>{formatDate(hiveCloudDeploy.deployed_at)}</dd></>}
                {hiveCloudDeploy.error && <><dt>error</dt><dd><code>{hiveCloudDeploy.error}</code></dd></>}
              </dl>
            </div>
          )}
        </HivePanel>
      )}

      {hasSite && (
        <HivePanel title="Production Deploy" style={{ marginTop: 16 }}>
          <p style={{ margin: "0 0 12px", opacity: 0.85 }}>
            Domain binding ve production deploy planı — gerçek nginx/certbot bu sprintte çalıştırılmaz.
          </p>
          {!hasDomainBinding ? (
            <div className="hive-domain-bind-form" style={{ marginBottom: 16 }}>
              <label style={{ display: "block", marginBottom: 8 }}>
                Domain
                <input
                  type="text"
                  value={domainInput}
                  onChange={(e) => setDomainInput(e.target.value)}
                  placeholder="penteraevleri.com"
                  style={{ display: "block", width: "100%", marginTop: 4 }}
                />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <input
                  type="checkbox"
                  checked={includeWww}
                  onChange={(e) => setIncludeWww(e.target.checked)}
                />
                www subdomain dahil
              </label>
              <HiveBtn disabled={!!busy || !domainInput.trim()} onClick={runBindDomain}>
                {busy === "bind" ? "Bağlanıyor..." : "Bind Domain"}
              </HiveBtn>
            </div>
          ) : (
            <dl className="hive-review-list" style={{ marginBottom: 16 }}>
              <dt>domain</dt><dd><code>{domainBinding.domain}</code></dd>
              {domainBinding.www_domain && <><dt>www_domain</dt><dd><code>{domainBinding.www_domain}</code></dd></>}
              <dt>status</dt><dd>{domainBinding.status}</dd>
              <dt>ssl_status</dt><dd>{domainBinding.ssl_status || "—"}</dd>
              {domainBinding.created_at && <><dt>created_at</dt><dd>{formatDate(domainBinding.created_at)}</dd></>}
            </dl>
          )}
          <div className="hive-export-actions" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <HiveBtn
              variant="primary"
              disabled={!!busy || !canPlanProduction}
              onClick={runPlanProduction}
            >
              {busy === "prodplan" ? "Planlanıyor..." : "Plan Production Deploy"}
            </HiveBtn>
            <HiveBtn
              disabled={!!busy || !hasDomainBinding}
              onClick={runNginxPreview}
            >
              {busy === "nginx" ? "Yükleniyor..." : "Show Nginx Preview"}
            </HiveBtn>
            <HiveBtn
              variant="primary"
              disabled={!!busy || !canGenerateApplyScript}
              onClick={runGenerateApplyScript}
            >
              {busy === "applyscript" ? "Üretiliyor..." : "Generate Apply Script"}
            </HiveBtn>
          </div>
          <p style={{ margin: "12px 0 0", opacity: 0.75, fontSize: 13 }}>
            Bu script root yetkisi ister. Çalıştırmadan önce nginx config ve pathleri kontrol edin.
          </p>
          {hasProductionPlan && (
            <dl className="hive-review-list" style={{ marginTop: 16 }}>
              <dt>status</dt><dd>{productionDeploy.status}</dd>
              {productionDeploy.production_path && <><dt>production_path</dt><dd><code>{productionDeploy.production_path}</code></dd></>}
              {productionDeploy.source_path && <><dt>source_path</dt><dd><code>{productionDeploy.source_path}</code></dd></>}
              {productionDeploy.nginx_config_path && <><dt>nginx_config_path</dt><dd><code>{productionDeploy.nginx_config_path}</code></dd></>}
              {productionDeploy.live_url && (
                <>
                  <dt>live_url</dt>
                  <dd>
                    <a href={productionDeploy.live_url} target="_blank" rel="noopener noreferrer">
                      {productionDeploy.live_url}
                    </a>
                  </dd>
                </>
              )}
              {productionDeploy.planned_at && <><dt>planned_at</dt><dd>{formatDate(productionDeploy.planned_at)}</dd></>}
            </dl>
          )}
          {nginxPreview && (
            <pre className="hive-build-log" style={{ marginTop: 16, maxHeight: 360, overflow: "auto" }}>
              {nginxPreview}
            </pre>
          )}
          {hasApplyScript && (
            <div className="hive-apply-script" style={{ marginTop: 16 }}>
              <div className="hive-brand-review-label">Apply Script</div>
              <div className="hive-validation-badges" style={{ marginTop: 8 }}>
                <span className="hive-val-badge ok">{applyScriptMeta.status}</span>
                {applyScriptMeta.requires_root && (
                  <span className="hive-val-badge warn">requires root</span>
                )}
              </div>
              {applyScript?.manual_steps?.length > 0 && (
                <ol style={{ margin: "12px 0", paddingLeft: 20, fontSize: 14 }}>
                  {applyScript.manual_steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              )}
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <HiveBtn onClick={copyApplyScript} disabled={!applyScript?.script}>
                  Copy Script
                </HiveBtn>
                <HiveBtn onClick={() => setShowApplyScript((v) => !v)}>
                  {showApplyScript ? "Hide Script" : "Show Script"}
                </HiveBtn>
              </div>
              {showApplyScript && applyScript?.script && (
                <pre className="hive-build-log" style={{ marginTop: 12, maxHeight: 420, overflow: "auto" }}>
                  {applyScript.script}
                </pre>
              )}
            </div>
          )}
        </HivePanel>
      )}

      {project.metadata?.astro_path && (
        <HivePanel title="Legacy Astro Export" style={{ marginTop: 16 }}>
          <code>{project.metadata.astro_path}</code>
          {site.export_path && <p style={{ margin: "8px 0 0", opacity: 0.8 }}>Export: {site.export_path}</p>}
        </HivePanel>
      )}

      <div style={{ marginTop: 16 }}>
        <ProjectCmsEditor projectId={projectId} project={project} onUpdated={load} />
      </div>

      {hasSite && (
        <HivePanel title="Site Skeleton" style={{ marginTop: 16 }}>
          <dl className="hive-review-list hive-site-meta">
            <dt>Site ID</dt><dd><code>{site.site_id}</code></dd>
            <dt>Engine</dt><dd>{site.engine || "—"}</dd>
            <dt>Status</dt><dd>{site.status || "—"}</dd>
            <dt>Language</dt><dd>{site.language || "—"}</dd>
            <dt>Pages</dt><dd>{site.pages_count ?? pages.length}</dd>
          </dl>
        </HivePanel>
      )}

      {hasSite && pages.length > 0 && (
        <HivePanel title="Pages" style={{ marginTop: 16 }}>
          <p style={{ margin: "0 0 12px", opacity: 0.8, fontSize: 14 }}>
            Satıra tıklayarak sayfa önizlemesini açın.
          </p>
          <HiveTable
            columns={["Başlık", "Tip", "Sections", "Blocks", "Keyword", "Schema", "Slug"]}
            rows={pages.map((p) => [
              p.title,
              p.type,
              sectionCount(p),
              blockCount(p),
              p.seo?.target_keyword || "—",
              p.seo?.schema_type || "—",
              pageHref(p.slug),
            ])}
            onRowClick={(rowIdx) => setPreviewPage(pages[rowIdx])}
          />
        </HivePanel>
      )}

      {previewPage && (
        <PagePreviewModal page={previewPage} onClose={() => setPreviewPage(null)} />
      )}

      {hasSite && Object.keys(theme).length > 0 && (
        <HivePanel title="Theme DNA" style={{ marginTop: 16 }}>
          <div className="hive-form-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <dl className="hive-review-list">
              <dt>Design DNA</dt><dd>{designDnaLabel(theme.design_dna) || theme.design_dna || "—"}</dd>
              <dt>Color Identity</dt><dd>{colorIdentityLabel(theme.color_identity) || theme.color_identity || "—"}</dd>
              <dt>Conversion Goal</dt><dd>{conversionGoalLabel(theme.conversion_goal) || theme.conversion_goal || "—"}</dd>
              <dt>Font</dt><dd>{theme.font_style || "—"}</dd>
              <dt>Radius</dt><dd>{theme.radius || "—"}</dd>
              <dt>Spacing</dt><dd>{theme.spacing || "—"}</dd>
            </dl>
            {isV2 && (
              <div className="hive-brand-detail-preview">
                <DesignPreview
                  designDna={theme.design_dna || d.design_dna}
                  colorIdentity={theme.color_identity || d.color_identity}
                  customColor={theme.custom_color || d.custom_color}
                />
              </div>
            )}
          </div>
        </HivePanel>
      )}

      {hasSite && navigation.length > 0 && (
        <HivePanel title="Navigation Preview" style={{ marginTop: 16 }}>
          <nav className="hive-site-nav-preview">
            {navigation.map((item) => (
              <span key={item.href} className="hive-site-nav-item">
                {item.label}
                <code>{item.href}</code>
              </span>
            ))}
          </nav>
        </HivePanel>
      )}

      <div className="hive-form-grid" style={{ marginTop: 16, gridTemplateColumns: "1fr 1fr" }}>
        <HivePanel title="Marka DNA">
          {isV2 ? (
            <dl className="hive-review-list">
              <dt>Kişilik</dt><dd>{personalityLabels(d.brand_personality).join(" · ") || "—"}</dd>
              <dt>Design DNA</dt><dd>{designDnaLabel(d.design_dna)}</dd>
              <dt>Renk kimliği</dt><dd>{colorIdentityLabel(d.color_identity)}</dd>
              <dt>Dönüşüm hedefi</dt><dd>{conversionGoalLabel(d.conversion_goal)}</dd>
              <dt>Deploy</dt><dd>{deployLabel(project.deploy_mode)}</dd>
            </dl>
          ) : (
            <dl className="hive-review-list">
              <dt>Layout</dt><dd>{d.layout || "—"}</dd>
              <dt>Renk tonu</dt><dd>{d.color_mood || "—"}</dd>
              <dt>Tipografi</dt><dd>{d.typography || "—"}</dd>
            </dl>
          )}
        </HivePanel>
        <HivePanel title="Business DNA">
          <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{project.business_brief || "—"}</p>
          {isV2 && d.creative_director_brief && (
            <>
              <div className="hive-brand-review-label" style={{ marginTop: 16 }}>AI Creative Director</div>
              <p style={{ margin: "6px 0 0", whiteSpace: "pre-wrap", opacity: 0.9 }}>{d.creative_director_brief}</p>
            </>
          )}
        </HivePanel>
      </div>

      <HivePanel title="Meta" style={{ marginTop: 16 }}>
        <dl className="hive-review-list">
          <dt>ID</dt><dd><code>{project.id}</code></dd>
          <dt>Sektör</dt><dd>{sectorLabel(project.sector)}</dd>
          <dt>Oluşturulma</dt><dd>{formatDate(project.created_at)}</dd>
          <dt>Güncelleme</dt><dd>{formatDate(project.updated_at)}</dd>
        </dl>
      </HivePanel>
    </HiveShell>
  );
}
