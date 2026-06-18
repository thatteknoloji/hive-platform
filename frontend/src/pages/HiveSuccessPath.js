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
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/success-path";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "progress", label: "Progress" },
  { id: "checklist", label: "Checklist" },
  { id: "recommendations", label: "Recommendations" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const ROLES = [
  { value: "seo_agency", label: "SEO Agency" },
  { value: "local_seo", label: "Local SEO" },
  { value: "directory_listing", label: "Directory / Listing" },
  { value: "publisher_network", label: "Publisher Network" },
  { value: "authority_builder", label: "Authority Builder" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  return e?.message || "Bilinmeyen hata";
}

function scoreTone(score) {
  if (score >= 75) return "success";
  if (score >= 40) return "warning";
  return "danger";
}

export default function HiveSuccessPath({ onNavigate }) {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [progress, setProgress] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [role, setRole] = useState("seo_agency");

  const go = (link) => {
    if (link && onNavigate) onNavigate(link);
  };

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [d, p, s] = await Promise.all([
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/progress`),
        API.get(`${API_PREFIX}/settings`),
      ]);
      setDash(d.data);
      setProgress(p.data);
      setSettings(s.data?.settings || s.data);
      setRole(s.data?.settings?.role || "seo_agency");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const recalculate = async () => {
    try {
      const r = await API.post(`${API_PREFIX}/recalculate`);
      setProgress(r.data);
      setMessage("Success Path yeniden hesaplandı");
      loadAll();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const saveSettings = async () => {
    try {
      const r = await API.post(`${API_PREFIX}/settings`, { role });
      setSettings(r.data?.settings);
      setMessage("Ayarlar kaydedildi — adım sırası güncellendi");
      loadAll();
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

  const score = progress?.completion_score ?? dash?.progress?.completion_score ?? 0;
  const steps = progress?.steps || dash?.progress?.steps || [];
  const badges = progress?.badges || dash?.badges || [];
  const recs = dash?.recommendations || [];

  return (
    <div className="hive-module hive-learn-page">
      <section className="hive-os-hero hive-learn-hero">
        <div className="hive-os-hero-glow" aria-hidden />
        <div className="hive-os-hero-top">
          <div>
            <span className="hive-os-hero-kicker">HIVE SEO OS · Activation</span>
            <h1 className="hive-os-hero-title">🚀 Success Path</h1>
            <p className="hive-os-hero-sub">
              Kayıt → İlk kampanya → İlk lead — tek başarı yolunda 100 puana ulaşın
            </p>
          </div>
          <HiveBtn variant="secondary" onClick={recalculate} disabled={loading}>
            Yeniden Hesapla
          </HiveBtn>
        </div>
        <div className="hive-wizard-progress">
          <div className="hive-wizard-progress-bar">
            <div className="hive-wizard-progress-fill" style={{ width: `${score}%` }} />
          </div>
          <div className="hive-wizard-progress-labels">
            <span>0</span>
            <span>Success Score: {score}/100</span>
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
                { label: "Success Score", value: `${score}`, variant: scoreTone(score) },
                { label: "Current Goal", value: progress?.current_goal || "—" },
                { label: "Steps Done", value: `${progress?.steps_completed?.length || 0}/${progress?.total_steps || 8}` },
                { label: "Badges", value: badges.length },
              ]}
            />
            <HivePanel title="Next Action">
              <p>{progress?.next_action || "—"}</p>
              <p className="hive-muted">Tahmini süre: {progress?.estimated_time_to_success || "—"}</p>
              {recs[0] && (
                <HiveBtn onClick={() => go(recs[0].deep_link || recs[0].module_id)}>
                  {recs[0].title} → Modüle Git
                </HiveBtn>
              )}
            </HivePanel>
            {badges.length > 0 && (
              <HivePanel title="Rozetler">
                <div className="hive-badge-row">
                  {badges.map((b) => (
                    <HiveBadge key={b.id} tone="success">{b.icon || "🏅"} {b.title || b.id}</HiveBadge>
                  ))}
                </div>
              </HivePanel>
            )}
          </>
        )}

        {tab === "progress" && (
          <HivePanel title="Progress Overview">
            <HiveStatGrid
              stats={[
                { label: "Completion", value: `${score}%` },
                { label: "Role", value: ROLES.find((r) => r.value === role)?.label || role },
                { label: "Wizard", value: progress?.wizard_completed ? "✓" : "Bekliyor" },
                { label: "Path", value: progress?.path_completed_at ? "Tamamlandı" : "Devam" },
              ]}
            />
            <p><strong>Hedef:</strong> {progress?.current_goal}</p>
            <p><strong>Sıradaki:</strong> {progress?.next_action}</p>
          </HivePanel>
        )}

        {tab === "checklist" && (
          <HiveSection title="Başarı Adımları">
            {steps.map((step) => (
              <div key={step.step_id} className={`hive-wizard-step ${step.completed ? "done" : ""}`}>
                <div className="hive-wizard-step-head">
                  <span>{step.order}. {step.title}</span>
                  <HiveBadge tone={step.completed ? "success" : "warning"}>
                    {step.completed ? "✓" : `${step.points} puan`}
                  </HiveBadge>
                </div>
                <p className="hive-muted">{step.description}</p>
                {!step.completed && (
                  <div className="hive-wizard-step-actions">
                    <HiveBtn size="sm" onClick={() => go(step.deep_link || step.module_id)}>
                      Modüle Git
                    </HiveBtn>
                    {step.academy_guide && (
                      <HiveBtn size="sm" variant="secondary" onClick={() => go("hive_academy")}>
                        Academy Dersi
                      </HiveBtn>
                    )}
                  </div>
                )}
              </div>
            ))}
          </HiveSection>
        )}

        {tab === "recommendations" && (
          <HiveSection title="Öneriler">
            {recs.length === 0 && <p>Tüm adımlar tamam — Mission Control'e geçin.</p>}
            {recs.map((r, i) => (
              <HivePanel key={r.step_id || i} title={r.title}>
                <p>{r.reason}</p>
                <p className="hive-muted">~{r.estimated_time}</p>
                <HiveBtn size="sm" onClick={() => go(r.deep_link || r.module_id)}>Başla</HiveBtn>
                {r.academy_guide && (
                  <HiveBtn size="sm" variant="secondary" onClick={() => go("hive_academy")}>Academy</HiveBtn>
                )}
              </HivePanel>
            ))}
          </HiveSection>
        )}

        {tab === "reports" && (
          <HivePanel title="Export Report">
            <p>Success Path ilerleme raporunu JSON olarak dışa aktarın.</p>
            <HiveBtn onClick={exportReport}>Rapor Oluştur</HiveBtn>
            {exportPath && <p className="hive-muted">{exportPath}</p>}
          </HivePanel>
        )}

        {tab === "settings" && (
          <HivePanel title="Settings">
            <HiveField label="Role Flow">
              <select className="hive-input" value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </HiveField>
            <p className="hive-muted">
              {dash?.role_flow?.description || "Rol seçimi adım önceliğini değiştirir."}
            </p>
            <HiveBtn onClick={saveSettings}>Kaydet</HiveBtn>
          </HivePanel>
        )}
      </HiveShell>
    </div>
  );
}
