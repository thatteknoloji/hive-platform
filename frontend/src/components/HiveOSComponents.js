import React, { memo } from "react";
import { HiveBadge, HiveBtn, HiveEmptyState, HivePanel } from "./HiveModuleUI";

const PRIORITY_TONE = {
  CRITICAL: "danger",
  HIGH: "warning",
  MEDIUM: "info",
  LOW: "neutral",
};

export function MissionControlSkeleton() {
  return (
    <div className="hive-os-skeleton" aria-hidden>
      <div className="hive-os-skeleton-bar" />
      <div className="hive-os-skeleton-rec" />
      <div className="hive-os-skeleton-grid">
        <div /><div /><div />
      </div>
    </div>
  );
}

export const OperationSummaryBar = memo(function OperationSummaryBar({ items, onNavigate }) {
  return (
    <div className="hive-os-ops-bar">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          className={`hive-os-ops-item hive-os-ops-${item.tone}`}
          onClick={() => onNavigate?.(item.link)}
        >
          <span className="hive-os-ops-label">{item.label}</span>
          <span className="hive-os-ops-value">{item.value}</span>
          <span className="hive-os-ops-narrative">{item.narrative}</span>
        </button>
      ))}
    </div>
  );
});
export function HiveRecommendation({ rec, onExecute, onNavigate }) {
  if (!rec) return null;
  return (
    <section className="hive-os-recommendation hive-os-enter">
      <div className="hive-os-rec-header">
        <span className="hive-os-rec-icon" aria-hidden>🧠</span>
        <div>
          <span className="hive-os-rec-kicker">HIVE Recommendation</span>
          <h2 className="hive-os-rec-title">{rec.headline}</h2>
          {rec.detail && <p className="hive-os-rec-detail">{rec.detail}</p>}
        </div>
        <HiveBadge tone={PRIORITY_TONE[rec.priority] || "info"}>{rec.priority}</HiveBadge>
      </div>
      <div className="hive-os-rec-body">
        <div className="hive-os-rec-gain">
          <span className="hive-os-rec-gain-label">{rec.estimatedGainLabel || "Tahmini etki"}</span>
          <span className="hive-os-rec-gain-value">{rec.estimatedGain}</span>
        </div>
        <div className="hive-os-rec-actions">
          <span className="hive-os-rec-source">Kaynak: {rec.source?.replace(/_/g, " ")}</span>
          <div className="hive-os-rec-btns">
            <HiveBtn variant="secondary" onClick={() => onNavigate?.(rec.target)}>
              {rec.actionLabel}
            </HiveBtn>
            <HiveBtn onClick={() => (onExecute ? onExecute(rec) : onNavigate?.(rec.target))}>
              {rec.executeLabel || "Execute Plan"}
            </HiveBtn>
          </div>
        </div>
      </div>
    </section>
  );
}

export function TodayMissionPanel({ items, onNavigate }) {
  if (!items?.length) {
    return (
      <HivePanel title="Today's Mission" className="hive-os-mission-panel">
        <HiveEmptyState
          icon="🎯"
          title="Bugün için görev üretilmedi"
          description="Autonomous Agent veya SERP Defense analizi çalıştırın."
          actionLabel="Autonomous Agent Aç"
          onAction={() => onNavigate?.("autonomous_seo_agent")}
        />
      </HivePanel>
    );
  }

  return (
    <HivePanel title="Today's Mission" className="hive-os-mission-panel hive-os-enter">
      <ol className="hive-os-mission-list">
        {items.map((m) => (
          <li key={m.id || m.order} className="hive-os-mission-item">
            <button type="button" className="hive-os-mission-btn" onClick={() => onNavigate?.(m.deep_link)}>
              <span className="hive-os-mission-order">{m.order}</span>
              <div className="hive-os-mission-main">
                <span className="hive-os-mission-module">{m.module}</span>
                <strong>{m.title}</strong>
                {m.detail && <span className="hive-os-mission-detail">{m.detail}</span>}
              </div>
              <div className="hive-os-mission-meta">
                <HiveBadge tone={PRIORITY_TONE[m.priority] || "info"}>{m.priority}</HiveBadge>
                <span className="hive-os-mission-impact">Impact: {m.impact}</span>
                <span className="hive-os-mission-gain">{m.gain}</span>
              </div>
            </button>
          </li>
        ))}
      </ol>
    </HivePanel>
  );
}

