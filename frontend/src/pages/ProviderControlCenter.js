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

const API_PREFIX = "/api/providers";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "providers", label: "Providers" },
  { id: "health", label: "Health" },
  { id: "errors", label: "Errors" },
  { id: "quota", label: "Quota" },
  { id: "activity", label: "Recent Activity" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

function statusVariant(s) {
  if (s === "healthy") return "ok";
  if (s === "warning" || s === "not_configured") return "warn";
  return "error";
}

function scoreVariant(s) {
  const n = Number(s) || 0;
  if (n >= 75) return "ok";
  if (n >= 50) return "warn";
  return "error";
}

function tokensMasked(meta) {
  const tokens = meta?.tokens?.tokens_masked || [];
  return tokens.length ? tokens.join(", ") : "—";
}

export default function ProviderControlCenter() {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [providers, setProviders] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [selectedProvider, setSelectedProvider] = useState("");

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, d, l, s] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/list`),
        API.get(`${API_PREFIX}/settings`),
      ]);
      setHealth(h.data);
      setDash(d.data);
      setProviders(l.data?.providers || []);
      setSettings(s.data?.settings || s.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  const handleCheckAll = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post(`${API_PREFIX}/check`, {});
      setProviders(res.data?.providers || []);
      setMessage(`Sağlık kontrolü tamam: ${res.data?.count ?? 0} provider`);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleCheckOne = async (name) => {
    if (!name) return;
    setLoading(true);
    try {
      await API.post(`${API_PREFIX}/check`, { provider: name });
      setMessage(`${name} kontrol edildi`);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
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

  const summary = dash?.summary || {};
  const errors = dash?.errors || [];
  const activity = dash?.recent_activity || [];
  const alerts = dash?.alerts || [];

  const providerRows = providers.map((p) => ({
    ...p,
    tokens: tokensMasked(p.metadata),
    module: p.metadata?.module || "—",
  }));

  return (
    <HiveShell
      title="Provider Control Center"
      subtitle="Dış servis gözlem — keşif, sağlık, token, quota ve son işlem durumu"
      loading={loading}
    >
      {error && <HiveAlert variant="error">{error}</HiveAlert>}
      {message && <HiveAlert variant="ok">{message}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <HivePanel>
          <HiveStatGrid
            items={[
              { label: "Provider Health", value: summary.health_score ?? 0, variant: scoreVariant(summary.health_score) },
              { label: "Connected", value: summary.connected ?? 0, variant: "ok" },
              { label: "Configured", value: summary.configured ?? 0, variant: "info" },
              { label: "Failed / Critical", value: summary.failed ?? 0, variant: summary.failed > 0 ? "error" : "ok" },
              { label: "Healthy", value: summary.healthy ?? 0, variant: "ok" },
              { label: "Warning", value: summary.warning ?? 0, variant: summary.warning > 0 ? "warn" : "ok" },
            ]}
          />
          <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <HiveBtn onClick={handleCheckAll}>Tüm Providerları Kontrol Et</HiveBtn>
            <HiveBtn variant="secondary" onClick={() => loadCore()}>Yenile</HiveBtn>
          </div>
          {dash?.last_full_check && (
            <p style={{ marginTop: 12, opacity: 0.75 }}>Son tam kontrol: {dash.last_full_check}</p>
          )}
          {alerts.length > 0 && (
            <>
              <h4 style={{ marginTop: 20 }}>Provider Alerts</h4>
              <HiveTable
                columns={[
                  { key: "provider", label: "Provider" },
                  { key: "type", label: "Type" },
                  { key: "message", label: "Message" },
                  { key: "at", label: "At" },
                ]}
                rows={alerts}
              />
            </>
          )}
        </HivePanel>
      )}

      {tab === "providers" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "label", label: "Provider" },
              { key: "status", label: "Status", render: (v) => <HiveStatusBadge variant={statusVariant(v)}>{v}</HiveStatusBadge> },
              { key: "connected", label: "Connected", render: (v) => (v ? "Yes" : "No") },
              { key: "configured", label: "Configured", render: (v) => (v ? "Yes" : "No") },
              { key: "health_score", label: "Score" },
              { key: "tokens", label: "Token (masked)" },
              { key: "module", label: "Source Module" },
              { key: "last_check", label: "Last Check" },
            ]}
            rows={providerRows}
          />
        </HivePanel>
      )}

      {tab === "health" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "label", label: "Provider" },
              { key: "status", label: "Status", render: (v) => <HiveStatusBadge variant={statusVariant(v)}>{v}</HiveStatusBadge> },
              { key: "health_score", label: "Health Score", render: (v) => <HiveStatusBadge variant={scoreVariant(v)}>{v}</HiveStatusBadge> },
              { key: "connected", label: "Connected", render: (v) => (v ? "✓" : "—") },
              { key: "last_success", label: "Last Success" },
              { key: "last_check", label: "Last Check" },
            ]}
            rows={providerRows}
          />
        </HivePanel>
      )}

      {tab === "errors" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "label", label: "Provider" },
              { key: "status", label: "Status", render: (v) => <HiveStatusBadge variant={statusVariant(v)}>{v}</HiveStatusBadge> },
              { key: "last_error", label: "Last Error" },
              { key: "last_check", label: "Last Check" },
            ]}
            rows={errors.length ? errors : providerRows.filter((p) => p.last_error)}
          />
        </HivePanel>
      )}

      {tab === "quota" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "label", label: "Provider" },
              { key: "quota", label: "Quota / Usage", render: (v) => JSON.stringify(v || {}) },
            ]}
            rows={providerRows}
          />
        </HivePanel>
      )}

      {tab === "activity" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "type", label: "Action" },
              { key: "provider", label: "Provider" },
              { key: "status", label: "Status" },
              { key: "title", label: "Title" },
              { key: "message", label: "Message" },
              { key: "at", label: "At" },
            ]}
            rows={activity}
          />
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel>
          <p>Provider durum raporlarını JSON olarak dışa aktarın.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            <HiveBtn onClick={() => handleExport("overview")}>Overview</HiveBtn>
            <HiveBtn variant="secondary" onClick={() => handleExport("providers")}>Providers</HiveBtn>
            <HiveBtn variant="secondary" onClick={() => handleExport("health")}>Health</HiveBtn>
          </div>
          {exportPath && <p style={{ marginTop: 12 }}>Kayıt: {exportPath}</p>}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel>
          <HiveField label="Modül aktif">
            <HiveCheck
              checked={!!settings.enabled}
              onChange={(v) => setSettings({ ...settings, enabled: v })}
              label="Provider Control Center etkin"
            />
          </HiveField>
          <HiveField label="Otomatik kontrol aralığı (dk)">
            <HiveInput
              type="number"
              value={settings.auto_check_interval_minutes ?? 30}
              onChange={(e) => setSettings({ ...settings, auto_check_interval_minutes: Number(e.target.value) })}
            />
          </HiveField>
          <HiveField label="Kritik alert">
            <HiveCheck
              checked={!!settings.alert_on_critical}
              onChange={(v) => setSettings({ ...settings, alert_on_critical: v })}
              label="Kritik provider hatalarında alert"
            />
          </HiveField>
          <HiveField label="Disconnect alert">
            <HiveCheck
              checked={!!settings.alert_on_disconnect}
              onChange={(v) => setSettings({ ...settings, alert_on_disconnect: v })}
              label="Bağlantı kopmasında alert"
            />
          </HiveField>
          <HiveField label="Tek provider kontrol">
            <HiveInput
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              placeholder="ör. github_pages"
            />
            <HiveBtn variant="secondary" onClick={() => handleCheckOne(selectedProvider)} style={{ marginTop: 8 }}>
              Kontrol Et
            </HiveBtn>
          </HiveField>
          <HiveBtn onClick={handleSaveSettings} style={{ marginTop: 16 }}>Kaydet</HiveBtn>
        </HivePanel>
      )}

      {health && (
        <p style={{ marginTop: 16, fontSize: 12, opacity: 0.6 }}>
          Module: {health.module} · Providers: {health.providers_total} · Publishes: {health.publishes ? "yes" : "no"}
        </p>
      )}
    </HiveShell>
  );
}
