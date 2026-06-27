import React from "react";
import { HivePanel, HiveBtn } from "./HiveModuleUI";

const STATUS_LABEL = {
  completed: "Tamamlandı",
  in_progress: "Devam ediyor",
  not_started: "Başlanmadı",
  blocked: "Engelli",
};

const STATUS_CLASS = {
  completed: "cj-step--completed",
  in_progress: "cj-step--progress",
  not_started: "cj-step--pending",
  blocked: "cj-step--blocked",
};

const STEP_GOSTERGE = {
  login: "__login__",
  project: "projects",
  domain: "domain_manager",
  seo: "talon",
  authority: "authority_factory",
  publish: "publisher_hub",
  deploy: "astro_factory",
  monitoring: "mission_control_center",
};

export default function CustomerJourneyCard({ journey, onNavigate }) {
  if (!journey) return null;

  const cjcr = journey.customer_journey_completion_rate ?? 0;
  const demo = journey.demo_project || {};
  const steps = (journey.steps || []).slice(0, 8);

  const goStep = (step) => {
    const target = STEP_GOSTERGE[step.id];
    if (target === "__login__") {
      window.location.assign("/login");
      return;
    }
    if (target && onNavigate) onNavigate(target);
  };

  return (
    <HivePanel title="Customer Journey — Operation Phoenix" className="cj-card">
      <div className="cj-card-head">
        <div className="cj-metric">
          <span className="cj-metric-label">CJCR</span>
          <span className="cj-metric-value">{cjcr}%</span>
          <span className="cj-metric-target">/ {journey.target ?? 100}% hedef</span>
        </div>
        {demo.name && (
          <div className="cj-demo-badge" title="Phoenix demo projesi">
            <span className="cj-demo-dot" aria-hidden />
            Demo: <strong>{demo.name}</strong>
            {demo.domain ? ` · ${demo.domain}` : ""}
            {demo.is_active ? " · Aktif" : ""}
          </div>
        )}
      </div>

      <div className="cj-steps" role="list">
        {steps.map((step) => (
          <button
            key={step.id}
            type="button"
            className={`cj-step ${STATUS_CLASS[step.status] || STATUS_CLASS.not_started}`}
            role="listitem"
            title={step.label_tr || step.label}
            onClick={() => goStep(step)}
          >
            <span className="cj-step-num">{step.order}</span>
            <span className="cj-step-label">{step.label_tr || step.label}</span>
            <span className="cj-step-status">{STATUS_LABEL[step.status] || step.status}</span>
          </button>
        ))}
      </div>

      <div className="cj-card-foot">
        <HiveBtn size="sm" variant="secondary" onClick={() => onNavigate?.("projects")}>
          Projects
        </HiveBtn>
        <HiveBtn size="sm" variant="secondary" onClick={() => onNavigate?.("hive_academy")}>
          Academy Rehberi
        </HiveBtn>
      </div>
    </HivePanel>
  );
}
