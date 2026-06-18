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
import { ExecutiveCEODashboard } from "../components/HiveOSVisualizations";

const API_PREFIX = "/api/executive-ai";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "summary", label: "Executive Summary" },
  { id: "priorities", label: "Priorities" },
  { id: "missions", label: "Missions" },
  { id: "forecasts", label: "Forecasts" },
  { id: "revenue", label: "Revenue" },
  { id: "citation", label: "Citation" },
  { id: "authority", label: "Authority" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

function scoreVariant(s) {
  const n = Number(s) || 0;
  if (n >= 75) return "ok";
  if (n >= 50) return "warn";
  return "error";
}

function catVariant(c) {
  if (c === "Healthy" || c === "Growth Mode") return "ok";
  if (c === "Warning") return "warn";
  return "error";
}

export default function ExecutiveAI() {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [settings, setSettings] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [priorities, setPriorities] = useState([]);
  const [missions, setMissions] = useState(null);
  const [forecasts, setForecasts] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [projectId, setProjectId] = useState("");

  const loadBase = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, d, s, p] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/priorities`),
      ]);
      setHealth(h.data);
      setDash(d.data);
      setSettings(s.data?.settings || s.data);
      setPriorities(p.data?.priorities || []);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTabData = useCallback(async (activeTab) => {
    try {
      if (activeTab === "missions" || activeTab === "dashboard") {
        const m = await API.get(`${API_PREFIX}/missions`);
        setMissions(m.data);
      }
      if (activeTab === "forecasts" || activeTab === "revenue" || activeTab === "citation" || activeTab === "authority") {
        const f = await API.get(`${API_PREFIX}/forecasts`, { params: { project_id: projectId } });
        setForecasts(f.data?.forecasts || f.data);
      }
      if (activeTab === "reports" || activeTab === "summary") {
        const r = await API.get(`${API_PREFIX}/reports`);
        setReports(r.data?.reports || []);
      }
    } catch (e) {
      setError(apiError(e));
    }
  }, [projectId]);

  useEffect(() => {
    loadBase();
  }, [loadBase]);

  useEffect(() => {
    loadTabData(tab);
  }, [tab, loadTabData]);

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post(`${API_PREFIX}/analyze-project`, { project_id: projectId.trim() });
      setAnalysis(res.data);
      setMessage(`Analiz tamam — Executive Score: ${res.data?.summary?.overall_score ?? "—"}`);
      loadBase();
      loadTabData(tab);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (rt = "overview") => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, { report_type: rt });
      setExportPath(res.data?.path || "");
      setMessage(`Rapor: ${rt}`);
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

  const summary = analysis?.summary || dash?.summary || {};
  const ceo = analysis?.ceo_reports || (reports[0]?.reports || {});
  const fc = analysis?.forecasts || forecasts || {};

  return (
    <HiveShell
      title="Executive AI"
      subtitle="Stratejik karar katmanı — üretim/yayın/deploy yok, sadece önceliklendirme"
      loading={loading}
    >
      {error && <HiveAlert tone="error">{error}</HiveAlert>}
      {message && <HiveAlert tone="ok">{message}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      <HivePanel title="Proje Analizi" style={{ marginBottom: "1rem" }}>
        <HiveField label="Project ID (boş = global)">
          <HiveInput value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="rank-watcher project id" />
        </HiveField>
        <HiveBtn onClick={handleAnalyze}>Analyze Project</HiveBtn>
      </HivePanel>

      {tab === "dashboard" && (
        <>
          <ExecutiveCEODashboard dash={dash} priorities={priorities} />
          <HiveStatGrid
            items={[
              { label: "Executive Score", value: dash?.executive_score ?? summary.overall_score ?? "—", variant: scoreVariant(dash?.executive_score || summary.overall_score) },
              { label: "Performance Score", value: dash?.performance_score ?? summary.performance_score ?? "—", variant: scoreVariant(dash?.performance_score || summary.performance_score) },
              { label: "Performance Risk", value: dash?.performance_risk ?? summary.performance_risk ?? "—", variant: (dash?.performance_risk ?? summary.performance_risk ?? 0) >= 55 ? "danger" : "success" },
              { label: "Health Category", value: dash?.health_category || summary.health_category || "—", variant: catVariant(dash?.health_category || summary.health_category) },
              { label: "Priorities", value: dash?.priorities_count ?? priorities.length },
              { label: "Agent Uyumu", value: `${dash?.agent_alignment_pct ?? 0}%` },
              { label: "Daily Missions", value: dash?.missions_daily ?? 0 },
              { label: "Projects", value: dash?.projects_analyzed ?? 0 },
            ]}
          />
          {dash?.latest_ceo_headline && (
            <HiveAlert tone="info">{dash.latest_ceo_headline}</HiveAlert>
          )}
          {analysis?.top_actions?.length > 0 && (
            <HivePanel title="Top 5 Actions">
              <ol style={{ margin: 0, paddingLeft: "1.2rem" }}>
                {analysis.top_actions.map((a) => (
                  <li key={a.rank}>{a.title} <span className="sf-dim">({a.source})</span></li>
                ))}
              </ol>
            </HivePanel>
          )}
        </>
      )}

      {tab === "summary" && (
        <HiveStatGrid
          items={[
            { label: "Health", value: summary.health_score ?? "—" },
            { label: "Growth", value: summary.growth_score ?? "—" },
            { label: "Risk", value: summary.risk_score ?? "—", variant: scoreVariant(100 - (summary.risk_score || 0)) },
            { label: "Revenue", value: summary.revenue_score ?? "—" },
            { label: "Citation", value: summary.citation_score ?? "—" },
            { label: "Authority", value: summary.authority_score ?? "—" },
            { label: "Execution", value: summary.execution_score ?? "—" },
            { label: "Overall", value: summary.overall_score ?? "—", variant: scoreVariant(summary.overall_score) },
          ]}
        />
      )}

      {tab === "priorities" && (
        <HiveTable
          columns={[
            { key: "title", label: "Başlık" },
            { key: "source", label: "Kaynak" },
            { key: "priority_score", label: "Skor", render: (r) => <HiveStatusBadge variant={scoreVariant(r.priority_score)} label={String(r.priority_score)} /> },
            { key: "impact", label: "Impact" },
            { key: "revenue", label: "Revenue" },
          ]}
          rows={priorities}
          emptyText="Öncelik yok — Analyze Project çalıştırın"
        />
      )}

      {tab === "missions" && missions && (
        <>
          <HivePanel title="Daily Mission">
            <ul>{(missions.daily || []).map((m) => <li key={m.id}>{m.title}</li>)}</ul>
          </HivePanel>
          <HivePanel title="Weekly Mission">
            <ul>{(missions.weekly || []).map((m) => <li key={m.id}>{m.title}</li>)}</ul>
          </HivePanel>
          <HivePanel title="Monthly Mission">
            <ul>{(missions.monthly || []).map((m) => <li key={m.id}>{m.title}</li>)}</ul>
          </HivePanel>
        </>
      )}

      {tab === "forecasts" && (
        <HiveStatGrid
          items={[
            { label: "Revenue (haftalık lead est.)", value: fc.revenue_forecast?.weekly_leads_est ?? "—" },
            { label: "Revenue (aylık est.)", value: fc.revenue_forecast?.monthly_revenue_est ?? "—" },
            { label: "Citation Health", value: fc.citation_forecast?.citation_health ?? "—" },
            { label: "AI Visibility", value: fc.citation_forecast?.ai_visibility_avg ?? "—" },
            { label: "Risk Alert", value: fc.risk_forecast?.alert ? "Evet" : "Hayır" },
            { label: "Pending Actions", value: fc.authority_forecast?.pending_actions ?? "—" },
          ]}
        />
      )}

      {tab === "revenue" && (
        <HivePanel title="Revenue Impact">
          <p>ROI skoru: {fc.revenue_forecast?.roi_score ?? "—"}</p>
          <p>Trend: {fc.revenue_forecast?.trend ?? "—"}</p>
          {ceo.today?.top_revenue_source && <p>En yüksek gelir kaynağı: <strong>{ceo.today.top_revenue_source}</strong></p>}
        </HivePanel>
      )}

      {tab === "citation" && (
        <HivePanel title="Citation Forecast">
          <p>Citation health: {fc.citation_forecast?.citation_health ?? summary.citation_score ?? "—"}</p>
          <p>Risk sayfalar: {fc.citation_forecast?.risk_pages ?? "—"}</p>
          <p>Trend: {fc.citation_forecast?.trend ?? "—"}</p>
          {ceo.today?.risks?.length > 0 && <HiveAlert tone="warn">Riskler: {ceo.today.risks.join(", ")}</HiveAlert>}
        </HivePanel>
      )}

      {tab === "authority" && (
        <HivePanel title="Authority Forecast">
          <p>Queued batches: {fc.authority_forecast?.queued_batches ?? "—"}</p>
          <p>Published today: {fc.authority_forecast?.published_today ?? "—"}</p>
          <p>Execution rate: {fc.authority_forecast?.execution_rate ?? "—"}%</p>
          {ceo.today?.authority_note && <p>{ceo.today.authority_note}</p>}
        </HivePanel>
      )}

      {tab === "reports" && (
        <>
          <HivePanel title="CEO Reports">
            {["today", "week", "month"].map((p) => (
              <div key={p} style={{ marginBottom: "1rem" }}>
                <strong>{p === "today" ? "Bugün" : p === "week" ? "Bu Hafta" : "Bu Ay"}</strong>
                <p>{ceo[p]?.headline || "—"}</p>
                <p className="sf-dim">Fırsat: {ceo[p]?.top_opportunity || "—"} · Risk: {ceo[p]?.top_risk || "—"}</p>
              </div>
            ))}
          </HivePanel>
          <HiveBtn variant="secondary" onClick={() => handleExport("overview")}>Export Overview</HiveBtn>
          {exportPath && <p className="sf-dim">{exportPath}</p>}
        </>
      )}

      {tab === "settings" && settings && (
        <HivePanel title="Settings">
          <HiveCheck label="Enabled" checked={!!settings.enabled} onChange={(v) => setSettings({ ...settings, enabled: v })} />
          <HiveField label="Default Project ID">
            <HiveInput value={settings.default_project_id || ""} onChange={(e) => setSettings({ ...settings, default_project_id: e.target.value })} />
          </HiveField>
          <HiveField label="Priority Threshold">
            <HiveInput type="number" value={settings.priority_threshold} onChange={(e) => setSettings({ ...settings, priority_threshold: Number(e.target.value) })} />
          </HiveField>
          <HiveBtn onClick={handleSaveSettings}>Kaydet</HiveBtn>
        </HivePanel>
      )}
    </HiveShell>
  );
}
