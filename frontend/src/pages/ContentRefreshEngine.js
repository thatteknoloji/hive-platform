import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveToolbar,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveFormRow,
  HiveField,
  HiveSelect,
  HiveInput,
  HiveBtn,
  HiveBadge,
  HiveTable,
  HiveCard,
  HiveCode,
  HiveCheck,
} from "../components/HiveModuleUI";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "candidates", label: "Refresh Candidates" },
  { id: "analysis", label: "Analysis" },
  { id: "plans", label: "Refresh Plans" },
  { id: "queue", label: "Queue" },
  { id: "jobs", label: "Jobs" },
  { id: "reports", label: "Reports" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

export default function ContentRefreshEngine({ preselectedProjectId = "" }) {
  const [tab, setTab] = useState("dashboard");
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(
    preselectedProjectId || sessionStorage.getItem("content_refresh_project_id") || ""
  );
  const [health, setHealth] = useState(null);
  const [settings, setSettings] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [plans, setPlans] = useState([]);
  const [queue, setQueue] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [selectedPageId, setSelectedPageId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");

  const loadProjects = useCallback(async () => {
    try {
      const res = await API.get("/api/astro-factory/projects");
      setProjects(res.data.projects || []);
    } catch {
      setProjects([]);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [h, s, q, j] = await Promise.all([
        API.get("/api/content-refresh/health"),
        API.get("/api/content-refresh/settings"),
        API.get("/api/content-refresh/queue"),
        API.get("/api/content-refresh/jobs?limit=30"),
      ]);
      setHealth(h.data);
      setSettings(s.data.settings);
      setQueue(q.data.queue || []);
      setJobs(j.data.jobs || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  useEffect(() => { loadProjects(); refresh(); }, [loadProjects, refresh]);
  useEffect(() => {
    if (projectId) sessionStorage.setItem("content_refresh_project_id", projectId);
  }, [projectId]);

  const saveSettings = async (patch) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/settings", patch);
      setSettings(res.data.settings);
      setMessage("Ayarlar kaydedildi");
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runScan = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/scan", { project_id: projectId });
      setCandidates(res.data.candidates || []);
      setMessage(`Tarama: ${res.data.pages_scanned} sayfa, ${res.data.refresh_needed} yenileme adayı`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runAnalyze = async (pageId) => {
    const pid = pageId || selectedPageId;
    if (!projectId || !pid) { setError("Proje ve sayfa seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/analyze-page", { project_id: projectId, page_id: pid });
      setAnalysis(res.data);
      setSelectedPageId(pid);
      setTab("analysis");
      setMessage("Sayfa analizi tamamlandı");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runAnalyzeProject = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/analyze-project", { project_id: projectId });
      setAnalysis(res.data);
      setTab("analysis");
      setMessage(`Proje analizi: ${res.data.refresh_needed_count} yenileme adayı`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runCreatePlans = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/create-refresh-plan", { project_id: projectId });
      setPlans(res.data.plans || []);
      setMessage(`${res.data.count} refresh planı oluşturuldu`);
      setTab("plans");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runQueue = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/queue", { project_id: projectId });
      setMessage(`${res.data.queued} sayfa kuyruğa alındı (toplam ${res.data.queue_size})`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runProcess = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/process", {
        project_id: projectId,
        auto_publish: settings?.auto_publish || false,
        auto_deploy: settings?.auto_deploy || false,
      });
      const s = res.data.summary || {};
      setMessage(
        `Yenilenen: ${s.pages_refreshed || 0} · Gate fail: ${s.quality_failed || 0} · Ort. iyileşme: ${s.avg_improvement_score || 0}`
      );
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runRefreshProject = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/refresh-project", {
        project_id: projectId,
        auto_publish: settings?.auto_publish || false,
        auto_deploy: settings?.auto_deploy || false,
      });
      const s = res.data.summary || {};
      setMessage(`Proje refresh: ${s.pages_refreshed || 0} sayfa yenilendi`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runExport = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/content-refresh/export-report", {
        project_id: projectId || "",
        job_id: "",
      });
      setExportPath(res.data.path || "");
      setMessage("Rapor dışa aktarıldı");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const dash = health?.dashboard || {};

  return (
    <HiveShell
      title="♻️ Content Refresh Engine V1"
      subtitle="Decay tespiti, QIE entegrasyonu, entity/GEO/link refresh, Quality Gate ≥85"
    >
      <HiveAlert type="ok">{message}</HiveAlert>
      <HiveAlert type="err">{error}</HiveAlert>

      <HiveToolbar>
        <HiveField label="Proje" className="hm-field-grow">
          <HiveSelect value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">— Proje seçin —</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.site_name || p.slug} ({p.domain})</option>
            ))}
          </HiveSelect>
        </HiveField>
        <div className="hm-toolbar-actions">
          <HiveBtn variant="primary" disabled={loading} onClick={runScan}>Scan</HiveBtn>
          <HiveBtn variant="outline" disabled={loading} onClick={runAnalyzeProject}>Analyze Project</HiveBtn>
          <HiveBtn variant="outline" disabled={loading} onClick={runCreatePlans}>Plan Oluştur</HiveBtn>
          <HiveBtn variant="outline" disabled={loading} onClick={runQueue}>Kuyruğa Al</HiveBtn>
          <HiveBtn variant="success" disabled={loading} onClick={runProcess}>Process Queue</HiveBtn>
          <HiveBtn variant="warning" disabled={loading} onClick={runRefreshProject}>Full Refresh</HiveBtn>
        </div>
      </HiveToolbar>

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <>
          <HiveStatGrid
            items={[
              ["Critical Pages", dash.critical_pages],
              ["High Priority", dash.high_priority_pages ?? dash.high_priority],
              ["Avg Decay", dash.avg_decay],
              ["Avg Entity Loss", dash.avg_entity_loss],
              ["Avg AI Visibility", dash.avg_ai_visibility_loss],
              ["Avg Authority Drop", dash.avg_authority_drop],
              ["Last Refresh", health?.last_refresh_at ? "✓" : "—"],
            ]}
          />
          <p className="hm-meta-line">
            Son refresh: <strong>{health?.last_refresh_at || "—"}</strong>
            {" · "}
            Son scan: <strong>{health?.last_scan_at || "—"}</strong>
          </p>
          <HivePanel>
            <h3 className="hm-panel-title">Ayarlar</h3>
            {settings && (
              <div className="hm-settings-grid">
                <HiveCheck
                  label="Motor aktif"
                  checked={!!settings.enabled}
                  onChange={(e) => saveSettings({ enabled: e.target.checked })}
                />
                <HiveCheck
                  label="Otomatik refresh"
                  checked={!!settings.auto_refresh}
                  onChange={(e) => saveSettings({ auto_refresh: e.target.checked })}
                />
                <HiveCheck
                  label="Auto Publisher"
                  checked={!!settings.auto_publish}
                  onChange={(e) => saveSettings({ auto_publish: e.target.checked })}
                />
                <HiveCheck
                  label="Otomatik deploy"
                  checked={!!settings.auto_deploy}
                  onChange={(e) => saveSettings({ auto_deploy: e.target.checked })}
                />
                <HiveField label="Priority threshold">
                  <HiveInput
                    type="number"
                    value={settings.priority_threshold}
                    onChange={(e) => saveSettings({ priority_threshold: Number(e.target.value) })}
                  />
                </HiveField>
                <HiveField label="Max pages / run">
                  <HiveInput
                    type="number"
                    value={settings.max_pages_per_run}
                    onChange={(e) => saveSettings({ max_pages_per_run: Number(e.target.value) })}
                  />
                </HiveField>
              </div>
            )}
          </HivePanel>
        </>
      )}

      {tab === "candidates" && (
        <HiveTable
          emptyText="Önce Scan çalıştırın."
          columns={[
            { key: "title", label: "Sayfa", render: (c) => c.title || c.slug },
            {
              key: "priority",
              label: "Priority",
              render: (c) => (
                <>
                  <HiveBadge level={c.priority_label} /> {c.refresh_priority}
                </>
              ),
            },
            { key: "ranking_decay_score", label: "Decay" },
            { key: "ctr_decay_score", label: "CTR" },
            { key: "entity_loss_score", label: "Entity" },
            { key: "ai_visibility_loss_score", label: "AI Vis" },
            { key: "content_age_days", label: "Age (gün)" },
            {
              key: "actions",
              label: "",
              render: (c) => (
                <HiveBtn variant="ghost" size="sm" onClick={() => runAnalyze(c.page_id)}>Analiz</HiveBtn>
              ),
            },
          ]}
          rows={candidates}
        />
      )}

      {tab === "analysis" && (
        analysis ? (
          <HivePanel>
            <h3 className="hm-panel-title">
              {analysis.page?.title || analysis.project?.site_name || "Proje Analizi"}
            </h3>
            {analysis.recommended_actions?.length > 0 && (
              <p className="hm-card-meta">Actions: {analysis.recommended_actions.join(", ")}</p>
            )}
            {analysis.geo_opportunities?.length > 0 && (
              <p className="hm-card-meta">GEO: {analysis.geo_opportunities.join(" · ")}</p>
            )}
            <HiveCode>{JSON.stringify(analysis, null, 2)}</HiveCode>
          </HivePanel>
        ) : (
          <p className="hm-empty">Analiz için bir sayfa seçin veya Analyze Project çalıştırın.</p>
        )
      )}

      {tab === "plans" && (
        plans.length ? plans.map((p) => (
          <HiveCard
            key={p.plan_id}
            title={p.page}
            meta={`Actions: ${(p.actions || []).join(", ")}`}
            actions={<HiveBadge level={p.priority} />}
          />
        )) : (
          <p className="hm-empty">Plan yok — Plan Oluştur ile üretin.</p>
        )
      )}

      {tab === "queue" && (
        <HiveTable
          emptyText="Kuyruk boş."
          columns={[
            { key: "queue_id", label: "ID", render: (q) => <code>{q.queue_id}</code> },
            { key: "page_id", label: "Page" },
            { key: "priority", label: "Priority", render: (q) => <HiveBadge level={q.priority} /> },
            { key: "status", label: "Status" },
            { key: "actions", label: "Actions", render: (q) => (q.actions || []).join(", ") },
          ]}
          rows={queue}
        />
      )}

      {tab === "jobs" && (
        jobs.length ? jobs.map((j) => (
          <HiveCard
            key={j.job_id}
            title={`${j.job_id} — ${j.status}`}
            meta={j.type}
          >
            <div className="hm-job-row">
              <span>{j.started_at} → {j.finished_at || "…"}</span>
              {j.summary && (
                <span>
                  Refreshed: <strong>{j.summary.pages_refreshed}</strong>
                  {" · "}Passed: <strong>{j.summary.quality_passed}</strong>
                  {" · "}Failed: <strong>{j.summary.quality_failed}</strong>
                </span>
              )}
            </div>
          </HiveCard>
        )) : (
          <p className="hm-empty">Henüz job yok.</p>
        )
      )}

      {tab === "reports" && (
        <HivePanel>
          <HiveBtn variant="outline" disabled={loading} onClick={runExport}>Export Report</HiveBtn>
          {exportPath && (
            <p className="hm-meta-line" style={{ marginTop: "0.85rem" }}>
              Dosya: <code>{exportPath}</code>
            </p>
          )}
        </HivePanel>
      )}
    </HiveShell>
  );
}
