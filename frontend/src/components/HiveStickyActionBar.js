import React, { memo } from "react";

/** Sticky quick-action bar — operasyon merkezi alt çubuğu */
export const HiveStickyActionBar = memo(function HiveStickyActionBar({
  actions = [],
  hint,
}) {
  if (!actions.length) return null;

  return (
    <div className="hive-sticky-bar" role="toolbar" aria-label="Quick actions">
      <div className="hive-sticky-bar-inner">
        {hint && <span className="hive-sticky-hint">{hint}</span>}
        <div className="hive-sticky-actions">
          {actions.map((a) => (
            <button
              key={a.id || a.label}
              type="button"
              className={`hive-sticky-btn ${a.variant ? `variant-${a.variant}` : ""}`}
              onClick={a.onClick}
              title={a.shortcut || a.label}
              disabled={a.disabled}
            >
              {a.icon && <span className="hive-sticky-icon">{a.icon}</span>}
              <span>{a.label}</span>
              {a.shortcut && <kbd className="hive-sticky-kbd">{a.shortcut}</kbd>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
});
