import React from "react";

export default function AcademyTopBar({
  searchQ,
  onSearchChange,
  onOpenPalette,
  theme,
  onThemeChange,
  onOpenHealth,
  onOpenChangelog,
  onNavigate,
  onGoDashboard,
  view,
}) {
  return (
    <header className="academy-topbar">
      <div className="academy-topbar__brand" onClick={onGoDashboard} onKeyDown={(e) => e.key === "Enter" && onGoDashboard()} role="button" tabIndex={0}>
        <span className="academy-topbar__logo">🎓</span>
        <span className="academy-topbar__name">Academy</span>
      </div>

      <div className="academy-topbar__search">
        <span className="academy-topbar__search-icon" aria-hidden>⌕</span>
        <input
          type="search"
          placeholder="Doküman, modül, workflow ara…"
          value={searchQ}
          onChange={(e) => onSearchChange(e.target.value)}
          onFocus={onOpenPalette}
        />
        <kbd className="academy-kbd" onClick={onOpenPalette}>⌘K</kbd>
      </div>

      <div className="academy-topbar__actions">
        <button type="button" className="academy-topbar-btn" title="Bildirimler" aria-label="Bildirimler">
          <span className="academy-topbar-btn__dot" />
          🔔
        </button>
        <select
          className="academy-topbar-select"
          value={theme}
          onChange={(e) => onThemeChange(e.target.value)}
          aria-label="Tema"
        >
          <option value="dark">Dark</option>
          <option value="light">Light</option>
          <option value="system">System</option>
        </select>
        <button type="button" className="academy-topbar-btn" onClick={onOpenHealth} title="Doc Health">
          Health
        </button>
        {view !== "changelog" && (
          <button type="button" className="academy-topbar-btn" onClick={onOpenChangelog}>
            Changelog
          </button>
        )}
        <button
          type="button"
          className="academy-topbar-btn academy-topbar-btn--gold"
          onClick={() => onNavigate?.("mission_control_center")}
        >
          ◆ Command Center
        </button>
        <button type="button" className="academy-topbar-avatar" title="Profil" aria-label="Profil">
          H
        </button>
      </div>
    </header>
  );
}
