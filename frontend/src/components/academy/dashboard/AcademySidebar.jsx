import React from "react";

const STATUS_ICON = { completed: "✓", in_progress: "◐", not_started: "○" };

export default function AcademySidebar({
  index,
  favorites,
  docStatus,
  activeSlug,
  view,
  searchQ,
  onSearchChange,
  onSearchSubmit,
  searchResults,
  onOpenDoc,
  sidebarOpen,
  onCloseSidebar,
}) {
  return (
    <>
      {sidebarOpen && (
        <button type="button" className="academy-sidebar-backdrop" onClick={onCloseSidebar} aria-label="Kapat" />
      )}
      <aside className={`academy-sidebar ${sidebarOpen ? "is-open" : ""}`}>
        <div className="academy-sidebar__brand">
          <span className="academy-sidebar__logo">⬡</span>
          <div>
            <strong>HIVE Academy</strong>
            <span>138 doküman</span>
          </div>
        </div>

        <div className="academy-sidebar__search">
          <input
            type="search"
            placeholder="Sidebar ara…"
            value={searchQ}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSearchSubmit()}
          />
          {searchResults?.length > 0 && (
            <div className="academy-sidebar__results">
              {searchResults.slice(0, 6).map((r) => (
                <button
                  key={r.slug}
                  type="button"
                  onClick={() => { onOpenDoc(r.slug); onCloseSidebar(); }}
                >
                  {r.title}
                </button>
              ))}
            </div>
          )}
        </div>

        <nav className="academy-sidebar__nav">
          {(index?.sections || []).map((section) => (
            <div key={section.slug} className="academy-sidebar__group">
              <div className="academy-sidebar__group-title">{section.title}</div>
              {(section.items || []).map((item) => {
                const st = docStatus(item.slug);
                const isActive = activeSlug === item.slug && view === "reader";
                return (
                  <button
                    key={`${section.slug}-${item.slug}`}
                    type="button"
                    className={`academy-sidebar__item ${isActive ? "is-active" : ""} is-${st}`}
                    onClick={() => { onOpenDoc(item.slug); onCloseSidebar(); }}
                  >
                    <span className="academy-sidebar__status">{STATUS_ICON[st] || "○"}</span>
                    <span className="academy-sidebar__item-text">
                      {favorites.includes(item.slug) && <span className="academy-sidebar__star">★</span>}
                      {item.title}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
