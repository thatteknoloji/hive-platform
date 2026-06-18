import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveBtn,
  HiveTable,
  HiveCheck,
  HiveField,
  HiveSelect,
  HiveBadge,
  HiveSection,
  HiveEmptyState,
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/action-orchestrator";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "queue", label: "Queue" },
  { id: "running", label: "Running" },
  { id: "completed", label: "Completed" },
  { id: "failed", label: "Failed" },
  { id: "pipelines", label: "Pipelines" },
  { id: "actions", label: "Actions" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const PRIORITY_TONE = { CRITICAL: "danger", HIGH: "warning", MEDIUM: "info", LOW: "neutral" };
const STATUS_TONE = {
  queued: "info",
  processing: "warning",
  waiting_approval: "accent",
  completed: "success",
  failed: "danger",
  cancelled: "neutral",
};

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  return e?.message || "Bilinmeyen hata";
}

export default function ActionOrchestrator({ onNavigate }) {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [settings, setSettings] = useState(null);
  const [settingsDraft, setSettingsDraft] = useState({});
  const [actions, setActions] = useState([]);
  const [pipelines, setPipelines] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [importSource, setImportSource] = useState("autonomous_seo_agent");
  const [projectId, setProjectId] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [d, s, a, p] = await Promise.all([
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/actions`, { params: { limit: 100 } }),
        API.get(`${API_PREFIX}/pipelines`),
      ]);
      setDash(d.data);
      setSettings(s.data.settings);
      setSettingsDraft(s.data.settings || {});
      setActions(a.data.actions || []);
      setPipelines(p.data.pipelines || []);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const saveSettings = async () => {
    try {
      const res = await API.post(`${API_PREFIX}/settings`, settingsDraft);
      setSettings(res.data.settings);
      setMessage("Ayarlar kaydedildi");
      await refresh();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const importPlan = async () => {
    try {
      const res = await API.post(`${API_PREFIX}/import-plan`, {
        source_module: importSource,
        project_id: projectId,
        plan: {},
      });
      setMessage(`${res.data.imported} aksiyon içe aktarıldı (${importSource})`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const runAction = async (actionId, approve = false) => {
    try {
      const res = await API.post(`${API_PREFIX}/run-action/${actionId}`, { approve, force: false });
      setMessage(`Aksiyon: ${res.data.action?.status || res.data.status || "ok"}`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const cancelAction = async (actionId) => {
    try {
      await API.post(`${API_PREFIX}/cancel-action/${actionId}`);
      setMessage("Aksiyon iptal edildi");
      await refresh();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const exportReport = async () => {
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, { report_type: "overview" });
      setMessage(`Rapor: ${res.data.filename}`);
    } catch (err) {
      setError(apiError(err));
    }
  };

  const filterByTab = () => {
    if (tab === "queue") return actions.filter((a) => a.status === "queued" || a.status === "waiting_approval");
    if (tab === "running") return actions.filter((a) => a.status === "processing");
    if (tab === "completed") return actions.filter((a) => a.status === "completed");
    if (tab === "failed") return actions.filter((a) => a.status === "failed");
    return actions;
  };

  const actionRows = filterByTab().map((a) => ({
    ...a,
    _actions: a,
  }));

  return (
    <div className="hive-module hive-ao-page">
      <section className="hive-os-hero hive-learn-hero">
        <div className="hive-os-hero-glow" aria-hidden />
        <div className="hive-os-hero-top">
          <div>
            <span className="hive-os-hero-kicker">HIVE SEO OS · Execution</span>
            <h1 className="hive-os-hero-title">⚡ Action Orchestrator</h1>
            <p className="hive-os-hero-sub">Karar → uygulama köprüsü — Agent önerir, Orchestrator uygular</p>
          </div>
          <HiveBadge tone={dash?.enabled ? "success" : "warning"}>
            {dash?.enabled ? `Mode: ${dash?.mode}` : "Disabled"}
          </HiveBadge>
        </div>
      </section>

      <HiveShell
        title=""
        subtitle=""
        actions={<HiveBtn onClick={refresh} disabled={loading}>{loading ? "…" : "↻ Yenile"}</HiveBtn>}
      >
        {error && <HiveAlert type="error" pulse>{error}</HiveAlert>}
        {message && <HiveAlert type="success">{message}</HiveAlert>}

        {!dash?.enabled && (
          <HiveAlert type="warn">
            Orchestrator devre dışı. Settings sekmesinden enabled=true yapın. Varsayılan mode: plan_only.
          </HiveAlert>
        )}

        <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

        {tab === "dashboard" && dash && (
          <>
            <HiveStatGrid
              columns={4}
              items={[
                { label: "Queued", value: dash.queued, tone: "info" },
                { label: "Processing", value: dash.processing, tone: "warning" },
                { label: "Completed", value: dash.completed, tone: "success" },
                { label: "Failed", value: dash.failed, tone: "danger" },
                { label: "Est. Traffic Gain", value: dash.estimated_traffic_gain, tone: "success" },
                { label: "Est. Authority Gain", value: dash.estimated_authority_gain, tone: "accent" },
                { label: "Today Executions", value: dash.today_executions },
                { label: "Pipeline Success", value: `${dash.pipeline_success_rate}%` },
              ]}
            />
            <HivePanel title="Plan İçe Aktar">
              <div className="hm-form-row">
                <HiveField label="Kaynak">
                  <HiveSelect value={importSource} onChange={(e) => setImportSource(e.target.value)}>
                    <option value="autonomous_seo_agent">Autonomous Agent</option>
                    <option value="opportunity_engine">Opportunity Engine</option>
                    <option value="serp_defense_engine">SERP Defense</option>
                    <option value="crawl_gap_engine">Crawl Gap</option>
                    <option value="mission_control_center">Mission Control</option>
                  </HiveSelect>
                </HiveField>
                <HiveField label="Project ID">
                  <input className="hm-input" value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="opsiyonel" />
                </HiveField>
                <HiveBtn onClick={importPlan} disabled={!dash.enabled}>Import Plan</HiveBtn>
              </div>
            </HivePanel>
          </>
        )}

        {["queue", "running", "completed", "failed", "actions"].includes(tab) && (
          <HivePanel title={TABS.find((t) => t.id === tab)?.label}>
            {actionRows.length === 0 ? (
              <HiveEmptyState
                icon="⚡"
                title="Aksiyon yok"
                description="Dashboard'dan plan içe aktarın veya Autonomous Agent kararlarını import edin."
                actionLabel="Dashboard"
                onAction={() => setTab("dashboard")}
              />
            ) : (
              <div className="hive-ao-action-list">
                {actionRows.map((a) => (
                  <article key={a.action_id} className="hive-ao-action-card">
                    <div className="hive-ao-action-head">
                      <HiveBadge tone={PRIORITY_TONE[a.priority] || "info"}>{a.priority}</HiveBadge>
                      <HiveBadge tone={STATUS_TONE[a.status] || "neutral"}>{a.status}</HiveBadge>
                      <strong>{a.title}</strong>
                    </div>
                    <p className="hive-ao-meta">
                      {a.action_type} · {a.source_module} → {a.assigned_module}
                      {a.pipeline_id && ` · pipeline ${a.pipeline_id.slice(0, 10)}`}
                    </p>
                    <p className="hive-ao-meta">Gain: {a.estimated_gain} · {a.keyword || "—"}</p>
                    <div className="hive-ao-action-btns">
                      {(a.status === "queued" || a.status === "waiting_approval") && (
                        <>
                          <HiveBtn size="sm" onClick={() => runAction(a.action_id, a.status === "waiting_approval")}>Run</HiveBtn>
                          <HiveBtn size="sm" variant="secondary" onClick={() => cancelAction(a.action_id)}>Cancel</HiveBtn>
                        </>
                      )}
                      <HiveBtn size="sm" variant="ghost" onClick={() => onNavigate?.(a.assigned_module?.replace("_engine", "_engine") || a.assigned_module)}>
                        Modül
                      </HiveBtn>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </HivePanel>
        )}

        {tab === "pipelines" && (
          <HivePanel title="Pipelines">
            {!pipelines.length ? (
              <HiveEmptyState icon="🔗" title="Pipeline yok" description="SERP Defense veya Opportunity plan import edin." />
            ) : (
              pipelines.map((p) => (
                <div key={p.pipeline_id} className="hive-ao-pipeline-card">
                  <strong>{p.pipeline_id}</strong>
                  <span>{p.source_module} · {p.steps_completed}/{p.steps_total} · {p.status}</span>
                </div>
              ))
            )}
          </HivePanel>
        )}

        {tab === "reports" && (
          <HivePanel title="Reports">
            <HiveBtn onClick={exportReport}>Export Overview</HiveBtn>
          </HivePanel>
        )}

        {tab === "settings" && settingsDraft && (
          <HivePanel title="Settings & Safety">
            <HiveCheck label="Enabled" checked={!!settingsDraft.enabled} onChange={(e) => setSettingsDraft({ ...settingsDraft, enabled: e.target.checked })} />
            <HiveField label="Mode">
              <HiveSelect value={settingsDraft.mode || "plan_only"} onChange={(e) => setSettingsDraft({ ...settingsDraft, mode: e.target.value })}>
                <option value="plan_only">Plan Only</option>
                <option value="semi_autonomous">Semi Autonomous</option>
                <option value="autonomous">Autonomous</option>
              </HiveSelect>
            </HiveField>
            <HiveField label="Max Concurrent">
              <input type="number" className="hm-input" value={settingsDraft.max_concurrent_actions ?? 5} onChange={(e) => setSettingsDraft({ ...settingsDraft, max_concurrent_actions: Number(e.target.value) })} />
            </HiveField>
            <h4 className="hive-ao-safety-title">Safety Rules</h4>
            {["allow_publish", "allow_deploy", "allow_google_sites", "allow_github_pages", "allow_authority_actions", "allow_network_actions"].map((key) => (
              <HiveCheck
                key={key}
                label={key.replace(/_/g, " ")}
                checked={!!settingsDraft[key]}
                onChange={(e) => setSettingsDraft({ ...settingsDraft, [key]: e.target.checked })}
              />
            ))}
            <HiveBtn onClick={saveSettings}>Kaydet</HiveBtn>
          </HivePanel>
        )}
      </HiveShell>
    </div>
  );
}
