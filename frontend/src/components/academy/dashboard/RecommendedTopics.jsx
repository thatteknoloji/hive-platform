import React from "react";

export default function RecommendedTopics({ topics = [], onOpenDoc }) {
  const items = topics.slice(0, 4);

  return (
    <section className="academy-panel academy-glass academy-fade-up">
      <header className="academy-panel__header">
        <h2 className="academy-panel__title">Önerilen Konular</h2>
        <span className="academy-pill academy-pill--ai">AI önerisi</span>
      </header>
      <div className="academy-rec-list">
        {items.map((t) => (
          <button
            key={t.slug || t.title}
            type="button"
            className="academy-rec-row academy-card-lift"
            onClick={() => onOpenDoc(t.slug)}
          >
            <span className="academy-rec-row__icon">📖</span>
            <div className="academy-rec-row__body">
              <span className="academy-rec-row__title">{t.title}</span>
              <span className="academy-rec-row__meta">
                {t.level || "Orta Seviye"} · {t.minutes || 10} dk
              </span>
            </div>
            <span className="academy-rec-row__arrow" aria-hidden>→</span>
          </button>
        ))}
        {!items.length && (
          <p className="academy-muted">Öneri yükleniyor…</p>
        )}
      </div>
    </section>
  );
}
