import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveToast,
  HiveSkeleton,
  HivePanel,
  HiveSection,
  HiveStatGrid,
  HiveBtn,
  HiveField,
  HiveInput,
  HiveCheck,
  HiveTable,
  HiveTabs,
  HiveEmptyState,
} from "../components/HiveModuleUI";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "settings", label: "Settings" },
  { id: "scan", label: "Scan Missing" },
  { id: "queue", label: "Queue" },
  { id: "process", label: "Process" },
  { id: "jobs", label: "Jobs" },
  { id: "reports", label: "Reports" },
];

const SOURCE_LABELS = {
  page_hub: "Page Hub",
  sss_automation: "SSS Automation",
  place_seo_pipeline: "Place SEO Pipeline",
  entity_detail_generator: "Entity Detail Generator",
  listing_hub: "Listing Hub",
  wordpress: "WordPress",
  network_replicator: "Network Replicator",
};

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

export default function AstroAutoPublisher({ preselectedProjectId = "" }) {
  const [tab, setTab] = useState("dashboard");
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(preselectedProjectId || sessionStorage.getItem("astro_auto_project_id") || "");
  const [health, setHealth] = useState(null);
  const [settings, setSettings] = useState(null);
  const [queue, setQueue] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [scanResult, setScanResult] = useState(null);
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
        API.get("/api/astro-auto/health"),
        API.get("/api/astro-auto/settings"),
        API.get("/api/astro-auto/queue"),
        API.get("/api/astro-auto/jobs?limit=30"),
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
    if (projectId) sessionStorage.setItem("astro_auto_project_id", projectId);
  }, [projectId]);

  const saveSettings = async (patch) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-auto/settings", patch);
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
      const res = await API.post("/api/astro-auto/scan-missing", {
        project_id: projectId,
        include_outdated: true,
      });
      setScanResult(res.data);
      setMessage(`Tarama: ${res.data.missing?.length || 0} eksik, ${res.data.outdated?.length || 0} güncel değil`);
      await refresh();
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
      const res = await API.post("/api/astro-auto/queue-missing", { project_id: projectId, include_outdated: true });
      setMessage(`${res.data.queued} öğe kuyruğa alındı (toplam ${res.data.queue_size})`);
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
      const res = await API.post("/api/astro-auto/process-queue", {
        project_id: projectId,
        auto_deploy: settings?.auto_deploy || false,
        auto_build: settings?.auto_build !== false,
      });
      const s = res.data.summary || {};
      setMessage(`Yazılan: ${s.written || 0} · Gate fail: ${s.quality_failed || 0} · Build: ${s.built ? "✓" : "—"} · Deploy: ${s.deployed ? "✓" : "—"}`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runSyncAll = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-auto/sync-all", {
        project_id: projectId,
        auto_deploy: settings?.auto_deploy || false,
        max_items: settings?.max_items_per_run || 50,
      });
      setMessage(`Sync All tamam — job ${res.data.job_id}`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runDeploy = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/astro-auto/deploy", { project_id: projectId });
      if (res.data.success) {
        setMessage(`Deploy OK: ${res.data.url || res.data.deployment_url || ""}`);
      } else {
        setError(res.data.error || "Deploy başarısız");
      }
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
      const res = await API.post("/api/astro-auto/export-report", { project_id: projectId });
      setExportPath(res.data.path || "");
      setMessage("Rapor export edildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const ignoreWarning = async (queueId) => {
    try {
      await API.post("/api/astro-auto/queue-ignore-warning", { queue_id: queueId });
      setMessage("Warning ignore işaretlendi (critical override yok)");
      await refresh();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const dash = health?.dashboard || {};

  return (
    <HiveShell title="Astro Auto Publisher" subtitle="Gerçek tarama · Quality Gate · Astro JSON yazımı · build · Cloudflare deploy">
      {error && <HiveAlert type="error">{error}</HiveAlert>}
      <HiveToast message={message} onClose={() => setMessage("")} />

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: "1rem", alignItems: "center" }}>
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ minWidth: 220, padding: "0.4rem" }}>
          <option value="">— Astro proje seç —</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.site_name || p.slug} ({p.id})</option>
          ))}
        </select>
        <HiveBtn onClick={runSyncAll} disabled={loading || !projectId}>
          Sync All
        </HiveBtn>
        <HiveBtn onClick={refresh} disabled={loading}>Yenile</HiveBtn>
      </div>



      <div className="ch-tabs" style={{ marginBottom: "1rem" }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`ch-tab ${tab === t.id ? "active" : ""}`}
            onClick={() => { setTab(t.id); setMessage(""); setError(""); }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <HiveSkeleton lines={6} />}

      {tab === "dashboard" && (
        <div className="ch-panel">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 12 }}>
            {[
              ["Missing", dash.missing || 0],
              ["Outdated", dash.outdated || 0],
              ["Queued", dash.queued || 0],
              ["Quality Failed", dash.quality_failed || 0],
              ["Last Build", dash.last_build_at || "—"],
              ["Last Deploy", dash.last_deploy_url ? "✓" : "—"],
            ].map(([label, val]) => (
              <div key={label} className="ch-preview-box" style={{ textAlign: "center", padding: "1rem" }}>
                <div style={{ fontSize: "0.75rem", opacity: 0.7 }}>{label}</div>
                <div style={{ fontSize: "1.1rem", fontWeight: 600, marginTop: 4 }}>{String(val).slice(0, 40)}</div>
              </div>
            ))}
          </div>
          {health && (
            <p className="sf-dim" style={{ marginTop: "1rem" }}>
              Kuyruk: {health.queue_size} · CF: {health.cloudflare_configured ? "✓" : "—"} ·
              Scheduler: {health.scheduler_active ? "aktif" : "—"} ·
              Running job: {health.running_job || "—"}
            </p>
          )}
          {dash.last_deploy_url && (
            <p><a href={dash.last_deploy_url} target="_blank" rel="noreferrer">{dash.last_deploy_url}</a></p>
          )}
        </div>
      )}

      {tab === "settings" && settings && (
        <div className="ch-panel">
          <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
            <label><input type="checkbox" checked={!!settings.enabled} onChange={(e) => saveSettings({ enabled: e.target.checked, target_project_id: projectId })} /> Enabled (scheduler)</label>
            <label><input type="checkbox" checked={!!settings.auto_build} onChange={(e) => saveSettings({ auto_build: e.target.checked })} /> Auto Build</label>
            <label><input type="checkbox" checked={!!settings.auto_deploy} onChange={(e) => saveSettings({ auto_deploy: e.target.checked })} /> Auto Deploy</label>
            <label><input type="checkbox" checked={!!settings.require_quality_gate_pass} onChange={(e) => saveSettings({ require_quality_gate_pass: e.target.checked })} /> Quality Gate zorunlu</label>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginTop: "1rem" }}>
            <label>Interval (dk) <input type="number" min={5} value={settings.interval_minutes} onChange={(e) => saveSettings({ interval_minutes: Number(e.target.value) })} style={{ width: 80, marginLeft: 8 }} /></label>
            <label>Min skor <input type="number" min={0} max={100} value={settings.min_quality_score} onChange={(e) => saveSettings({ min_quality_score: Number(e.target.value) })} style={{ width: 70, marginLeft: 8 }} /></label>
            <label>Max/run <input type="number" min={1} value={settings.max_items_per_run} onChange={(e) => saveSettings({ max_items_per_run: Number(e.target.value) })} style={{ width: 70, marginLeft: 8 }} /></label>
          </div>
          <div style={{ marginTop: "1rem" }}>
            <strong>Kaynaklar</strong>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginTop: 8 }}>
              {Object.entries(settings.sources || {}).map(([k, v]) => (
                <label key={k}>
                  <input type="checkbox" checked={!!v} onChange={(e) => saveSettings({ sources: { ...settings.sources, [k]: e.target.checked } })} />
                  {" "}{SOURCE_LABELS[k] || k}
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "scan" && (
        <div className="ch-panel">
          <HiveBtn onClick={runScan} disabled={loading || !projectId}>Eksikleri Tara</HiveBtn>
          <HiveBtn onClick={runQueue} disabled={loading || !projectId}>Kuyruğa Al</HiveBtn>
          {scanResult && (
            <ul style={{ marginTop: "1rem" }}>
              <li>Eksik: {scanResult.missing?.length || 0}</li>
              <li>Güncel değil: {scanResult.outdated?.length || 0}</li>
              <li>Sync OK: {scanResult.synced?.length || scanResult.already_synced?.length || 0}</li>
              <li>Gate engeli: {scanResult.blocked?.length || scanResult.blocked_by_quality?.length || 0}</li>
            </ul>
          )}
        </div>
      )}

      {tab === "queue" && (
        <div className="ch-panel" style={{ overflowX: "auto" }}>
          <HiveTable>
            <thead>
              <tr>
                <th>Item</th><th>Source</th><th>Type</th><th>Score</th><th>Status</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {queue.length === 0 && <tr><td colSpan={6}>Kuyruk boş</td></tr>}
              {queue.map((q) => {
                const item = q.content_item || q;
                return (
                  <tr key={q.queue_id || `${item.source}-${item.source_id}`}>
                    <td>{item.title || item.slug}</td>
                    <td>{item.source}</td>
                    <td>{item.type}</td>
                    <td>{q.quality_score ?? item.quality_score ?? "—"}</td>
                    <td>{q.status}</td>
                    <td>
                      {q.status === "quality_failed" && (
                        <HiveBtn onClick={() => ignoreWarning(q.queue_id)}>Ignore warning</HiveBtn>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </HiveTable>
        </div>
      )}

      {tab === "process" && (
        <div className="ch-panel">
          <HiveBtn onClick={runProcess} disabled={loading || !projectId}>Kuyruğu İşle (Build)</HiveBtn>
          <HiveBtn onClick={runDeploy} disabled={loading || !projectId}>Deploy</HiveBtn>
          <p className="sf-dim" style={{ marginTop: "0.75rem" }}>
            auto_deploy varsayılan kapalı — Settings’ten açılabilir. Quality Gate fail varsa deploy engellenir.
          </p>
        </div>
      )}

      {tab === "jobs" && (
        <div className="ch-panel" style={{ overflowX: "auto" }}>
          <HiveTable>
            <thead><tr><th>Job</th><th>Type</th><th>Status</th><th>Project</th><th>Summary</th></tr></thead>
            <tbody>
              {jobs.length === 0 && <tr><td colSpan={5}>Job yok</td></tr>}
              {jobs.map((j) => (
                <tr key={j.job_id}>
                  <td>{j.job_id}</td>
                  <td>{j.type}</td>
                  <td>{j.status}</td>
                  <td>{j.project_id}</td>
                  <td>{JSON.stringify(j.summary || {}).slice(0, 80)}</td>
                </tr>
              ))}
            </tbody>
          </HiveTable>
        </div>
      )}

      {tab === "reports" && (
        <div className="ch-panel">
          <HiveBtn onClick={runExport} disabled={loading}>Export Report</HiveBtn>
          {exportPath && <p style={{ marginTop: "0.75rem" }}><code>{exportPath}</code></p>}
        </div>
      )}
    </HiveShell>
  );
}
