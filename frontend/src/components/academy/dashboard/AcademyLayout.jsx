import React from "react";
import AcademyTopBar from "./AcademyTopBar";
import AcademySidebar from "./AcademySidebar";

export default function AcademyLayout({
  children,
  view,
  index,
  favorites,
  docStatus,
  activeSlug,
  searchQ,
  onSearchChange,
  onSearchSubmit,
  searchResults,
  onOpenDoc,
  sidebarOpen,
  onToggleSidebar,
  onCloseSidebar,
  theme,
  onThemeChange,
  onOpenPalette,
  onOpenHealth,
  onOpenChangelog,
  onNavigate,
  onGoDashboard,
  showReaderAI,
  aiPanel,
  aiCollapsed,
}) {
  return (
    <div className={`academy-enterprise ${showReaderAI ? "has-ai-panel" : ""}`}>
      <AcademyTopBar
        searchQ={searchQ}
        onSearchChange={onSearchChange}
        onOpenPalette={onOpenPalette}
        theme={theme}
        onThemeChange={onThemeChange}
        onOpenHealth={onOpenHealth}
        onOpenChangelog={onOpenChangelog}
        onNavigate={onNavigate}
        onGoDashboard={onGoDashboard}
        view={view}
      />

      <div className="academy-body">
        <button
          type="button"
          className="academy-mobile-toggle"
          onClick={onToggleSidebar}
          aria-label="Menü"
        >
          ☰
        </button>

        <AcademySidebar
          index={index}
          favorites={favorites}
          docStatus={docStatus}
          activeSlug={activeSlug}
          view={view}
          searchQ={searchQ}
          onSearchChange={onSearchChange}
          onSearchSubmit={onSearchSubmit}
          searchResults={searchResults}
          onOpenDoc={onOpenDoc}
          sidebarOpen={sidebarOpen}
          onCloseSidebar={onCloseSidebar}
        />

        <main className={`academy-main ${view === "reader" ? "academy-main--reader" : "academy-main--dashboard"}`}>
          {children}
        </main>

        {aiPanel}
        {aiCollapsed}
      </div>
    </div>
  );
}
