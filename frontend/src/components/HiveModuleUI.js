import React from "react";

const ALERT_CLASS = {
  ok: "ok",
  success: "ok",
  err: "err",
  error: "err",
  warn: "warn",
  warning: "warn",
  info: "info",
};

export function HiveShell({ title, subtitle, meta, actions, children }) {
  return (
    <div className="hive-module">
      <header className="hm-header">
        <div className="hm-header-main">
          <div>
            <h2 className="hm-title">{title}</h2>
            {subtitle && <p className="hm-sub">{subtitle}</p>}
            {meta && <p className="hm-meta">{meta}</p>}
          </div>
          {actions && <div className="hm-header-actions">{actions}</div>}
        </div>
      </header>
      {children}
    </div>
  );
}

export function HiveAlert({ type = "ok", tone, children, pulse = false }) {
  if (!children) return null;
  const cls = ALERT_CLASS[tone || type] || "info";
  const pulseCls = pulse || cls === "err" ? " hm-alert-pulse" : "";
  return <div className={`hm-alert hm-alert-${cls}${pulseCls}`} role="status">{children}</div>;
}

export function HiveContextBar({ children, className = "" }) {
  return <div className={`hm-context-bar ${className}`.trim()}>{children}</div>;
}

export function HiveToolbar({ children }) {
  return <div className="hm-toolbar">{children}</div>;
}

