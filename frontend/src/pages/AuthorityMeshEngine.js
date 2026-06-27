import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";

import {
  HiveAlert,
  HiveBtn,
  HiveCard,
  HiveCheck,
  HiveCode,
  HiveConceptTooltip,
  HiveField,
  HiveInput,
  HiveIntegrationList,
  HiveLabelWithTip,
  HiveMissionBoard,
  HivePanel,
  HiveSection,
  HiveShell,
  HiveSkeleton,
  HiveStatGrid,
  HiveStatusBadge,
  HiveTable,
  HiveTabs,
  HiveTaskTimeline,
  HiveToast,
  HiveWorkerHealthCard,
} from "../components/HiveModuleUI";
import { HivePanelHero, AuthorityMeshInteractiveGraph } from "../components/HiveOSVisualizations";

const API_PREFIX = "/api/authority-mesh";
const GH_PREFIX = "/api/github-pages";
const GS_PREFIX = "/api/google-sites";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "sites", label: "Authority Sites" },
  { id: "mesh_plans", label: "Mesh Plans" },
  { id: "google_sites", label: "Google Sites" },
  { id: "github_pages", label: "GitHub Pages" },
  { id: "publisher", label: "Publisher Sources" },
  { id: "link_policy", label: "Link Policy" },
  { id: "tasks", label: "Tasks" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const REPORT_TYPES = [
  { id: "overview", label: "Overview" },
  { id: "sites", label: "Authority Sites" },
  { id: "plans", label: "Mesh Plans" },
  { id: "tasks", label: "Tasks" },
  { id: "link_policy", label: "Link Policies" },
];

function apiError(e) {
  return e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

function taskTimelineSteps(status) {
  const order = ["queued", "processing", "login_required", "review_required", "published", "failed"];
  const idx = order.indexOf(status);
  return [
    { id: "q", label: "Queued", state: idx >= 0 ? "done" : "pending" },
    { id: "p", label: "Process", state: status === "processing" ? "active" : idx > 0 ? "done" : "pending" },
    { id: "l", label: "Login", state: status === "login_required" ? "active" : "pending" },
    { id: "pub", label: "Published", state: status === "published" ? "done" : status === "failed" ? "error" : "pending" },
  ];
}

export default function AuthorityMeshEngine({ onNavigate }) {
  const [tab, setTab] = useState(() => {
    const saved = sessionStorage.getItem("hive_mesh_tab");
    return saved && TABS.some((t) => t.id === saved) ? saved : "dashboard";
  });

  useEffect(() => {
    const saved = sessionStorage.getItem("hive_mesh_tab");
    if (saved && TABS.some((t) => t.id === saved)) {
      setTab(saved);
    }
  }, []);

  useEffect(() => {
    sessionStorage.setItem("hive_mesh_tab", tab);
    window.dispatchEvent(new Event("hive-mesh-tab"));
  }, [tab]);
  const [health, setHealth] = useState(null);
  const [settings, setSettings] = useState(null);
  const [dash, setDash] = useState(null);
  const [sites, setSites] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [reports, setReports] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");

  const [keyword, setKeyword] = useState("");
  const [moneySite, setMoneySite] = useProjectSiteField();
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [lastPlan, setLastPlan] = useState(null);

  const [gsAccount, setGsAccount] = useState("default");
  const [gsTitle, setGsTitle] = useState("");
  const [gsSlug, setGsSlug] = useState("");
  const [gsKeyword, setGsKeyword] = useState("");
  const [gsMoney, setGsMoney] = useProjectSiteField();
  const [gsPagesJson, setGsPagesJson] = useState("[]");
  const [gsHealth, setGsHealth] = useState(null);
  const [gsTasks, setGsTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [lastTask, setLastTask] = useState(null);

  const [ghHealth, setGhHealth] = useState(null);
  const [ghSites, setGhSites] = useState([]);
  const [ghRepoName, setGhRepoName] = useState("");
  const [ghTitle, setGhTitle] = useState("");
  const [ghKeyword, setGhKeyword] = useState("");
  const [ghMoney, setGhMoney] = useProjectSiteField();
  const [ghRole, setGhRole] = useState("geo_hub");
  const [ghPagesJson, setGhPagesJson] = useState("[]");
  const [ghSelectedSiteId, setGhSelectedSiteId] = useState("");
  const [ghLastSite, setGhLastSite] = useState(null);

  const [settingsDraft, setSettingsDraft] = useState({});

  const refresh = useCallback(async () => {
    try {
      const [h, s, d, si, t, r, gh, ghs, gsh, gst] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/sites`).catch(() => ({ data: { sites: [] } })),
        API.get(`${API_PREFIX}/tasks?limit=50`).catch(() => ({ data: { tasks: [] } })),
        API.get(`${API_PREFIX}/reports`).catch(() => ({ data: null })),
        API.get(`${GH_PREFIX}/health`).catch(() => ({ data: null })),
        API.get(`${GH_PREFIX}/sites`).catch(() => ({ data: { sites: [] } })),
        API.get(`${GS_PREFIX}/health`).catch(() => ({ data: null })),
        API.get(`${GS_PREFIX}/tasks?limit=50`).catch(() => ({ data: { tasks: [] } })),
      ]);
      setHealth(h.data);
      const st = s.data.settings || s.data;
      setSettings(st);
      setSettingsDraft(st);
      setDash(d.data);
      setSites(si.data.sites || []);
      setTasks(t.data.tasks || []);
      setReports(r.data);
      setGhHealth(gh.data);
      setGhSites(ghs.data.sites || []);
      setGsHealth(gsh.data);
      setGsTasks(gst.data.tasks || []);
    } catch (err) {
      setError(apiError(err));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const createMeshPlan = async () => {
    if (!keyword.trim()) { setError("Keyword gerekli"); return; }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post(`${API_PREFIX}/create-site-plan`, {
        keyword: keyword.trim(),
        money_site: moneySite.trim(),
      });
      setLastPlan(res.data.plan);
      setSelectedPlanId(res.data.plan?.plan_id || "");
      setMessage(`Mesh plan oluşturuldu: ${res.data.plan?.items?.length || 0} item`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const createPublisherPlan = async () => {
    if (!selectedPlanId && !keyword.trim()) { setError("Plan ID veya keyword gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/create-publisher-plan`, {
        plan_id: selectedPlanId,
        keyword: keyword.trim(),
        money_site: moneySite.trim(),
      });
      setMessage(`Publisher plan: ${res.data.publisher_plan?.publisher_plan_id}`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const processPlan = async () => {
    if (!selectedPlanId) { setError("Plan ID seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/process-plan`, { plan_id: selectedPlanId, auto_publish: true });
      setMessage(`Plan işlendi: ${res.data.success_count} başarılı, ${res.data.fail_count} hata`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const createGoogleSiteTask = async () => {
    if (!gsTitle.trim() && !gsKeyword.trim()) { setError("Site title veya keyword gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      let pages = [];
      if (gsPagesJson.trim() && gsPagesJson.trim() !== "[]") {
        pages = JSON.parse(gsPagesJson);
      }
      const res = await API.post(`${GS_PREFIX}/create-task`, {
        site_title: gsTitle.trim(),
        site_slug: gsSlug.trim(),
        target_keyword: gsKeyword.trim(),
        target_money_site: gsMoney.trim(),
        account_profile: gsAccount.trim() || "default",
        pages: pages.length ? pages : undefined,
      });
      setLastTask(res.data.task);
      setSelectedTaskId(res.data.task?.task_id || "");
      setMessage(`Google Sites task oluşturuldu: ${res.data.task?.task_id}`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const processGoogleSiteTask = async (taskId) => {
    const tid = taskId || selectedTaskId;
    if (!tid) { setError("Task ID gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${GS_PREFIX}/process-task`, { task_id: tid });
      setLastTask(res.data.task);
      const st = res.data.task?.status;
      if (st === "login_required") {
        setMessage("Login gerekli — tarayıcıda Google hesabına giriş yapın, ardından Resume Task kullanın.");
      } else if (st === "published") {
        setMessage(`Yayınlandı: ${res.data.task?.published_url}`);
      } else if (st === "failed" && res.data.worker?.error === "provider_missing") {
        setMessage("Browser worker yapılandırılmadı (provider_missing)");
      } else {
        setMessage(`Task durumu: ${st}`);
      }
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const resumeGoogleSiteTask = async (taskId) => {
    const tid = taskId || selectedTaskId;
    if (!tid) { setError("Task ID gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${GS_PREFIX}/resume-task`, { task_id: tid });
      setLastTask(res.data.task);
      const st = res.data.task?.status;
      if (st === "published") {
        setMessage(`Yayınlandı: ${res.data.task?.published_url}`);
      } else if (st === "login_required") {
        setMessage("Hâlâ login gerekli — tarayıcı profilinde oturum açın.");
      } else {
        setMessage(`Resume sonucu: ${st}`);
      }
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const gsPagesPreview = (() => {
    if (!lastTask?.pages?.length) return null;
    try {
      return JSON.stringify(lastTask.pages, null, 2);
    } catch {
      return null;
    }
  })();

  const createGitHubSite = async () => {
    if (!ghRepoName.trim() && !ghTitle.trim() && !ghKeyword.trim()) {
      setError("repo name, site title veya keyword gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      let pages = [];
      if (ghPagesJson.trim() && ghPagesJson.trim() !== "[]") {
        pages = JSON.parse(ghPagesJson);
      }
      const res = await API.post(`${GH_PREFIX}/create-site`, {
        repo_name: ghRepoName.trim(),
        site_title: ghTitle.trim(),
        target_keyword: ghKeyword.trim(),
        target_money_site: ghMoney.trim(),
        role: ghRole,
        pages,
      });
      setGhLastSite(res.data.site);
      setGhSelectedSiteId(res.data.site?.site_id || "");
      setMessage(`GitHub Pages site: ${res.data.site?.status} — ${res.data.site?.pages_url || res.data.site?.repo_url || ""}`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const publishGitHubSite = async (siteId) => {
    const sid = siteId || ghSelectedSiteId;
    if (!sid) { setError("Site ID gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${GH_PREFIX}/publish-site`, { site_id: sid });
      setGhLastSite(res.data.site);
      setMessage(res.data.site?.pages_url ? `Published: ${res.data.site.pages_url}` : `Status: ${res.data.site?.status}`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/settings`, settingsDraft);
      setSettings(res.data.settings);
      setMessage("Ayarlar kaydedildi");
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (reportType) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, { report_type: reportType });
      setExportPath(res.data.path || "");
      setMessage(`Rapor dışa aktarıldı: ${reportType}`);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const meshPlans = dash?.recent_mesh_plans || [];
  const browserWorker = dash?.browser_worker || health?.browser_worker || {};
  const providers = health?.providers || {};
  const integrations = dash?.integrations || health?.integrations || {};

  return (
    <div className="hive-module hive-os-command-center">
      <HivePanelHero
        kicker="Authority OS"
        title="Authority Mesh Engine"
        subtitle="Otorite ağı orkestrasyonu — platformlar tek mesh altında"
      />
    <HiveShell title="" subtitle="">
      {error && <HiveAlert type="error">{error}</HiveAlert>}
      <HiveToast message={message} onClose={() => setMessage("")} />

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />
      {loading && !dash && <HiveSkeleton lines={6} />}

      {tab === "dashboard" && (
        <>
          <div className="hive-viz-grid hive-ops-primary">
            <AuthorityMeshInteractiveGraph
              sites={sites}
              moneySite={moneySite || settings?.money_site || "Money Site"}
              publisherCount={dash?.published_count ?? 0}
              traffic={dash?.traffic_estimate ?? (dash?.published_count || 0) * 150}
              sources={meshPlans.map((p) => ({ label: p.name || p.plan_id || "Plan", source: p.provider }))}
              onNavigate={onNavigate}
            />
          </div>
          <div className="hive-ops-pills">
            <span className="hive-pill hive-pill-success hive-pill-sm">{dash?.published_count ?? 0} published</span>
            <span className="hive-pill hive-pill-accent hive-pill-sm">{dash?.authority_sites_count ?? 0} authority</span>
            <span className="hive-pill hive-pill-warning hive-pill-sm">{dash?.queued_tasks ?? 0} queued</span>
            <span className="hive-pill hive-pill-neutral hive-pill-sm">{dash?.mesh_plans_count ?? 0} plans</span>
          </div>
        </>
      )}

      {tab === "sites" && (
        <HivePanel title="Authority Sites">
          <HiveTable
            columns={["Provider", "Role", "Status", "Score", "URL", "Keyword"]}
            rows={sites.map((s) => [
              s.provider,
              s.role,
              <HiveStatusBadge status={s.status} />,
              s.authority_score ?? "—",
              (s.domain_or_url || s.published_urls?.[0] || "—").slice(0, 48),
              (s.target_keyword_cluster || "—").slice(0, 32),
            ])}
          />
        </HivePanel>
      )}

      {tab === "mesh_plans" && (
        <HivePanel title="Mesh Plans">
          <HiveField label="Keyword">
            <HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="kuşadası gece hayatı" />
          </HiveField>
          <HiveField label="Money Site URL">
            <HiveInput value={moneySite} onChange={(e) => setMoneySite(e.target.value)} />
          </HiveField>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <HiveBtn onClick={createMeshPlan} disabled={loading}>Mesh Plan Oluştur</HiveBtn>
            <HiveBtn onClick={createPublisherPlan} disabled={loading} variant="secondary">Publisher Plan</HiveBtn>
            <HiveBtn onClick={processPlan} disabled={loading || !selectedPlanId} variant="secondary">Planı İşle</HiveBtn>
          </div>
          <HiveField label="Seçili Plan ID">
            <HiveInput value={selectedPlanId} onChange={(e) => setSelectedPlanId(e.target.value)} placeholder="ame-plan-..." />
          </HiveField>
          {lastPlan && (
            <HiveCard title="Son Plan">
              <HiveCode>{JSON.stringify(lastPlan, null, 2)}</HiveCode>
            </HiveCard>
          )}
          <HiveTable
            columns={["Plan ID", "Keyword", "Items", "Created"]}
            rows={meshPlans.map((p) => [
              p.plan_id,
              p.keyword,
              p.items?.length ?? 0,
              p.created_at || "—",
            ])}
          />
        </HivePanel>
      )}

      {tab === "google_sites" && (
        <HivePanel title="Google Sites — Browser Automation Worker">
          <HiveWorkerHealthCard
            title="Google Sites Provider"
            providerReady={gsHealth?.ready ?? gsHealth?.provider_ready}
            provider={gsHealth?.provider}
            error={gsHealth?.ready || gsHealth?.provider_ready ? null : (gsHealth?.reason || gsHealth?.error || "provider_missing")}
            stats={[
              ["Browser Ready", gsHealth?.ready || gsHealth?.provider_ready ? "✓" : "—"],
              ["Playwright", gsHealth?.playwright_installed || gsHealth?.playwright_available ? "✓" : "—"],
              ["Chromium", gsHealth?.chromium_installed ? "✓" : "—"],
              ["Headless", gsHealth?.headless ? "on" : "off"],
              ["Published", gsHealth?.published_count ?? 0],
              ["Login Required", gsHealth?.login_required_count ?? 0],
              ["Failed", gsHealth?.failed_count ?? 0],
            ]}
          />
          {gsHealth?.browser_profile_dir && (
            <HiveAlert type="info">
              Browser profile: <code>{gsHealth.browser_profile_dir}</code>
              {!gsHealth?.chromium_installed && " — Chromium eksik: backend venv içinde `python -m playwright install chromium`"}
            </HiveAlert>
          )}
          <HiveAlert type="info">
            Gerçek tarayıcı otomasyonu. Login/captcha durumunda tarayıcı profilinde giriş yapın, ardından Resume Task.
          </HiveAlert>
          <HiveField label="Account Profile">
            <HiveInput value={gsAccount} onChange={(e) => setGsAccount(e.target.value)} placeholder="default" />
          </HiveField>
          <HiveField label="Site Title">
            <HiveInput value={gsTitle} onChange={(e) => setGsTitle(e.target.value)} placeholder="Kuşadası Gece Hayatı Rehberi" />
          </HiveField>
          <HiveField label="Site Slug">
            <HiveInput value={gsSlug} onChange={(e) => setGsSlug(e.target.value)} placeholder="kusadasi-gece-hayati-rehberi" />
          </HiveField>
          <HiveField label="Target Keyword">
            <HiveInput value={gsKeyword} onChange={(e) => setGsKeyword(e.target.value)} />
          </HiveField>
          <HiveField label="Money Site URL">
            <HiveInput value={gsMoney} onChange={(e) => setGsMoney(e.target.value)} />
          </HiveField>
          <HiveField label="Pages JSON (opsiyonel)">
            <HiveInput value={gsPagesJson} onChange={(e) => setGsPagesJson(e.target.value)} placeholder='[{"title":"...","slug":"...","content_html":"..."}]' />
          </HiveField>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <HiveBtn onClick={createGoogleSiteTask} disabled={loading}>Create Task</HiveBtn>
            <HiveBtn onClick={() => processGoogleSiteTask()} disabled={loading || !selectedTaskId} variant="secondary">Process Task</HiveBtn>
            <HiveBtn onClick={() => resumeGoogleSiteTask()} disabled={loading || !selectedTaskId} variant="secondary">Resume Task</HiveBtn>
          </div>
          {lastTask && (
            <HiveCard title="Son Task">
              <p><strong>Task ID:</strong> {lastTask.task_id}</p>
              <p><strong>Status:</strong> <HiveStatusBadge status={lastTask.status} /></p>
              <HiveTaskTimeline steps={taskTimelineSteps(lastTask.status)} />
              {lastTask.status === "login_required" && (
                <HiveAlert type="warning" pulse>
                  Google hesabına giriş yapın (headless=false, profil dizininde), ardından Resume Task çalıştırın.
                  {lastTask.error && <> Hata kodu: <code>{lastTask.error}</code></>}
                </HiveAlert>
              )}
              {(lastTask.status === "browser_missing" || lastTask.status === "provider_missing") && (
                <HiveAlert type="error">
                  {lastTask.status === "browser_missing"
                    ? "Chromium kurulu değil — backend venv: python -m playwright install chromium"
                    : "Provider eksik — OPENCLAW_BROWSER_WORKER_URL veya Playwright yapılandırın"}
                </HiveAlert>
              )}
              {lastTask.published_url && (
                <div className="hm-published-url">
                  <strong>Published URL</strong>
                  <a href={lastTask.published_url} target="_blank" rel="noopener noreferrer">{lastTask.published_url}</a>
                </div>
              )}
              {lastTask.error && <p><strong>Error:</strong> {lastTask.error}</p>}
              {gsPagesPreview && (
                <HiveField label="Pages Preview">
                  <HiveCode>{gsPagesPreview}</HiveCode>
                </HiveField>
              )}
            </HiveCard>
          )}
          <HiveTable
            columns={["Task ID", "Title", "Status", "Published URL", "Actions"]}
            density="comfortable"
            rows={(gsTasks.length ? gsTasks : tasks.filter((t) => t.provider === "google_sites")).map((t) => [
              t.task_id,
              (t.site_title || "—").slice(0, 36),
              <HiveStatusBadge status={t.status} />,
              (t.published_url || "—").slice(0, 40),
              t.status === "queued" || t.status === "login_required" ? (
                <span key={t.task_id} style={{ display: "flex", gap: 4 }}>
                  <HiveBtn size="sm" onClick={() => { setSelectedTaskId(t.task_id); processGoogleSiteTask(t.task_id); }} disabled={loading}>
                    Process
                  </HiveBtn>
                  {t.status === "login_required" && (
                    <HiveBtn size="sm" onClick={() => { setSelectedTaskId(t.task_id); resumeGoogleSiteTask(t.task_id); }} disabled={loading}>
                      Resume
                    </HiveBtn>
                  )}
                </span>
              ) : "—",
            ])}
          />
          <HiveSection title="Login Required Tasks">
            <HiveTable
              columns={["Task ID", "Title", "Error", "Actions"]}
              rows={(gsTasks || []).filter((t) => t.status === "login_required").map((t) => ({
                task_id: t.task_id,
                title: (t.site_title || "—").slice(0, 40),
                error: t.error || "google_login_required",
                actions: (
                  <HiveBtn size="sm" onClick={() => { setSelectedTaskId(t.task_id); resumeGoogleSiteTask(t.task_id); }} disabled={loading}>
                    Resume
                  </HiveBtn>
                ),
              }))}
              emptyText="Login bekleyen task yok"
            />
          </HiveSection>
          <HiveSection title="Published Sites">
            <HiveTable
              columns={["Task ID", "Title", "Published URL"]}
              rows={(gsTasks || []).filter((t) => t.status === "published").map((t) => ({
                task_id: t.task_id,
                title: (t.site_title || "—").slice(0, 40),
                published_url: t.published_url ? <a href={t.published_url} target="_blank" rel="noopener noreferrer">{t.published_url}</a> : "—",
              }))}
              emptyText="Henüz published site yok"
            />
          </HiveSection>
          <HiveSection title="Failed Tasks">
            <HiveTable
              columns={["Task ID", "Title", "Error"]}
              rows={(gsTasks || []).filter((t) => t.status === "failed").map((t) => ({
                task_id: t.task_id,
                title: (t.site_title || "—").slice(0, 40),
                error: t.error || "—",
              }))}
              emptyText="Failed task yok"
            />
          </HiveSection>
        </HivePanel>
      )}

      {tab === "github_pages" && (
        <HivePanel title="GitHub Pages — REST API Worker">
          <HiveWorkerHealthCard
            title="GitHub Pages Provider"
            providerReady={ghHealth?.provider_ready}
            provider="github_rest_api"
            error={ghHealth?.provider_ready ? null : (ghHealth?.error || "provider_missing — GITHUB_TOKEN")}
            stats={[
              ["Sites", ghHealth?.sites_count ?? 0],
              ["Published", ghHealth?.published_count ?? 0],
              ["Branch", ghHealth?.pages_branch || "main"],
            ]}
          />
          <HiveAlert type="info">
            Gerçek GitHub REST API — repo, static HTML, Pages etkinleştirme.
          </HiveAlert>
          <HiveField label="Repo Name">
            <HiveInput value={ghRepoName} onChange={(e) => setGhRepoName(e.target.value)} placeholder="kusadasi-gece-hayati-rehberi" />
          </HiveField>
          <HiveField label="Site Title">
            <HiveInput value={ghTitle} onChange={(e) => setGhTitle(e.target.value)} placeholder="Kuşadası Gece Hayatı Rehberi" />
          </HiveField>
          <HiveField label="Target Keyword">
            <HiveInput value={ghKeyword} onChange={(e) => setGhKeyword(e.target.value)} />
          </HiveField>
          <HiveField label="Money Site URL">
            <HiveInput value={ghMoney} onChange={(e) => setGhMoney(e.target.value)} />
          </HiveField>
          <HiveField label="Role">
            <HiveInput value={ghRole} onChange={(e) => setGhRole(e.target.value)} placeholder="geo_hub" />
          </HiveField>
          <HiveField label="Pages JSON (opsiyonel)">
            <HiveInput value={ghPagesJson} onChange={(e) => setGhPagesJson(e.target.value)} placeholder='[{"title":"...","slug":"...","content_html":"..."}]' />
          </HiveField>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <HiveBtn onClick={createGitHubSite} disabled={loading}>Create Site</HiveBtn>
            <HiveBtn onClick={() => publishGitHubSite()} disabled={loading || !ghSelectedSiteId} variant="secondary">Publish Site</HiveBtn>
          </div>
          {ghLastSite && (
            <HiveCard title="Son Site">
              <p><strong>Site ID:</strong> {ghLastSite.site_id}</p>
              <p><strong>Status:</strong> <HiveStatusBadge status={ghLastSite.status} /></p>
              {ghLastSite.repo_url && <p><strong>Repo:</strong> {ghLastSite.repo_url}</p>}
              {ghLastSite.pages_url && (
                <div className="hm-published-url">
                  <strong>Pages URL</strong>
                  <a href={ghLastSite.pages_url} target="_blank" rel="noopener noreferrer">{ghLastSite.pages_url}</a>
                </div>
              )}
              {ghLastSite.error && <p><strong>Error:</strong> {ghLastSite.error}</p>}
            </HiveCard>
          )}
          <HiveTable
            columns={["Site ID", "Repo", "Status", "Pages URL", "Keyword", "Action"]}
            rows={ghSites.map((s) => [
              s.site_id,
              s.repo_name,
              <HiveStatusBadge status={s.status} />,
              (s.pages_url || "—").slice(0, 40),
              (s.target_keyword || "—").slice(0, 24),
              s.status !== "published" ? (
                <HiveBtn key={s.site_id} size="sm" onClick={() => { setGhSelectedSiteId(s.site_id); publishGitHubSite(s.site_id); }} disabled={loading}>
                  Publish
                </HiveBtn>
              ) : "✅",
            ])}
          />
        </HivePanel>
      )}

      {tab === "publisher" && (
        <HivePanel title="Publisher Sources">
          <HiveTable
            columns={["Provider", "Type", "Publisher Channel"]}
            rows={Object.entries(providers).map(([id, ptype]) => [
              id,
              ptype,
              ptype === "api" ? "Publisher Hub" : ptype === "browser" ? "Browser Worker" : "Manual Review",
            ])}
          />
          <HiveCard title="Publisher Hub Entegrasyonu">
            <p>API provider yayınları Publisher Hub <code>enqueue</code> / <code>publish_item</code> üzerinden delegasyon ile yapılır.</p>
            <p>Integration: {integrations.publisher_hub?.ok ? "✅" : "⚠️"}</p>
          </HiveCard>
        </HivePanel>
      )}

      {tab === "link_policy" && (
        <HivePanel title="Link Policy">
          <HiveAlert type="info">
            Spam pattern engeli: exact match anchor oranı düşük, anchor tekrarı yok, her içerikte link zorunlu değil.
          </HiveAlert>
          {lastPlan?.link_policy ? (
            <HiveTable
              columns={["Anchor", "Target URL", "Link Type"]}
              rows={lastPlan.link_policy.map((lp) => [lp.anchor || "—", (lp.target_url || "—").slice(0, 48), lp.link_type])}
            />
          ) : meshPlans[0]?.link_policy ? (
            <HiveTable
              columns={["Anchor", "Target URL", "Link Type"]}
              rows={meshPlans[0].link_policy.map((lp) => [lp.anchor || "—", (lp.target_url || "—").slice(0, 48), lp.link_type])}
            />
          ) : (
            <p>Mesh plan oluşturun — link policy otomatik üretilir.</p>
          )}
        </HivePanel>
      )}

      {tab === "tasks" && (
        <HivePanel title="Tasks">
          <HiveTable
            columns={["Task ID", "Provider", "Status", "Title", "Updated"]}
            rows={tasks.map((t) => [
              t.task_id,
              t.provider,
              <HiveStatusBadge status={t.status} />,
              (t.site_title || t.target_keyword || "—").slice(0, 32),
              t.finished_at || t.updated_at || t.created_at || "—",
            ])}
          />
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel title="Reports">
          {reports && (
            <HiveStatGrid
              items={[
                { label: "Mesh Plans", value: reports.mesh_plans },
                { label: "Authority Sites", value: reports.authority_sites },
                { label: "Google Sites Tasks", value: reports.google_sites_tasks },
                { label: "Support Sources", value: reports.support_network_sources },
              ]}
            />
          )}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            {REPORT_TYPES.map((r) => (
              <HiveBtn key={r.id} variant="secondary" onClick={() => exportReport(r.id)} disabled={loading}>
                {r.label}
              </HiveBtn>
            ))}
          </div>
          {exportPath && <p style={{ marginTop: 12 }}><strong>Export:</strong> {exportPath}</p>}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel title="Settings">
          <HiveField label="Default Money Site">
            <HiveInput
              value={settingsDraft.default_money_site || ""}
              onChange={(e) => setSettingsDraft({ ...settingsDraft, default_money_site: e.target.value })}
            />
          </HiveField>
          <HiveField label="Default Network ID">
            <HiveInput
              value={settingsDraft.default_network_id || ""}
              onChange={(e) => setSettingsDraft({ ...settingsDraft, default_network_id: e.target.value })}
            />
          </HiveField>
          <HiveCheck
            label="Duplicate content block (opsiyonel — varsayılan kapalı)"
            checked={!!settingsDraft.duplicate_content_block}
            onChange={(v) => setSettingsDraft({ ...settingsDraft, duplicate_content_block: v })}
          />
          <HiveCheck
            label="Duplicate site block (opsiyonel — varsayılan kapalı)"
            checked={!!settingsDraft.duplicate_site_block}
            onChange={(v) => setSettingsDraft({ ...settingsDraft, duplicate_site_block: v })}
          />
          <HiveCheck
            label="Auto track Rank Watcher"
            checked={!!settingsDraft.auto_track_rank_watcher}
            onChange={(v) => setSettingsDraft({ ...settingsDraft, auto_track_rank_watcher: v })}
          />
          <HiveCheck
            label="Auto register Support Network"
            checked={!!settingsDraft.auto_register_support_network}
            onChange={(v) => setSettingsDraft({ ...settingsDraft, auto_register_support_network: v })}
          />
          <HiveBtn onClick={saveSettings} disabled={loading} style={{ marginTop: 12 }}>Kaydet</HiveBtn>
        </HivePanel>
      )}
    </HiveShell>
    </div>
  );
}
