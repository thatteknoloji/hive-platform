import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveBtn,
  HiveBadge,
  HiveSection,
  HiveField,
  HiveCheck,
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/readiness";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "readiness", label: "Readiness" },
  { id: "blockers", label: "Blockers" },
  { id: "warnings", label: "Warnings" },
  { id: "providers", label: "Providers" },
  { id: "audit", label: "Audit" },
  { id: "queues", label: "Queues" },
  { id: "security", label: "Security" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const MODE_LABELS = {
  development: "Development",
  alpha: "Alpha",
  beta: "Beta",
  production_ready: "Production Ready",
  enterprise_ready: "Enterprise Ready",
};

function apiError(e) {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : e?.message || "İstek başarısız";
}

function modeTone(mode) {
  if (mode === "enterprise_ready" || mode === "production_ready") return "success";
  if (mode === "beta" || mode === "alpha") return "warning";
  return "danger";
}

function scoreTone(s) {
  const n = Number(s) || 0;
  if (n >= 80) return "ok";
  if (n >= 60) return "warn";
  return "error";
}

export default function ProductionReadinessEngine() {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [exportPath, setExportPath] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [d, s] = await Promise.all([
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/settings`),
      ]);
      setDash(d.data);
      setSettings(s.data?.settings || s.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const calculate = async () => {
    try {
      const r = await API.post(`${API_PREFIX}/calculate`);
      setDash((prev) => ({ ...prev, readiness: r.data }));
      setMessage("Readiness yeniden hesaplandı");
      load();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const exportReport = async () => {
    try {
      const r = await API.post(`${API_PREFIX}/export-report`, { report_type: "overview" });
      setExportPath(r.data?.path || "Rapor oluşturuldu");
      setMessage("Rapor dışa aktarıldı");
    } catch (e) {
      setError(apiError(e));
    }
  };

  const saveSettings = async () => {
    try {
      await API.post(`${API_PREFIX}/settings`, settings);
      setMessage("Ayarlar kaydedildi");
      load();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const r = dash?.readiness || {};
  const components = r.score_components || {};
  const blockers = r.blockers || [];
  const warnings = r.warnings || [];

  return (
    <div className="hive-module hive-learn-page">
      <section className="hive-os-hero hive-learn-hero">
        <div className="hive-os-hero-glow" aria-hidden />
        <div className="hive-os-hero-top">
          <div>
            <span className="hive-os-hero-kicker">HIVE SEO OS · Launch</span>
            <h1 className="hive-os-hero-title">🚀 Production Readiness</h1>
            <p className="hive-os-hero-sub">Canlı kullanıma hazırlık skoru — publish/deploy yapmaz, sadece ölçer</p>
          </div>
          <HiveBtn variant="secondary" onClick={calculate} disabled={loading}>
            Hesapla
          </HiveBtn>
        </div>
        <div className="hive-wizard-progress">
          <div className="hive-wizard-progress-bar">
            <div className="hive-wizard-progress-fill" style={{ width: `${r.overall_score || 0}%` }} />
          </div>
          <div className="hive-wizard-progress-labels">
            <span>0</span>
            <span>{r.overall_score || 0}/100 — {MODE_LABELS[r.launch_mode] || r.launch_mode}</span>
            <span>100</span>
          </div>
        </div>
      </section>

      <HiveShell loading={loading}>
        {error && <HiveAlert type="error">{error}</HiveAlert>}
        {message && <HiveAlert type="success">{message}</HiveAlert>}

        <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

        {tab === "dashboard" && (
          <>
            <HiveStatGrid
              stats={[
                { label: "Overall Score", value: `${r.overall_score || 0}`, variant: scoreTone(r.overall_score) },
                { label: "Launch Mode", value: MODE_LABELS[r.launch_mode] || "—" },
                { label: "Blockers", value: blockers.length, variant: blockers.length ? "error" : "ok" },
                { label: "Warnings", value: warnings.length, variant: warnings.length ? "warn" : "ok" },
              ]}
            />
            <HivePanel title="Recommendation">
              <p>{r.recommendation || "—"}</p>
              <p className="hive-muted">Passed checks: {(r.passed_checks || []).length}</p>
            </HivePanel>
          </>
        )}

        {tab === "readiness" && (
          <HivePanel title="Score Components">
            <div className="hive-stat-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(140px,1fr))", gap: "0.75rem" }}>
              {Object.entries(components).map(([k, v]) => (
                <div key={k} className="hive-stat-cell">
                  <span className="hive-muted">{k.replace(/_/g, " ")}</span>
                  <strong>{v}</strong>
                </div>
              ))}
            </div>
            <h4 style={{ marginTop: "1rem" }}>Launch Modes</h4>
            <ul>
              <li>0–39 Development</li>
              <li>40–59 Alpha</li>
              <li>60–79 Beta</li>
              <li>80–89 Production Ready (blocker yoksa)</li>
              <li>90–100 Enterprise Ready</li>
            </ul>
          </HivePanel>
        )}

        {tab === "blockers" && (
          <HiveSection title={`Blockers (${blockers.length})`}>
            {blockers.length === 0 && <p>Blocker yok ✓</p>}
            {blockers.map((b, i) => (
              <HivePanel key={i} title={b.title}>
                <HiveBadge tone="danger">{b.type}</HiveBadge>
                <p className="hive-muted">{b.module}</p>
              </HivePanel>
            ))}
          </HiveSection>
        )}

        {tab === "warnings" && (
          <HiveSection title={`Warnings (${warnings.length})`}>
            {warnings.length === 0 && <p>Uyarı yok</p>}
            {warnings.map((w, i) => (
              <HivePanel key={i} title={w.title}>
                <HiveBadge tone="warning">{w.type}</HiveBadge>
              </HivePanel>
            ))}
          </HiveSection>
        )}

        {tab === "providers" && (
          <HivePanel title="Provider Score">
            <p>Score: <strong>{components.provider ?? "—"}</strong></p>
            <p className="hive-muted">Kaynak: Provider Control Center — health {dash?.sources_summary?.provider_health ?? "—"}</p>
          </HivePanel>
        )}

        {tab === "audit" && (
          <HivePanel title="Audit Score">
            <p>Score: <strong>{components.audit ?? "—"}</strong></p>
            <p className="hive-muted">Kaynak: HIVE Audit Engine — {dash?.sources_summary?.audit_score ?? "—"}</p>
          </HivePanel>
        )}

        {tab === "queues" && (
          <HivePanel title="Queue Score">
            <p>Score: <strong>{components.queue ?? "—"}</strong></p>
            <p className="hive-muted">Action Orchestrator + Publisher kuyrukları</p>
          </HivePanel>
        )}

        {tab === "security" && (
          <HivePanel title="Security Score">
            <p>Score: <strong>{components.security ?? "—"}</strong></p>
            <p className="hive-muted">Critical audit + provider riskleri</p>
          </HivePanel>
        )}

        {tab === "reports" && (
          <HivePanel title="Export">
            <HiveBtn onClick={exportReport}>Rapor Dışa Aktar</HiveBtn>
            {exportPath && <p className="hive-muted">{exportPath}</p>}
          </HivePanel>
        )}

        {tab === "settings" && settings && (
          <HivePanel title="Settings">
            <HiveField label="Enabled">
              <HiveCheck checked={settings.enabled} onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })} />
            </HiveField>
            <HiveField label="Min Production Score">
              <input className="hive-input" type="number" value={settings.min_production_score} onChange={(e) => setSettings({ ...settings, min_production_score: Number(e.target.value) })} />
            </HiveField>
            <HiveField label="Block on Critical Audit">
              <HiveCheck checked={settings.block_on_critical_audit} onChange={(e) => setSettings({ ...settings, block_on_critical_audit: e.target.checked })} />
            </HiveField>
            <HiveBtn onClick={saveSettings}>Kaydet</HiveBtn>
          </HivePanel>
        )}
      </HiveShell>
    </div>
  );
}
