import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveTable,
  HiveCheck,
  HiveStatusBadge,
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/hive-audit";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "modules", label: "Modules" },
  { id: "api", label: "API Routes" },
  { id: "frontend", label: "Frontend Routes" },
  { id: "providers", label: "Providers" },
  { id: "states", label: "States" },
  { id: "queues", label: "Queues" },
  { id: "security", label: "Security" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const CATEGORIES = ["module", "api", "frontend", "provider", "state", "queue", "test", "security"];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

function severityVariant(s) {
  if (s === "info") return "info";
  if (s === "warning") return "warn";
  return "error";
}

function scoreVariant(s) {
  const n = Number(s) || 0;
  if (n >= 75) return "ok";
  if (n >= 50) return "warn";
  return "error";
}

export default function HiveAuditEngine() {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [issues, setIssues] = useState([]);
  const [reports, setReports] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [lastRun, setLastRun] = useState(null);

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, d, s] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/settings`),
      ]);
      setHealth(h.data);
      setDash(d.data);
      setSettings(s.data?.settings || s.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadIssues = useCallback(async (category = "") => {
    try {
      const params = { limit: 200 };
      if (category) params.category = category;
      const r = await API.get(`${API_PREFIX}/issues`, { params });
      setIssues(r.data?.issues || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  const loadReports = useCallback(async () => {
    try {
      const r = await API.get(`${API_PREFIX}/reports`);
      setReports(r.data?.reports || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    const catMap = {
      modules: "module",
      api: "api",
      frontend: "frontend",
      providers: "provider",
      states: "state",
      queues: "queue",
      security: "security",
    };
    if (catMap[tab]) loadIssues(catMap[tab]);
    else if (tab === "dashboard") loadIssues("");
    else if (tab === "reports") loadReports();
  }, [tab, loadIssues, loadReports]);

  const handleRunAudit = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post(`${API_PREFIX}/run`);
      setLastRun(res.data);
      setMessage(`Audit tamamlandı — skor: ${res.data?.scores?.overall_audit_score ?? "—"}`);
      loadCore();
      loadIssues("");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleAck = async (issueId) => {
    try {
      await API.post(`${API_PREFIX}/issue/${issueId}/ack`);
      setMessage(`Issue acknowledged: ${issueId}`);
      loadIssues("");
      loadCore();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const handleResolve = async (issueId) => {
    try {
      await API.post(`${API_PREFIX}/issue/${issueId}/resolve`);
      setMessage(`Issue resolved: ${issueId}`);
      loadIssues("");
      loadCore();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const handleExport = async (reportType = "overview") => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, { report_type: reportType });
      setExportPath(res.data?.path || "");
      setMessage(`Rapor: ${reportType}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/settings`, settings);
      setSettings(res.data?.settings || settings);
      setMessage("Ayarlar kaydedildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const scores = dash?.scores || {};
  const summary = dash?.summary || {};

  const issueColumns = [
    { key: "severity", label: "Severity", render: (v) => <HiveStatusBadge variant={severityVariant(v)}>{v}</HiveStatusBadge> },
    { key: "category", label: "Category" },
    { key: "title", label: "Title" },
    { key: "affected_module", label: "Module" },
    { key: "status", label: "Status" },
    {
      key: "issue_id",
      label: "Actions",
      render: (v, row) => (
        <span style={{ display: "flex", gap: 6 }}>
          {row.status === "open" && (
            <>
              <HiveBtn variant="secondary" onClick={() => handleAck(v)}>Ack</HiveBtn>
              <HiveBtn variant="secondary" onClick={() => handleResolve(v)}>Resolve</HiveBtn>
            </>
          )}
        </span>
      ),
    },
  ];

  return (
    <HiveShell
      title="HIVE Audit Engine"
      subtitle="Modül, API, frontend, provider, state, queue ve güvenlik denetimi"
      loading={loading}
    >
      {error && <HiveAlert variant="error">{error}</HiveAlert>}
      {message && <HiveAlert variant="ok">{message}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <HivePanel>
          <HiveStatGrid
            items={[
              { label: "Overall Audit Score", value: scores.overall_audit_score ?? 0, variant: scoreVariant(scores.overall_audit_score) },
              { label: "Open Issues", value: summary.open_issues ?? 0, variant: summary.open_issues > 0 ? "warn" : "ok" },
              { label: "Critical", value: summary.critical_issues ?? 0, variant: summary.critical_issues > 0 ? "error" : "ok" },
              { label: "Warning", value: summary.warning_issues ?? 0, variant: "warn" },
              ...CATEGORIES.slice(0, 4).map((c) => ({
                label: `${c}_score`,
                value: scores[`${c}_score`] ?? scores[`${c.replace("test", "test")}_score`] ?? "—",
                variant: scoreVariant(scores[`${c}_score`]),
              })),
            ]}
          />
          <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <HiveBtn onClick={handleRunAudit}>Run Full Audit</HiveBtn>
            <HiveBtn variant="secondary" onClick={loadCore}>Yenile</HiveBtn>
          </div>
          {dash?.last_run && <p style={{ marginTop: 12, opacity: 0.75 }}>Son audit: {dash.last_run}</p>}
          {lastRun?.scores && (
            <p style={{ opacity: 0.75 }}>Son run skor: {lastRun.scores.overall_audit_score}</p>
          )}
          <h4 style={{ marginTop: 20 }}>Top Critical Issues</h4>
          <HiveTable
            columns={issueColumns.filter((c) => c.key !== "issue_id").concat(issueColumns.slice(-1))}
            rows={dash?.top_critical || []}
          />
        </HivePanel>
      )}

      {["modules", "api", "frontend", "providers", "states", "queues", "security"].includes(tab) && (
        <HivePanel>
          <HiveTable columns={issueColumns} rows={issues} />
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <HiveBtn onClick={() => handleExport("overview")}>Overview</HiveBtn>
            <HiveBtn variant="secondary" onClick={() => handleExport("issues")}>Issues</HiveBtn>
            <HiveBtn variant="secondary" onClick={() => handleExport("full")}>Full Audit</HiveBtn>
          </div>
          {exportPath && <p style={{ marginTop: 12 }}>Kayıt: {exportPath}</p>}
          <h4 style={{ marginTop: 20 }}>Recent Reports</h4>
          <HiveTable
            columns={[
              { key: "report_id", label: "ID" },
              { key: "run_at", label: "Run At" },
              { key: "total_issues", label: "Issues" },
              { key: "critical_issues", label: "Critical", render: (_, row) => row.scores?.critical_issues ?? "—" },
              { key: "overall", label: "Score", render: (_, row) => row.scores?.overall_audit_score ?? "—" },
            ]}
            rows={reports}
          />
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel>
          <HiveField label="Modül aktif">
            <HiveCheck checked={!!settings.enabled} onChange={(v) => setSettings({ ...settings, enabled: v })} label="Audit Engine etkin" />
          </HiveField>
          <HiveField label="Stale state (gün)">
            <HiveInput type="number" value={settings.stale_state_days ?? 30} onChange={(e) => setSettings({ ...settings, stale_state_days: Number(e.target.value) })} />
          </HiveField>
          <HiveField label="Stuck queue (saat)">
            <HiveInput type="number" value={settings.stuck_queue_hours ?? 6} onChange={(e) => setSettings({ ...settings, stuck_queue_hours: Number(e.target.value) })} />
          </HiveField>
          <HiveField label="Kritik alert">
            <HiveCheck checked={!!settings.alert_on_critical} onChange={(v) => setSettings({ ...settings, alert_on_critical: v })} label="Kritik issue'larda alert" />
          </HiveField>
          <HiveBtn onClick={handleSaveSettings} style={{ marginTop: 16 }}>Kaydet</HiveBtn>
        </HivePanel>
      )}

      {health && (
        <p style={{ marginTop: 16, fontSize: 12, opacity: 0.6 }}>
          Module: {health.module} · Open issues: {health.open_issues} · Publishes: {health.publishes ? "yes" : "no"}
        </p>
      )}
    </HiveShell>
  );
}
