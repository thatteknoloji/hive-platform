import React from "react";
import { DASHBOARD_LEARNING_PATH } from "./academyUtils";

const STATUS_LABEL = {
  completed: "Done",
  active: "Active",
  pending: "Pending",
  in_progress: "Active",
  not_started: "Pending",
};

export default function LearningPath({ steps, currentStep, horizontal = false }) {
  const path = (steps?.length ? steps : DASHBOARD_LEARNING_PATH.map((s) => ({
    id: s.id,
    title: s.label,
    status: s.id === (currentStep || "authority") ? "active" : "pending",
  })));

  return (
    <section className={`academy-panel academy-glass academy-fade-up ${horizontal ? "academy-path--horizontal" : ""}`}>
      <header className="academy-panel__header">
        <h2 className="academy-panel__title">Öğrenme Rotası</h2>
      </header>
      <div className={`academy-path-timeline ${horizontal ? "academy-path-timeline--horizontal" : ""}`}>
        {path.map((step, i) => {
          const status = step.status || "pending";
          const isActive = status === "active" || status === "in_progress";
          const isDone = status === "completed";
          return (
            <React.Fragment key={step.id || step.title}>
              <div
                className={`academy-path-node ${isActive ? "is-active" : ""} ${isDone ? "is-done" : ""}`}
              >
                <span className="academy-path-node__dot" />
                <span className="academy-path-node__label">{step.title || step.label}</span>
                {horizontal && (
                  <span className="academy-path-node__status">{STATUS_LABEL[status] || status}</span>
                )}
              </div>
              {i < path.length - 1 && (
                <span className={`academy-path-arrow ${horizontal ? "academy-path-arrow--h" : ""}`} aria-hidden>
                  {horizontal ? "→" : "↓"}
                </span>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </section>
  );
}