export function HiveTabs({ tabs, active, onChange }) {
  return (
    <div className="ch-tabs hm-tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={active === t.id}
          className={`ch-tab hm-tab ${active === t.id ? "active" : ""}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function HiveSection({ title, description, actions, children, className = "" }) {
  return (
    <section className={`hm-section ${className}`.trim()}>
      {(title || actions) && (
        <div className="hm-section-head">
          <div>
            {title && <h3 className="hm-section-title">{title}</h3>}
            {description && <p className="hm-section-desc">{description}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function HivePanel({ title, description, children, className = "", flush = false, actions }) {
  return (
    <div className={`hm-panel ${flush ? "hm-panel-flush" : ""} ${className}`.trim()}>
      {(title || actions) && (
        <div className="hm-panel-head">
          <div>
            {title && <h3 className="hm-panel-title">{title}</h3>}
            {description && <p className="hm-panel-desc">{description}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className="hm-panel-body">{children}</div>
    </div>
  );
}

function normalizeStatItem(item, i) {
  if (Array.isArray(item)) {
    return { label: item[0], value: item[1], key: item[0] || i };
  }
  if (item && typeof item === "object") {
    return {
      label: item.label,
      value: item.value,
      hint: item.hint,
      tone: item.tone,
      highlight: item.highlight,
      key: item.key || item.label || i,
    };
  }
  return { label: String(item), value: "—", key: i };
}

export function HiveMissionBoard({ primary = [], secondary = [] }) {
  const p = (primary || []).map(normalizeStatItem);
  const s = (secondary || []).map(normalizeStatItem);
  return (
    <div className="hm-mission-board">
      {p.length > 0 && (
        <div className="hm-mission-primary">
          {p.map(({ label, value, hint, tone, key }) => (
            <div key={key} className={`hm-mission-metric hm-metric-${tone || "accent"}`}>
              <div className="hm-mission-label">{label}</div>
              <div className="hm-mission-value">{value ?? "—"}</div>
              {hint && <div className="hm-mission-hint">{hint}</div>}
            </div>
          ))}
        </div>
      )}
      {s.length > 0 && (
        <div className="hm-mission-secondary">
          {s.map(({ label, value, hint, tone, key }) => (
            <div key={key} className={`hm-stat-card hm-stat-compact ${tone ? `hm-metric-${tone}` : ""}`}>
              <div className="hm-stat-label">{label}</div>
              <div className="hm-stat-value">{value ?? "—"}</div>
              {hint && <div className="hm-stat-hint">{hint}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function HiveStatGrid({ items = [], stats, variant = "default", columns }) {
  const raw = items?.length ? items : stats || [];
  const normalized = raw.map(normalizeStatItem);
  const gridClass = [
    "hm-stat-grid",
    variant === "mission" ? "hm-stat-grid-mission" : "",
    columns ? `hm-stat-cols-${columns}` : "",
  ].filter(Boolean).join(" ");

  return (
    <div className={gridClass}>
      {normalized.map(({ label, value, hint, tone, highlight, key }) => (
        <div
          key={key}
          className={[
            "hm-stat-card",
            highlight || variant === "mission" ? "hm-stat-highlight" : "",
            tone ? `hm-metric-${tone}` : "",
          ].filter(Boolean).join(" ")}
        >
          <div className="hm-stat-label">{label}</div>
          <div className="hm-stat-value">{value ?? "—"}</div>
          {hint && <div className="hm-stat-hint">{hint}</div>}
        </div>
      ))}
    </div>
  );
}

export function HiveFormRow({ children }) {
  return <div className="hm-form-row">{children}</div>;
}

export function HiveField({ label, children, className = "", style }) {
  return (
    <div className={`hm-field ${className}`.trim()} style={style}>
      {label && <label className="hm-label">{label}</label>}
      {children}
    </div>
  );
}

export function HiveSelect({ value, onChange, children, ...props }) {
  return (
    <select className="hm-input" value={value} onChange={onChange} {...props}>
      {children}
    </select>
  );
}

export function HiveInput({ className = "", ...props }) {
  return <input className={`hm-input ${className}`.trim()} {...props} />;
}

export function HiveBtn({ variant = "primary", size = "", disabled, children, ...props }) {
  const mapped = variant === "secondary" ? "outline" : variant;
  const cls = ["hm-btn", `hm-btn-${mapped}`, size === "sm" ? "hm-btn-sm" : ""].filter(Boolean).join(" ");
  return (
    <button type="button" className={cls} disabled={disabled} {...props}>
      {children}
    </button>
  );
}

export function HiveBadge({ level, tone, children, variant }) {
  const map = {
    CRITICAL: "danger",
    HIGH: "warning",
    MEDIUM: "info",
    LOW: "neutral",
    danger: "danger",
    critical: "danger",
    err: "danger",
    error: "danger",
    warn: "warning",
    warning: "warning",
    ok: "success",
    success: "success",
    info: "info",
    muted: "neutral",
    neutral: "neutral",
  };
  const lvl = variant || level || tone || "neutral";
  const text = children || level || tone;
  return <span className={`hm-badge hm-badge-${map[lvl] || "neutral"}`}>{text}</span>;
}

const STATUS_CONFIG = {
  published: { tone: "success", label: "published", icon: "✓" },
  success: { tone: "success", label: "success", icon: "✓" },
  failed: { tone: "danger", label: "failed", icon: "✕" },
  login_required: { tone: "warning", label: "login required", icon: "🔐" },
  provider_missing: { tone: "danger", label: "provider missing", icon: "⚠" },
  processing: { tone: "info", label: "processing", icon: "⚙" },
  queued: { tone: "neutral", label: "queued", icon: "⏳" },
  review_required: { tone: "warning", label: "review", icon: "👁" },
  repo_created: { tone: "info", label: "repo created", icon: "📦" },
  pages_enabled: { tone: "info", label: "pages enabled", icon: "🌐" },
  planned: { tone: "neutral", label: "planned", icon: "📋" },
  draft: { tone: "neutral", label: "draft", icon: "📝" },
};

export function HiveStatusBadge({ status }) {
  const key = (status || "").toLowerCase().replace(/\s+/g, "_");
  const cfg = STATUS_CONFIG[key] || { tone: "neutral", label: status || "—", icon: "•" };
  return (
    <HiveBadge tone={cfg.tone}>
      {cfg.icon} {cfg.label}
    </HiveBadge>
  );
}

export function HiveEmptyState({
  icon = "📭",
  title = "Veri yok",
  description,
  why,
  actionLabel,
  onAction,
  navigateLabel,
  onNavigate,
  academyLabel,
  onAcademy,
}) {
  return (
    <div className="hm-empty-state">
      <div className="hm-empty-icon" aria-hidden>{icon}</div>
      <div className="hm-empty-title">{title}</div>
      {description && <p className="hm-empty-desc">{description}</p>}
      {why && <p className="hm-empty-why">{why}</p>}
      <div className="hm-empty-actions">
        {actionLabel && onAction && (
          <HiveBtn size="sm" onClick={onAction}>{actionLabel}</HiveBtn>
        )}
        {navigateLabel && onNavigate && (
          <HiveBtn size="sm" variant="secondary" onClick={onNavigate}>{navigateLabel}</HiveBtn>
        )}
        {academyLabel && onAcademy && (
          <HiveBtn size="sm" variant="secondary" onClick={onAcademy}>{academyLabel}</HiveBtn>
        )}
      </div>
    </div>
  );
}

export function HiveConceptTooltip({ conceptKey, concepts = {} }) {
  const c = concepts[conceptKey];
  if (!c) return null;
  return (
    <span className="hm-concept-tip" title={c.text}>
      <span className="hm-concept-tip-icon" aria-label={`${c.label} açıklaması`}>?</span>
      <span className="hm-concept-tip-popup" role="tooltip">{c.text}</span>
    </span>
  );
}

export function HiveLabelWithTip({ label, conceptKey, concepts }) {
  return (
    <span className="hm-label-tip">
      {label}
      <HiveConceptTooltip conceptKey={conceptKey} concepts={concepts} />
    </span>
  );
}

export function HiveMetricCard({ label, value, tone = "accent", sublabel, icon, onClick, className = "", size = "md" }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      className={`hm-metric-card hm-metric-${tone} hm-metric-${size} ${onClick ? "hm-metric-clickable" : ""} ${className}`.trim()}
      onClick={onClick}
    >
      {icon && <span className="hm-metric-icon" aria-hidden>{icon}</span>}
      <div className="hm-metric-label">{label}</div>
      <div className="hm-metric-value">{value ?? "—"}</div>
      {sublabel && <div className="hm-metric-sublabel">{sublabel}</div>}
    </Tag>
  );
}

export function HiveWorkerHealthCard({ title, providerReady, provider, error, stats = [], variant = "default" }) {
  const tone = providerReady ? "success" : "danger";
  return (
    <div className={`hm-worker-health hm-worker-${variant} hm-worker-${tone}`}>
      <div className="hm-worker-head">
        <span className="hm-worker-dot" />
        <strong>{title}</strong>
        <HiveBadge tone={tone}>{providerReady ? "READY" : "MISSING"}</HiveBadge>
      </div>
      {provider && <p className="hm-worker-meta">Provider: {provider}</p>}
      {error && !providerReady && (
        <HiveAlert type="error" pulse>{error}</HiveAlert>
      )}
      {stats.length > 0 && (
        <div className="hm-worker-stats">
          {stats.map(([l, v]) => (
            <div key={l} className="hm-worker-stat">
              <span>{l}</span>
              <strong>{v}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function HiveTaskTimeline({ steps = [] }) {
  if (!steps.length) return null;
  return (
    <ol className="hm-task-timeline">
      {steps.map((s, i) => (
        <li key={s.id || i} className={`hm-task-step hm-task-${s.state || "pending"}`}>
          <span className="hm-task-dot" />
          <span className="hm-task-label">{s.label}</span>
        </li>
      ))}
    </ol>
  );
}

export function HiveTable({ columns, rows, emptyText = "Veri yok", empty, density = "comfortable", emptyAction, emptyActionLabel, onRowClick }) {
  const emptyMessage = emptyText || empty || "Veri yok";
  if (!rows?.length) {
    return (
      <HiveEmptyState
        icon="📋"
        title={emptyMessage}
        description="Bu bölümde henüz kayıt yok. İlgili aksiyonu çalıştırarak veri oluşturabilirsiniz."
        actionLabel={emptyActionLabel}
        onAction={emptyAction}
      />
    );
  }
  return (
    <div className={`hm-table-wrap hm-table-${density}`}>
      <table className="hm-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key || c}>{typeof c === "string" ? c : c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row?.id || row?.key || i}
              className={onRowClick ? "hm-table-row-clickable" : undefined}
              onClick={onRowClick ? () => onRowClick(i, row) : undefined}
            >
              {columns.map((c, colIdx) => {
                const key = typeof c === "string" ? c : c.key;
                const render = typeof c === "object" && c.render;
                let cell;
                if (Array.isArray(row)) {
                  cell = row[colIdx];
                } else if (render) {
                  cell = render(row);
                } else {
                  cell = row[key];
                }
                return <td key={key || colIdx}>{cell}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function HiveCard({ title, meta, children, actions, variant = "default" }) {
  return (
    <div className={`hm-card hm-card-${variant}`}>
      {(title || actions) && (
        <div className="hm-card-head">
          <div>
            {title && <div className="hm-card-title">{title}</div>}
            {meta && <div className="hm-card-meta">{meta}</div>}
          </div>
          {actions}
        </div>
      )}
      {children && <div className="hm-card-body">{children}</div>}
    </div>
  );
}

export function HiveCode({ children }) {
  return <pre className="hm-code">{children}</pre>;
}

export function HiveCheck({ label, checked, onChange }) {
  return (
    <label className="hm-check">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span>{label}</span>
    </label>
  );
}

export function HiveIntegrationList({ items = [] }) {
  if (!items.length) return null;
  return (
    <ul className="hm-integration-list">
      {items.map(([name, ok, detail]) => (
        <li key={name} className={ok ? "is-ok" : "is-warn"}>
          <span className="hm-integration-name">{name}</span>
          <span className="hm-integration-status">{ok ? "OK" : detail || "not ready"}</span>
        </li>
      ))}
    </ul>
  );
}

export function HiveToast({ message, onClose }) {
  if (!message) return null;
  return (
    <div className="hm-toast" role="status">
      <span>{message}</span>
      {onClose && (
        <button type="button" className="hm-toast-close" onClick={onClose} aria-label="Kapat">×</button>
      )}
    </div>
  );
}

export function HiveSkeleton({ lines = 3 }) {
  return (
    <div className="hm-skeleton-wrap" aria-busy="true" aria-label="Yükleniyor">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`hm-skeleton ${i === 0 ? "hm-skeleton-lg" : ""}`} />
      ))}
    </div>
  );
}
