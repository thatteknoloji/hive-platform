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
  HiveCard,
  HiveCheck,
  HiveCode,
  HiveMissionBoard,
  HiveContextBar,
  HiveSection,
  HiveIntegrationList,
  HiveStatusBadge,
} from "../components/HiveModuleUI";
import { HiveCommandBar } from "../components/HiveAppShell";

const API_PREFIX = "/api/autonomous-agent";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "threats", label: "Threats" },
  { id: "growth", label: "Growth" },
  { id: "authority", label: "Authority" },
  { id: "refresh", label: "Refresh" },
  { id: "publishing", label: "Publishing" },
  { id: "daily", label: "Daily Mission" },
  { id: "weekly", label: "Weekly Mission" },
  { id: "decisions", label: "Decisions" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

export default function AutonomousSEOAgent() {
  const [tab, setTab] = useState("dashboard");
  const [projectId, setProjectId] = useState(sessionStorage.getItem("asa_project_id") || "");
  const [networkId, setNetworkId] = useState(sessionStorage.getItem("asa_network_id") || "");
  const [health, setHealth] = useState(null);
  const [settings, setSettings] = useState(null);
  const [settingsDraft, setSettingsDraft] = useState({});
  const [dash, setDash] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [missions, setMissions] = useState({ daily: [], weekly: [] });
  const [reports, setReports] = useState(null);
  const [dailyMission, setDailyMission] = useState(null);
  const [weeklyMission, setWeeklyMission] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");

  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}${networkId ? `&network_id=${encodeURIComponent(networkId)}` : ""}` : "";

  const refresh = useCallback(async () => {
    try {
      const [h, s, d, dec, mis, rep] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/dashboard${q}`).catch(() => ({ data: null })),
        API.get(`${API_PREFIX}/decisions?limit=50${projectId ? `&project_id=${encodeURIComponent(projectId)}` : ""}`).catch(() => ({ data: { decisions: [] } })),
        API.get(`${API_PREFIX}/missions`).catch(() => ({ data: { daily: [], weekly: [] } })),
        API.get(`${API_PREFIX}/reports`).catch(() => ({ data: null })),
      ]);
      setHealth(h.data);
      const st = s.data.settings || s.data;
      setSettings(st);
      setSettingsDraft(st);
      setDash(d.data);
      setDecisions(dec.data.decisions || []);
      setMissions({ daily: mis.data.daily || [], weekly: mis.data.weekly || [] });
      setReports(rep.data);
    } catch (err) {
      setError(apiError(err));
    }
  }, [q, projectId]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (projectId) sessionStorage.setItem("asa_project_id", projectId);
    if (networkId) sessionStorage.setItem("asa_network_id", networkId);
  }, [projectId, networkId]);

  const analyzeProject = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post(`${API_PREFIX}/analyze-project`, { project_id: projectId, network_id: networkId });
      setMessage(`${res.data.decisions?.length || 0} karar üretildi (mode: ${res.data.mode})`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const genDaily = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/generate-daily-mission`, { project_id: projectId, network_id: networkId });
      setDailyMission(res.data.mission);
      setMessage("Daily mission oluşturuldu");
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const genWeekly = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/generate-weekly-mission`, { project_id: projectId, network_id: networkId });
      setWeeklyMission(res.data.mission);
      setMessage("Weekly mission oluşturuldu");
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
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (type) => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, { report_type: type });
      setExportPath(res.data.path || "");
      setMessage(`Rapor: ${type}`);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const decisionRows = (list) => (list || []).map((d) => [
    d.agent_type,
    d.recommended_action,
    d.priority_score ?? "—",
    d.confidence_score ?? "—",
    (d.keyword || d.reason || "—").slice(0, 40),
    d.status,
  ]);

  return (
    <HiveShell title="🤖 Autonomous SEO Agent" subtitle="Modül çıktılarını okuyup aksiyon kararı veren merkezi karar katmanı">
      {error && <HiveAlert type="error">{error}</HiveAlert>}
      {message && <HiveAlert type="success">{message}</HiveAlert>}

      {!settings?.enabled && (
        <HiveAlert type="warning">Agent varsayılan olarak kapalı. Settings sekmesinden enabled=true yapın.</HiveAlert>
      )}

      <HiveContextBar>
        <HiveField label="Project ID">
          <HiveInput value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="proj-..." />
        </HiveField>
        <HiveField label="Network ID">
          <HiveInput value={networkId} onChange={(e) => setNetworkId(e.target.value)} placeholder="net-..." />
        </HiveField>
        <HiveBtn onClick={analyzeProject} disabled={loading}>Projeyi Analiz Et</HiveBtn>
        <HiveBtn variant="secondary" onClick={refresh} disabled={loading}>Yenile</HiveBtn>
      </HiveContextBar>

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && dash && (
        <HivePanel title="Mission Overview" description="Agent karar özeti — günlük/haftalık görev akışına hazır">
          <HiveCommandBar placeholder="Bugün ne yapıyoruz? Agent aksiyonu veya keyword…" />
          <HiveMissionBoard
            primary={[
              { label: "Active Threats", value: dash.active_threats ?? 0, tone: "danger", hint: "Defense agent" },
              { label: "Growth Opportunities", value: dash.growth_opportunities ?? 0, tone: "accent", hint: "Growth agent" },
              { label: "Success Rate", value: `${dash.success_rate ?? 0}%`, tone: "ok", hint: "Decision memory" },
            ]}
            secondary={[
              { label: "Authority", value: dash.authority_opportunities ?? 0 },
              { label: "Refresh", value: dash.refresh_candidates ?? 0 },
              { label: "Pending Publish", value: dash.pending_publish ?? 0 },
              { label: "Weekly Impact", value: dash.weekly_impact_estimate ?? 0 },
              { label: "Mode", value: dash.mode || "plan_only" },
            ]}
          />
          <HiveSection title="Suggested Actions" description="Öncelik skoruna göre sıralı">
            <HiveTable
              columns={["Agent", "Action", "Priority", "Confidence", "Context", "Status"]}
              rows={decisionRows(dash.suggested_actions)}
              emptyText="Henüz karar yok — projeyi analiz edin"
            />
          </HiveSection>
        </HivePanel>
      )}

      {tab === "threats" && (
        <HivePanel title="Threats — Defense Agent">
          <HiveTable columns={["Agent", "Action", "Priority", "Confidence", "Context", "Status"]} rows={decisionRows(dash?.threats || decisions.filter((d) => d.agent_type === "defense"))} />
        </HivePanel>
      )}

      {tab === "growth" && (
        <HivePanel title="Growth — Growth Agent">
          <HiveTable columns={["Agent", "Action", "Priority", "Confidence", "Context", "Status"]} rows={decisionRows(dash?.growth_queue || decisions.filter((d) => d.agent_type === "growth"))} />
        </HivePanel>
      )}

      {tab === "authority" && (
        <HivePanel title="Authority — Authority Agent">
          <HiveTable columns={["Agent", "Action", "Priority", "Confidence", "Context", "Status"]} rows={decisionRows(dash?.authority_queue || decisions.filter((d) => d.agent_type === "authority"))} />
        </HivePanel>
      )}

      {tab === "refresh" && (
        <HivePanel title="Refresh — Content Agent">
          <HiveTable columns={["Agent", "Action", "Priority", "Confidence", "Context", "Status"]} rows={decisionRows(dash?.refresh_queue || decisions.filter((d) => d.agent_type === "content"))} />
        </HivePanel>
      )}

      {tab === "publishing" && (
        <HivePanel title="Publishing — Publisher Agent">
          <HiveAlert type="info">Varsayılan: publish/deploy kapalı (plan_only). Settings&apos;ten açılabilir.</HiveAlert>
          <HiveTable columns={["Agent", "Action", "Priority", "Confidence", "Context", "Status"]} rows={decisionRows(dash?.publish_queue || decisions.filter((d) => d.agent_type === "publisher"))} />
        </HivePanel>
      )}

      {tab === "daily" && (
        <HivePanel title="Daily Mission">
          <HiveBtn onClick={genDaily} disabled={loading}>Günlük Görev Üret</HiveBtn>
          {(dailyMission || missions.daily[0]) && (
            <HiveCard title={`Daily — ${(dailyMission || missions.daily[0]).date || ""}`}>
              <ul>{((dailyMission || missions.daily[0]).summary || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
              <HiveCode>{JSON.stringify(dailyMission || missions.daily[0], null, 2)}</HiveCode>
            </HiveCard>
          )}
        </HivePanel>
      )}

      {tab === "weekly" && (
        <HivePanel title="Weekly Mission">
          <HiveBtn onClick={genWeekly} disabled={loading}>Haftalık Plan Üret</HiveBtn>
          {(weeklyMission || missions.weekly[0]) && (
            <HiveCard title="Weekly Plan">
              {Object.entries((weeklyMission || missions.weekly[0]).sections || {}).map(([k, v]) => (
                <div key={k} style={{ marginBottom: 12 }}>
                  <strong>{k}</strong>: {(v || []).length} aksiyon
                </div>
              ))}
              <HiveCode>{JSON.stringify(weeklyMission || missions.weekly[0], null, 2)}</HiveCode>
            </HiveCard>
          )}
        </HivePanel>
      )}

      {tab === "decisions" && (
        <HivePanel title="Decisions">
          <HiveTable columns={["Agent", "Action", "Priority", "Confidence", "Context", "Status"]} rows={decisionRows(decisions)} />
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel title="Reports">
          {reports && (
            <HiveStatGrid items={[
              { label: "Decisions", value: reports.decisions_count },
              { label: "Daily Missions", value: reports.daily_missions },
              { label: "Weekly Missions", value: reports.weekly_missions },
              { label: "Audit Entries", value: reports.audit_entries },
            ]} />
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            {["overview", "decisions", "missions", "audit"].map((t) => (
              <HiveBtn key={t} variant="secondary" onClick={() => exportReport(t)} disabled={loading}>{t}</HiveBtn>
            ))}
          </div>
          {exportPath && <p style={{ marginTop: 8 }}>{exportPath}</p>}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel title="Settings">
          <HiveCheck label="Enabled" checked={!!settingsDraft.enabled} onChange={(v) => setSettingsDraft({ ...settingsDraft, enabled: v })} />
          <HiveField label="Mode (plan_only | semi_autonomous | autonomous)">
            <HiveInput value={settingsDraft.mode || "plan_only"} onChange={(e) => setSettingsDraft({ ...settingsDraft, mode: e.target.value })} />
          </HiveField>
          <HiveField label="Max actions per day">
            <HiveInput type="number" value={settingsDraft.max_actions_per_day ?? 25} onChange={(e) => setSettingsDraft({ ...settingsDraft, max_actions_per_day: Number(e.target.value) })} />
          </HiveField>
          <HiveField label="Min confidence score">
            <HiveInput type="number" value={settingsDraft.min_confidence_score ?? 70} onChange={(e) => setSettingsDraft({ ...settingsDraft, min_confidence_score: Number(e.target.value) })} />
          </HiveField>
          <HiveCheck label="Allow refresh" checked={!!settingsDraft.allow_refresh} onChange={(v) => setSettingsDraft({ ...settingsDraft, allow_refresh: v })} />
          <HiveCheck label="Allow publish" checked={!!settingsDraft.allow_publish} onChange={(v) => setSettingsDraft({ ...settingsDraft, allow_publish: v })} />
          <HiveCheck label="Allow authority actions" checked={!!settingsDraft.allow_authority_actions} onChange={(v) => setSettingsDraft({ ...settingsDraft, allow_authority_actions: v })} />
          <HiveCheck label="Allow network actions" checked={!!settingsDraft.allow_network_actions} onChange={(v) => setSettingsDraft({ ...settingsDraft, allow_network_actions: v })} />
          <HiveCheck label="Allow deploy" checked={!!settingsDraft.allow_deploy} onChange={(v) => setSettingsDraft({ ...settingsDraft, allow_deploy: v })} />
          <HiveBtn onClick={saveSettings} disabled={loading} style={{ marginTop: 12 }}>Kaydet</HiveBtn>
        </HivePanel>
      )}
    </HiveShell>
  );
}
