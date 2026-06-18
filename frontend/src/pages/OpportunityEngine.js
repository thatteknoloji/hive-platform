import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveToolbar,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveTable,
  HiveBadge,
  HiveCode,
  HiveConceptTooltip,
  HiveEmptyState,
} from "../components/HiveModuleUI";
import { HIVE_CONCEPTS } from "../config/hiveConcepts";

const API_PREFIX = "/api/opportunity";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "keywords", label: "Keywords" },
  { id: "entities", label: "Entities" },
  { id: "geo", label: "GEO" },
  { id: "authority", label: "Authority" },
  { id: "ai", label: "AI" },
  { id: "quickwins", label: "Quick Wins" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const REPORT_TYPES = [
  { id: "overview", label: "Overview" },
  { id: "keywords", label: "Keyword Opportunities" },
  { id: "entities", label: "Entity Opportunities" },
  { id: "geo", label: "GEO Opportunities" },
  { id: "authority", label: "Authority Opportunities" },
  { id: "ai", label: "AI Opportunities" },
  { id: "quickwins", label: "Quick Wins" },
  { id: "full", label: "Full Analysis" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "API hatası";
}

function OppTable({ rows, emptyText }) {
  return (
    <HiveTable
      columns={[
        { key: "title", label: "Fırsat" },
        { key: "type", label: "Tip" },
        { key: "score", label: "Skor" },
        { key: "traffic", label: "Trafik" },
        { key: "difficulty", label: "Zorluk" },
        { key: "actions", label: "Aksiyon" },
      ]}
      rows={(rows || []).map((o) => ({
        id: o.id,
        title: (o.title || "—").slice(0, 70),
        type: o.subtype || o.type,
        score: o.opportunity_score,
        traffic: o.traffic_score,
        difficulty: o.difficulty_score,
        actions: (o.action_plan || []).slice(0, 2).join(", "),
      }))}
      emptyText={emptyText}
    />
  );
}

export default function OpportunityEngine() {
  const [tab, setTab] = useState("dashboard");
  const [projectId, setProjectId] = useState(sessionStorage.getItem("opportunity_project_id") || "");
  const [networkId, setNetworkId] = useState("");
  const [location, setLocation] = useState("Kuşadası");
  const [seedKeyword, setSeedKeyword] = useState("");
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [quickData, setQuickData] = useState(null);
  const [plan, setPlan] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [exportPath, setExportPath] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [h, d, s] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/dashboard${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`),
        API.get(`${API_PREFIX}/settings`),
      ]);
      setHealth(h.data);
      setDash(d.data);
      setSettings(s.data.settings);
      setError("");
    } catch (e) {
      setError(apiError(e));
    }
  }, [projectId]);

  useEffect(() => { refresh(); }, [refresh]);

  const analyze = async () => {
    if (!projectId.trim()) { setError("Project ID gerekli"); return; }
    setLoading(true);
    setError("");
    sessionStorage.setItem("opportunity_project_id", projectId.trim());
    try {
      const res = await API.post(`${API_PREFIX}/analyze-project`, {
        project_id: projectId.trim(),
        network_id: networkId,
        location,
        seed_keyword: seedKeyword,
      });
      setOpportunities(res.data.opportunities || []);
      setMessage(`${res.data.opportunity_count} fırsat bulundu`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadTab = async (type) => {
    if (!projectId.trim() && type !== "authority") {
      setError("Önce Project ID girin ve analiz çalıştırın");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const endpoints = {
        keywords: `${API_PREFIX}/keywords?project_id=${encodeURIComponent(projectId)}`,
        entities: `${API_PREFIX}/entities?project_id=${encodeURIComponent(projectId)}`,
        geo: `${API_PREFIX}/geo?project_id=${encodeURIComponent(projectId)}&location=${encodeURIComponent(location)}`,
        authority: `${API_PREFIX}/authority?network_id=${encodeURIComponent(networkId)}`,
        ai: `${API_PREFIX}/ai?project_id=${encodeURIComponent(projectId)}`,
        quickwins: `${API_PREFIX}/quickwins?project_id=${encodeURIComponent(projectId)}`,
      };
      const res = await API.get(endpoints[type]);
      if (type === "quickwins") {
        setQuickData(res.data);
        setOpportunities(res.data.quick_wins || []);
      } else {
        setOpportunities(res.data.opportunities || []);
      }
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const oneClickPlan = async () => {
    if (!projectId.trim()) return;
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/one-click-plan`, {
        project_id: projectId.trim(),
        network_id: networkId,
      });
      setPlan(res.data.plan);
      setMessage(`Plan oluşturuldu: ${res.data.plan.plan_id} (uygulama yok)`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (reportType) => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, {
        project_id: projectId,
        report_type: reportType,
      });
      setExportPath(res.data.path);
      setMessage(`Rapor: ${res.data.path}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setLoading(true);
    try {
      await API.post(`${API_PREFIX}/settings`, settings);
      setMessage("Ayarlar kaydedildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const integrationOk = health?.ready !== false;

  return (
    <HiveShell
      title="🎯 Opportunity Engine"
      subtitle="Nerede trafik var? Kolay sıralama? Rakip zayıf? İçerik açığı?"
    >
      <HiveToolbar>
        <HiveBadge tone={integrationOk ? "low" : "high"}>
          Kaynaklar: {integrationOk ? "bağlı" : "eksik"}
        </HiveBadge>
        <HiveBtn variant="ghost" onClick={refresh}>Yenile</HiveBtn>
      </HiveToolbar>

      {!integrationOk && health?.integration_errors?.length > 0 && (
        <HiveAlert type="warn">
          Provider eksik: {health.integration_errors.slice(0, 3).join(" · ")}
        </HiveAlert>
      )}

      {message && <HiveAlert type="ok">{message}</HiveAlert>}
      {error && <HiveAlert type="err">{error}</HiveAlert>}

      <HivePanel>
        <div className="hm-form-row">
          <HiveField label="Project ID">
            <HiveInput value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="astro-proj-..." />
          </HiveField>
          <HiveField label="Network ID">
            <HiveInput value={networkId} onChange={(e) => setNetworkId(e.target.value)} />
          </HiveField>
          <HiveField label="Lokasyon">
            <HiveInput value={location} onChange={(e) => setLocation(e.target.value)} />
          </HiveField>
          <HiveField label="Seed keyword">
            <HiveInput value={seedKeyword} onChange={(e) => setSeedKeyword(e.target.value)} />
          </HiveField>
        </div>
        <HiveToolbar>
          <HiveBtn onClick={analyze} disabled={loading}>Analiz Et</HiveBtn>
          <HiveBtn variant="secondary" onClick={oneClickPlan} disabled={loading || !projectId}>
            One-Click Plan
          </HiveBtn>
        </HiveToolbar>
      </HivePanel>

      <HiveTabs tabs={TABS} active={tab} onChange={(id) => { setTab(id); if (id !== "dashboard" && id !== "reports" && id !== "settings") loadTab(id); }} />

      {tab === "dashboard" && dash && (
        <>
          <p className="hm-label-tip hm-panel-tip">
            Opportunity Score
            <HiveConceptTooltip conceptKey="opportunity_score" concepts={HIVE_CONCEPTS} />
            {" · "}
            Quick Win
            <HiveConceptTooltip conceptKey="quick_win" concepts={HIVE_CONCEPTS} />
          </p>
          <HiveStatGrid items={[
            ["Toplam fırsat", dash.total_opportunities ?? "—"],
            ["Quick wins", dash.quick_wins ?? "—"],
            ["Keyword", dash.by_type?.keyword ?? 0],
            ["Entity", dash.by_type?.entity ?? 0],
            ["GEO", dash.by_type?.geo ?? 0],
            ["AI", dash.by_type?.ai_overview ?? 0],
          ]} />
          <HivePanel title="En yüksek skorlu fırsatlar">
            <OppTable rows={dash.top_opportunities} emptyText="Analiz çalıştırın" />
          </HivePanel>
        </>
      )}

      {["keywords", "entities", "geo", "authority", "ai"].includes(tab) && (
        <HivePanel title={TABS.find((t) => t.id === tab)?.label}>
          <OppTable rows={opportunities} emptyText="Veri yok — analiz çalıştırın veya provider eksik" />
        </HivePanel>
      )}

      {tab === "quickwins" && (
        <>
          <HiveStatGrid items={[
            ["Quick wins", quickData?.counts?.quick_wins ?? "—"],
            ["Düşük rekabet", quickData?.counts?.low_competition ?? "—"],
            ["Yüksek etki", quickData?.counts?.high_impact ?? "—"],
          ]} />
          <HivePanel title="Quick Wins">
            <OppTable rows={quickData?.quick_wins} emptyText="Quick win yok" />
          </HivePanel>
          <HivePanel title="Low Competition">
            <OppTable rows={quickData?.low_competition} emptyText="—" />
          </HivePanel>
        </>
      )}

      {tab === "reports" && (
        <HivePanel title="Raporlar">
          <div className="hm-form-row" style={{ flexWrap: "wrap", gap: 8 }}>
            {REPORT_TYPES.map((r) => (
              <HiveBtn key={r.id} variant="outline" disabled={loading} onClick={() => exportReport(r.id)}>
                {r.label}
              </HiveBtn>
            ))}
          </div>
          {exportPath && <p className="hm-meta-line">Son export: {exportPath}</p>}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel title="Scoring eşikleri">
          <div className="hm-form-row">
            <HiveField label="Quick win threshold">
              <HiveInput type="number" value={settings.quick_win_threshold} onChange={(e) => setSettings({ ...settings, quick_win_threshold: Number(e.target.value) })} />
            </HiveField>
            <HiveField label="High impact threshold">
              <HiveInput type="number" value={settings.high_impact_threshold} onChange={(e) => setSettings({ ...settings, high_impact_threshold: Number(e.target.value) })} />
            </HiveField>
            <HiveField label="Max low competition difficulty">
              <HiveInput type="number" value={settings.low_competition_max_difficulty} onChange={(e) => setSettings({ ...settings, low_competition_max_difficulty: Number(e.target.value) })} />
            </HiveField>
          </div>
          <HiveBtn onClick={saveSettings} disabled={loading}>Kaydet</HiveBtn>
        </HivePanel>
      )}

      {plan && (
        <HivePanel title="One-Click Plan (uygulama yok)">
          <HiveCode>{JSON.stringify(plan, null, 2)}</HiveCode>
        </HivePanel>
      )}
    </HiveShell>
  );
}