export function LiveEventStream({ events, onNavigate }) {
  return (
    <HivePanel title="Live Event Stream" className="hive-os-events hive-os-enter">
      {!events?.length ? (
        <HiveEmptyState
          icon="📡"
          title="Henüz canlı event yok"
          description="Modül aktiviteleri HIVE Brain timeline'a düştükçe burada görünür."
          actionLabel="HIVE Brain Aç"
          onAction={() => onNavigate?.("hive_brain_engine")}
        />
      ) : (
        <ul className="hive-os-event-list">
          {events.map((ev) => (
            <li key={ev.id}>
              <button type="button" className="hive-os-event-row" onClick={() => onNavigate?.(ev.deep_link)}>
                <span className="hive-os-event-time">{ev.time}</span>
                <span className="hive-os-event-dot" aria-hidden />
                <span className="hive-os-event-label">{ev.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </HivePanel>
  );
}

export function NextBestActionsPanel({ actions, onNavigate, onAck, onDone }) {
  return (
    <HivePanel title="Next Best Actions" className="hive-os-actions hive-os-enter">
      {!actions?.length ? (
        <HiveEmptyState
          icon="⚡"
          title="Önerilen aksiyon bekleniyor"
          description="Rank Watcher ve SERP Defense verisi geldikçe aksiyonlar burada listelenir."
          actionLabel="Rank Watcher Aç"
          onAction={() => onNavigate?.("rank_index_watcher")}
        />
      ) : (
        <div className="hive-os-action-cards">
          {actions.map((a) => (
            <article key={a.action_id} className="hive-os-action-card">
              <div className="hive-os-action-head">
                <HiveBadge tone={PRIORITY_TONE[a.priority] || "info"}>{a.priority}</HiveBadge>
                <strong>{a.title}</strong>
              </div>
              {a.reason && <p>{a.reason}</p>}
              <span className="hive-os-action-source">
                {a.source_module?.replace(/_/g, " ")} → {a.target_module?.replace(/_/g, " ")}
              </span>
              <div className="hive-os-action-footer">
                <HiveBtn size="sm" onClick={() => onNavigate?.(a.deep_link || a.target_module)}>
                  Go to Module
                </HiveBtn>
                {onAck && (
                  <HiveBtn size="sm" variant="secondary" onClick={() => onAck(a.action_id)} disabled={a.status !== "suggested"}>
                    Ack
                  </HiveBtn>
                )}
                {onDone && (
                  <HiveBtn size="sm" variant="secondary" onClick={() => onDone(a.action_id)} disabled={a.status === "done"}>
                    Done
                  </HiveBtn>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </HivePanel>
  );
}

export function ActiveThreatsPanel({ threats, onNavigate }) {
  return (
    <HivePanel title="Active Threats" className="hive-os-threats hive-os-enter">
      {!threats?.length ? (
        <HiveEmptyState
          icon="🛡"
          title="SERP verisi yok"
          description="Rank Watcher ile pozisyon takibi başlatın, tehditler otomatik görünür."
          actionLabel="Rank Watcher Aç"
          onAction={() => onNavigate?.("rank_index_watcher")}
        />
      ) : (
        <div className="hive-os-threat-grid">
          {threats.map((t, i) => (
            <button
              key={t.keyword || i}
              type="button"
              className="hive-os-threat-card"
              onClick={() => onNavigate?.("serp_defense_engine")}
            >
              <span className="hive-os-threat-keyword">{t.keyword || t.title}</span>
              <span className="hive-os-threat-fortress">Fortress {t.fortress_score ?? "—"}</span>
              <span className="hive-os-threat-risk">{t.pressure_level || t.risk_type || "Position Loss"}</span>
            </button>
          ))}
        </div>
      )}
    </HivePanel>
  );
}

export function GrowthOpportunitiesPanel({ opportunities, onNavigate }) {
  return (
    <HivePanel title="Growth Opportunities" className="hive-os-growth hive-os-enter">
      {!opportunities?.length ? (
        <HiveEmptyState
          icon="📈"
          title="Fırsat analizi yok"
          description="Opportunity Engine quick win taraması çalıştırın."
          actionLabel="Opportunity Aç"
          onAction={() => onNavigate?.("opportunity_engine")}
        />
      ) : (
        <div className="hive-os-growth-grid">
          {opportunities.map((o, i) => (
            <button
              key={o.title || o.label || i}
              type="button"
              className="hive-os-growth-card"
              onClick={() => onNavigate?.("opportunity_engine")}
            >
              <strong>{o.title || o.label || o.keyword}</strong>
              <span>Trafik: {o.traffic_score ?? o.opportunity_score ?? "—"}</span>
              <span>Zorluk: {o.difficulty_score ?? o.difficulty ?? "—"}</span>
            </button>
          ))}
        </div>
      )}
    </HivePanel>
  );
}

export function ModuleStatusWall({ modules, onNavigate }) {
  return (
    <section className="hive-os-status-wall hive-os-enter">
      <h3 className="hive-os-status-title">Module Status Wall</h3>
      <div className="hive-os-status-grid">
        {modules.map((m) => (
          <button
            key={m.name}
            type="button"
            className={`hive-os-status-card hive-os-status-${m.status}`}
            onClick={() => onNavigate?.(m.link)}
          >
            <span className="hive-os-status-dot" aria-hidden />
            <span className="hive-os-status-name">{m.name}</span>
            <span className="hive-os-status-detail">{m.detail}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

export function LearningProgressPanel({ learning, onNavigate }) {
  if (!learning) return null;
  const { academy, wizard, successPath, readiness, mentor } = learning;
  return (
    <section className="hive-os-learning hive-os-enter">
      <h3 className="hive-os-status-title">Learning Progress</h3>
      <div className="hive-os-learning-grid">
        <button type="button" className="hive-os-learning-card" onClick={() => onNavigate?.("production_readiness_engine")}>
          <span className="hive-os-learning-label">Production Readiness</span>
          <span className="hive-os-learning-value">{learning.readiness?.overall_score ?? 0}%</span>
          <span className="hive-os-learning-sub">{learning.readiness?.launch_mode || "development"}</span>
        </button>
        <button type="button" className="hive-os-learning-card" onClick={() => onNavigate?.("hive_success_path")}>
          <span className="hive-os-learning-label">Success Path</span>
          <span className="hive-os-learning-value">{successPath?.completion_score ?? 0}%</span>
          <span className="hive-os-learning-sub">
            {successPath?.steps_completed ?? 0}/{successPath?.total_steps ?? 8} adım
          </span>
        </button>
        <button type="button" className="hive-os-learning-card" onClick={() => onNavigate?.("hive_academy")}>
          <span className="hive-os-learning-label">Academy Progress</span>
          <span className="hive-os-learning-value">{academy?.progress_percent ?? 0}%</span>
          <span className="hive-os-learning-sub">{academy?.modules_viewed ?? 0} modül incelendi</span>
        </button>
        <button type="button" className="hive-os-learning-card" onClick={() => onNavigate?.("first_run_wizard")}>
          <span className="hive-os-learning-label">Wizard</span>
          <span className="hive-os-learning-value">{wizard?.progress_percent ?? 0}%</span>
          <span className="hive-os-learning-sub">{wizard?.completed_count ?? 0}/{wizard?.total_steps ?? 8} adım</span>
        </button>
        <button type="button" className="hive-os-learning-card" onClick={() => onNavigate?.("hive_mentor")}>
          <span className="hive-os-learning-label">Mentor Questions</span>
          <span className="hive-os-learning-value">{mentor?.questions_asked ?? 0}</span>
          <span className="hive-os-learning-sub">Kural tabanlı yönlendirme</span>
        </button>
      </div>
    </section>
  );
}

export function OrchestratorStatusPanel({ orchestrator, onNavigate }) {
  if (!orchestrator) return null;
  const mcc = orchestrator.mission_control || orchestrator;
  return (
    <section className="hive-os-orchestrator hive-os-enter">
      <h3 className="hive-os-status-title">Action Orchestrator</h3>
      <div className="hive-os-learning-grid">
        <button type="button" className="hive-os-learning-card" onClick={() => onNavigate?.("action_orchestrator")}>
          <span className="hive-os-learning-label">Pending Actions</span>
          <span className="hive-os-learning-value">{mcc.pending_actions ?? orchestrator.queued ?? 0}</span>
          <span className="hive-os-learning-sub">Kuyruk + onay bekleyen</span>
        </button>
        <button type="button" className="hive-os-learning-card" onClick={() => onNavigate?.("action_orchestrator")}>
          <span className="hive-os-learning-label">Running Actions</span>
          <span className="hive-os-learning-value">{mcc.running_actions ?? orchestrator.processing ?? 0}</span>
          <span className="hive-os-learning-sub">İşleniyor</span>
        </button>
        <button type="button" className="hive-os-learning-card" onClick={() => onNavigate?.("action_orchestrator")}>
          <span className="hive-os-learning-label">Failed / Today</span>
          <span className="hive-os-learning-value">{mcc.failed_actions ?? orchestrator.failed ?? 0} / {mcc.completed_today ?? orchestrator.completed_today ?? 0}</span>
          <span className="hive-os-learning-sub">Hata · bugün tamamlanan</span>
        </button>
      </div>
    </section>
  );
}
