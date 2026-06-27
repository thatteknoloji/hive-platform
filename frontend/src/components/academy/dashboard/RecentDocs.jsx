import React from "react";
import { formatRelativeDate } from "./academyUtils";

export default function RecentDocs({ docs = [], onOpenDoc, onViewAll }) {
  const items = docs.slice(0, 6);

  return (
    <section className="academy-panel academy-glass academy-fade-up">
      <header className="academy-panel__header">
        <h2 className="academy-panel__title">Son Güncellenen Dokümanlar</h2>
        <button type="button" className="academy-link" onClick={onViewAll}>Tümünü Gör</button>
      </header>
      <ul className="academy-doc-list">
        {items.map((d) => (
          <li key={d.slug || d.title}>
            <button type="button" className="academy-doc-row" onClick={() => onOpenDoc(d.slug)}>
              <div className="academy-doc-row__main">
                <span className="academy-doc-row__title">{d.title}</span>
                <span className="academy-doc-row__meta">{d.section || "Academy"}</span>
              </div>
              <div className="academy-doc-row__tags">
                {d.version && (
                  <span className="academy-tag academy-tag--gold">{d.version}</span>
                )}
                {d.badge === "Yeni" && <span className="academy-tag academy-tag--new">Yeni</span>}
                {(d.updated_at || d.last_updated) && (
                  <span className="academy-doc-row__time">
                    {d.updated_at || formatRelativeDate(d.last_updated)}
                  </span>
                )}
              </div>
            </button>
          </li>
        ))}
        {!items.length && (
          <li className="academy-doc-list__empty">Henüz güncelleme yok</li>
        )}
      </ul>
    </section>
  );
}
