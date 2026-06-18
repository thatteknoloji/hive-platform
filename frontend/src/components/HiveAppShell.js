import React from "react";
import { HiveBtn } from "./HiveModuleUI";

export function HiveTopBar({
  projectName = "HIVE SEO OS",
  moduleLabel = "Mission Control",
  systemHealth,
  onQuickAction,
  quickActionLabel = "Mission Control",
  onLogout,
  userEmail,
  activeProjectName,
  projects = [],
  onProjectChange,
}) {
  const score = systemHealth ?? "—";
  const num = Number(score);
  const healthClass = Number.isFinite(num)
    ? num >= 75 ? "success" : num >= 50 ? "warning" : "danger"
    : "neutral";

  return (
    <header className="hive-topbar">
      <div className="hive-topbar-left">
        <div className="hive-topbar-brand">
          <span className="hive-topbar-logo">◆</span>
          <div>
            <div className="hive-topbar-project">{projectName}</div>
            <div className="hive-topbar-module">{moduleLabel}</div>
          </div>
        </div>
      </div>
      <div className="hive-topbar-right">
        {userEmail && (
          <span className="hive-topbar-user" title={userEmail}>
            {userEmail}
          </span>
        )}
        {projects.length > 0 && (
          <select
            className="hive-topbar-project-select"
            value={activeProjectName || ""}
            onChange={(e) => onProjectChange && onProjectChange(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.project_id} value={p.project_id}>{p.name}</option>
            ))}
          </select>
        )}
        <div className={`hive-health-badge hive-health-${healthClass}`} title="System Health">
          <span className="hive-health-dot" />
          <span className="hive-health-label">Health</span>
          <span className="hive-health-score">{score}</span>
        </div>
        {onQuickAction && (
          <HiveBtn size="sm" onClick={onQuickAction}>{quickActionLabel}</HiveBtn>
        )}
        {onLogout && (
          <HiveBtn size="sm" variant="secondary" onClick={onLogout}>Çıkış</HiveBtn>
        )}
      </div>
    </header>
  );
}

export function HivePageFrame({ children, pageKey }) {
  return (
    <div className="hive-page-frame hive-page-enter" key={pageKey}>
      {children}
    </div>
  );
}

export function HiveCommandBar({
  placeholder = "Bugün ne yapıyoruz? Komut veya modül ara…",
  value,
  onChange,
  onSubmit,
}) {
  const handleKey = (e) => {
    if (e.key === "Enter" && onSubmit) onSubmit(value);
  };
  return (
    <div className="hive-command-bar">
      <span className="hive-command-icon" aria-hidden>⌘</span>
      <input
        type="text"
        className="hive-command-input"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onKeyDown={handleKey}
        readOnly={!onChange}
      />
      <span className="hive-command-hint">Enter</span>
    </div>
  );
}
