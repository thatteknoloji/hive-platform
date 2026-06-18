import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HivePanel,
  HiveBtn,
  HiveBadge,
  HiveSection,
} from "../components/HiveModuleUI";
import HiveApiErrorCard from "../components/HiveApiErrorCard";
import { formatHiveApiError } from "../utils/hiveApiErrors";

const API_PREFIX = "/api/first-run";

function apiError(e, endpoint = `${API_PREFIX}/status`) {
  return formatHiveApiError(e, endpoint);
}

function StepStatusBadge({ step }) {
  if (step.completed) return <HiveBadge tone="success">✓ Tamam</HiveBadge>;
  if (step.status === "connect_required") return <HiveBadge tone="danger">🔗 Bağlantı gerekli</HiveBadge>;
  if (step.auto_detected) return <HiveBadge tone="info">Otomatik algılandı</HiveBadge>;
  return <HiveBadge tone="warning">Bekliyor</HiveBadge>;
}

export default function FirstRunWizard({ onNavigate }) {
  const [status, setStatus] = useState(null);
  const [expandedStep, setExpandedStep] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const go = (step) => {
    if (step.mesh_tab) {
      sessionStorage.setItem("hive_mesh_tab", step.mesh_tab);
      window.dispatchEvent(new Event("hive-mesh-tab"));
    }
    onNavigate?.(step.deep_link || step.module_id);
  };

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.get(`${API_PREFIX}/status`);
      setStatus(res.data);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const completeStep = async (stepId) => {
    try {
      const res = await API.post(`${API_PREFIX}/complete-step`, { step_id: stepId, manual: true });
      setStatus(res.data);
      setMessage(`Adım tamamlandı: ${stepId}`);
    } catch (err) {
      setError(apiError(err));
    }
  };

  const reset = async () => {
    try {
      const res = await API.post(`${API_PREFIX}/reset`);
      setStatus(res.data);
      setMessage("Wizard sıfırlandı");
    } catch (err) {
      setError(apiError(err));
    }
  };

  const pct = status?.progress_percent ?? 0;
  const bucket = status?.progress_bucket ?? 0;
  const nextStep = status?.steps?.find((s) => !s.completed);
  const connectRequired = (status?.steps || []).filter((s) => s.status === "connect_required");

  return (
    <div className="hive-module hive-learn-page">
      <section className="hive-os-hero hive-learn-hero">
        <div className="hive-os-hero-glow" aria-hidden />
        <div className="hive-os-hero-top">
          <div>
            <span className="hive-os-hero-kicker">HIVE SEO OS · Onboarding</span>
            <h1 className="hive-os-hero-title">🚀 First Run Wizard</h1>
            <p className="hive-os-hero-sub">
              8 adımda HIVE SEO OS kurulumu — gerçek API bağlantıları otomatik doğrulanır
            </p>
          </div>
        </div>
        <div className="hive-wizard-progress">
          <div className="hive-wizard-progress-bar">
            <div className="hive-wizard-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <div className="hive-wizard-progress-labels">
            {[0, 25, 50, 75, 100].map((m) => (
              <span key={m} className={bucket >= m && m > 0 ? "active" : pct >= m ? "active" : ""}>{m}%</span>
            ))}
          </div>
          <div className="hive-wizard-progress-current">
            {pct}% tamamlandı · {status?.completed_count ?? 0}/{status?.total_steps ?? 8} adım
          </div>
        </div>
      </section>

      <HiveShell
        title=""
        subtitle=""
        actions={
          <>
            <HiveBtn variant="secondary" onClick={reset}>Sıfırla</HiveBtn>
            <HiveBtn onClick={refresh} disabled={loading}>{loading ? "…" : "↻ Kontrol"}</HiveBtn>
          </>
        }
      >
        {error && <HiveApiErrorCard errorInfo={error} />}
        {message && <HiveAlert type="success">{message}</HiveAlert>}
        {status?.wizard_completed && (
          <HiveAlert type="success">🎉 Wizard tamamlandı! Mission Control&apos;a geçebilirsiniz.</HiveAlert>
        )}
        {connectRequired.length > 0 && !status?.wizard_completed && (
          <HiveAlert type="warning">
            {connectRequired.length} adımda bağlantı eksik — detayları genişleterek .env ve OAuth adımlarını tamamlayın.
          </HiveAlert>
        )}

        <HiveSection title="Kurulum Adımları">
          <ol className="hive-wizard-steps">
            {(status?.steps || []).map((step) => (
              <li key={step.step_id} className={`hive-wizard-step ${step.completed ? "done" : ""} ${step.status === "connect_required" ? "connect-required" : ""}`}>
                <div className="hive-wizard-step-head">
                  <span className="hive-os-mission-order">{step.order}</span>
                  <div className="hive-wizard-step-info">
                    <strong>{step.title}</strong>
                    <p>{step.description}</p>
                    {step.success_criteria && (
                      <span className="hive-wizard-criteria">✓ Kriter: {step.success_criteria}</span>
                    )}
                  </div>
                  <StepStatusBadge step={step} />
                </div>

                <div className="hive-wizard-step-actions">
                  <HiveBtn size="sm" onClick={() => go(step)}>Modüle Git</HiveBtn>
                  <HiveBtn size="sm" variant="secondary" onClick={() => setExpandedStep(expandedStep === step.step_id ? null : step.step_id)}>
                    {expandedStep === step.step_id ? "Detay Gizle" : "Detay Göster"}
                  </HiveBtn>
                  {!step.completed && (
                    <HiveBtn size="sm" variant="ghost" onClick={() => completeStep(step.step_id)}>Tamamladım</HiveBtn>
                  )}
                  {step.academy_guide && (
                    <HiveBtn size="sm" variant="ghost" onClick={() => onNavigate?.("hive_academy")}>📖 Rehber</HiveBtn>
                  )}
                </div>

                {expandedStep === step.step_id && (
                  <div className="hive-wizard-step-detail">
                    {step.instructions?.length > 0 && (
                      <div>
                        <h5>Adım adım talimatlar</h5>
                        <ol>
                          {step.instructions.map((inst, i) => <li key={i}>{inst}</li>)}
                        </ol>
                      </div>
                    )}
                    {step.env_vars?.length > 0 && (
                      <div className="hive-wizard-env">
                        <h5>.env anahtarları</h5>
                        <ul>
                          {step.env_vars.map((ev) => (
                            <li key={ev.key}><code>{ev.key}</code> — {ev.description}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {step.troubleshooting?.length > 0 && (
                      <div className="hive-wizard-troubleshoot">
                        <h5>Sorun giderme</h5>
                        <ul>
                          {step.troubleshooting.map((t, i) => <li key={i}>{t}</li>)}
                        </ul>
                      </div>
                    )}
                    {step.check_error && (
                      <p className="hive-wizard-check-error">Kontrol hatası: {step.check_error}</p>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </HiveSection>

        <HivePanel title="Sonraki adım">
          {nextStep ? (
            <>
              <p><strong>{nextStep.title}</strong> — {nextStep.description}</p>
              {nextStep.status === "connect_required" && (
                <p className="hive-wizard-connect-hint">
                  Bu adım için bağlantı gerekli. &quot;Detay Göster&quot; ile .env checklist&apos;ine bakın.
                </p>
              )}
              <HiveBtn onClick={() => go(nextStep)}>Devam Et →</HiveBtn>
            </>
          ) : (
            <p>Tüm adımlar tamamlandı. <HiveBtn size="sm" onClick={() => onNavigate?.("mission_control_center")}>Mission Control →</HiveBtn></p>
          )}
        </HivePanel>
      </HiveShell>
    </div>
  );
}
