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
  HiveSection,
} from "../components/HiveModuleUI";
import { HivePanelHero, RevenueFunnelOps } from "../components/HiveOSVisualizations";

const API_PREFIX = "/api/revenue-leads";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "leads", label: "Leads" },
  { id: "sources", label: "Sources" },
  { id: "keywords", label: "Keywords" },
  { id: "funnel", label: "Funnel" },
  { id: "publisher", label: "Publisher Impact" },
  { id: "authority", label: "Authority Impact" },
  { id: "settings", label: "Settings" },
  { id: "reports", label: "Reports" },
];

function apiError(e) {
  return e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

function statusVariant(s) {
  if (s === "converted") return "ok";
  if (s === "lost" || s === "invalid") return "error";
  if (s === "qualified") return "warn";
  return "neutral";
}

export default function RevenueLeadEngine() {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [settings, setSettings] = useState(null);
  const [leads, setLeads] = useState([]);
  const [sources, setSources] = useState([]);
  const [keywords, setKeywords] = useState([]);
  const [funnel, setFunnel] = useState(null);
  const [publisher, setPublisher] = useState(null);
  const [authority, setAuthority] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [d, s, f] = await Promise.all([
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/funnel`).catch(() => ({ data: null })),
      ]);
      setDash(d.data);
      setSettings(s.data?.settings || s.data);
      if (f.data) setFunnel(f.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    const loadTab = async () => {
      try {
        if (tab === "leads") {
          const r = await API.get(`${API_PREFIX}/leads`, { params: { limit: 100 } });
          setLeads(r.data?.leads || []);
        } else if (tab === "sources") {
          const r = await API.get(`${API_PREFIX}/sources`);
          setSources(r.data?.sources || []);
        } else if (tab === "keywords") {
          const r = await API.get(`${API_PREFIX}/keywords`);
          setKeywords(r.data?.keywords || []);
        } else if (tab === "funnel") {
          const r = await API.get(`${API_PREFIX}/funnel`);
          setFunnel(r.data);
        } else if (tab === "publisher") {
          const r = await API.get(`${API_PREFIX}/publisher-impact`);
          setPublisher(r.data);
        } else if (tab === "authority") {
          const r = await API.get(`${API_PREFIX}/authority-impact`);
          setAuthority(r.data);
        }
      } catch (e) {
        setError(apiError(e));
      }
    };
    loadTab();
  }, [tab]);

  const updateStatus = async (leadId, status) => {
    try {
      await API.post(`${API_PREFIX}/lead/${leadId}/status`, { status });
      setMessage(`Lead ${leadId} → ${status}`);
      const r = await API.get(`${API_PREFIX}/leads`, { params: { limit: 100 } });
      setLeads(r.data?.leads || []);
      await loadCore();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const saveSettings = async () => {
    setLoading(true);
    try {
      const r = await API.post(`${API_PREFIX}/settings`, settings);
      setSettings(r.data?.settings);
      setMessage("Ayarlar kaydedildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (type) => {
    try {
      const r = await API.post(`${API_PREFIX}/export-report`, { report_type: type });
      setExportPath(r.data?.path || "");
      setMessage(`Rapor: ${type}`);
    } catch (e) {
      setError(apiError(e));
    }
  };

  const leadCols = [
    { key: "lead_id", label: "ID" },
    { key: "timestamp", label: "Zaman" },
    { key: "lead_type", label: "Tip" },
    { key: "keyword", label: "Keyword" },
    { key: "source_domain", label: "Domain" },
    { key: "status", label: "Durum", render: (v) => <HiveStatusBadge status={statusVariant(v)} label={v} /> },
    { key: "estimated_value", label: "Değer" },
    {
      key: "actions",
      label: "",
      render: (_, row) => (
        <span className="hive-inline-actions">
          {row.status === "new" && (
            <>
              <HiveBtn size="sm" onClick={() => updateStatus(row.lead_id, "qualified")}>Qualify</HiveBtn>
              <HiveBtn size="sm" variant="ghost" onClick={() => updateStatus(row.lead_id, "converted")}>Convert</HiveBtn>
            </>
          )}
        </span>
      ),
    },
  ];

  const funnelData = funnel || {
    visits: dash?.visits ?? 0,
    clicks: dash?.clicks ?? 0,
    leads: dash?.total_leads ?? 0,
    qualified: dash?.qualified ?? 0,
    converted: dash?.converted ?? 0,
    conversion_rate: dash?.conversion_rate ?? 0,
    estimated_revenue: dash?.estimated_revenue ?? 0,
  };

  return (
    <div className="hive-module hive-os-command-center">
      <HivePanelHero
        kicker="Revenue OS"
        title="Revenue / Lead Engine"
        subtitle="SEO ve GEO çalışmalarının ticari sonucunu ölçer — lead → qualified → converted"
      />
    <HiveShell title="" subtitle="" loading={loading}>
      {error && <HiveAlert type="error">{error}</HiveAlert>}
      {message && <HiveAlert type="success">{message}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <>
          <div className="hive-viz-grid hive-ops-primary">
            <RevenueFunnelOps dash={dash} funnel={funnelData} />
          </div>
          {(dash?.recent_leads || []).length > 0 && (
            <div className="hive-war-lead-list">
              {(dash.recent_leads || []).slice(0, 6).map((l, i) => (
                <div key={l.id || i} className="hive-war-lead-row">
                  <span>{l.source || l.page || l.email || "Lead"}</span>
                  <span className="hive-pill hive-pill-neutral hive-pill-xs">{l.status || l.quality || "new"}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "leads" && <HivePanel><HiveTable columns={leadCols} rows={leads} emptyText="Lead yok" /></HivePanel>}

      {tab === "sources" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "source_module", label: "Kaynak" },
              { key: "leads", label: "Leads" },
              { key: "converted", label: "Converted" },
              { key: "conversion_rate", label: "Conv %" },
              { key: "estimated_revenue", label: "Est. Revenue" },
              { key: "avg_commercial_score", label: "Commercial" },
            ]}
            rows={sources}
            emptyText="Kaynak verisi yok"
          />
        </HivePanel>
      )}

      {tab === "keywords" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "keyword", label: "Keyword" },
              { key: "leads", label: "Leads" },
              { key: "converted", label: "Converted" },
              { key: "estimated_revenue", label: "Est. Revenue" },
              { key: "avg_quality_score", label: "Quality" },
            ]}
            rows={keywords}
            emptyText="Keyword verisi yok"
          />
        </HivePanel>
      )}

      {tab === "funnel" && funnel && (
        <HivePanel>
          <div className="hive-viz-grid">
            <RevenueFunnelOps dash={dash} funnel={funnel} />
          </div>
          <HiveStatGrid
            stats={[
              { label: "Visits", value: funnel.visits ?? 0 },
              { label: "Clicks", value: funnel.clicks ?? 0 },
              { label: "Leads", value: funnel.leads ?? 0 },
              { label: "Qualified", value: funnel.qualified ?? 0 },
              { label: "Converted", value: funnel.converted ?? 0 },
              { label: "Est. Revenue", value: funnel.estimated_revenue ?? 0 },
              { label: "Conv. Rate %", value: funnel.conversion_rate ?? 0 },
            ]}
          />
        </HivePanel>
      )}

      {tab === "publisher" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "channel", label: "Channel" },
              { key: "leads", label: "Leads" },
              { key: "converted", label: "Converted" },
              { key: "estimated_revenue", label: "Est. Revenue" },
            ]}
            rows={publisher?.channels || []}
            emptyText="Publisher lead verisi yok"
          />
        </HivePanel>
      )}

      {tab === "authority" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "domain", label: "Domain" },
              { key: "module", label: "Module" },
              { key: "leads", label: "Leads" },
              { key: "estimated_revenue", label: "Est. Revenue" },
            ]}
            rows={authority?.domains || []}
            emptyText="Authority lead verisi yok"
          />
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel>
          <HiveSection title="Tracking & Güvenlik">
            <HiveCheck checked={!!settings.enabled} onChange={(v) => setSettings({ ...settings, enabled: v })} label="Engine aktif" />
            <HiveCheck checked={!!settings.tracking_secret_required} onChange={(v) => setSettings({ ...settings, tracking_secret_required: v })} label="Tracking secret zorunlu" />
            <HiveCheck checked={!!settings.store_ip_hash} onChange={(v) => setSettings({ ...settings, store_ip_hash: v })} label="IP hash sakla (KVKK)" />
            <HiveField label="default_lead_value">
              <HiveInput type="number" value={settings.default_lead_value ?? 100} onChange={(e) => setSettings({ ...settings, default_lead_value: Number(e.target.value) })} />
            </HiveField>
            <HiveField label="spam_window_seconds">
              <HiveInput type="number" value={settings.spam_window_seconds ?? 30} onChange={(e) => setSettings({ ...settings, spam_window_seconds: Number(e.target.value) })} />
            </HiveField>
            <p className="hive-muted">{settings.gdpr_note}</p>
            <HiveBtn onClick={saveSettings} disabled={loading}>Kaydet</HiveBtn>
          </HiveSection>
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel>
          {["overview", "leads", "sources", "keywords", "funnel", "publisher", "authority"].map((t) => (
            <HiveBtn key={t} variant="ghost" onClick={() => exportReport(t)} style={{ marginRight: 8 }}>{t}</HiveBtn>
          ))}
          {exportPath && <p className="hive-muted">{exportPath}</p>}
        </HivePanel>
      )}
    </HiveShell>
    </div>
  );
}
