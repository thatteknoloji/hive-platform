import React from "react";

export default function ContinueLearning({ data, onContinue }) {
  const cont = data?.continue_learning || data?.continue || data?.last_read || {};
  const slug = cont.slug || "authority-factory-nedir";
  const title = cont.title || "Authority Factory";
  const desc = cont.description || "Otorite ağları oluştur, güçlendir ve yönet.";
  const pct = cont.progress ?? data?.percent ?? 63;
  const lastRead = cont.last_read;

  return (
    <section className="academy-continue academy-glass academy-card-lift academy-fade-up">
      <div className="academy-continue__glow" aria-hidden />
      <div className="academy-continue__header">
        <span className="academy-section-label">Devam Et</span>
        <span className="academy-pill academy-pill--gold">%{pct}</span>
      </div>
      <h2 className="academy-continue__title">{title}</h2>
      <p className="academy-continue__desc">{desc}</p>
      <div className="academy-continue__progress">
        <div className="academy-continue__bar">
          <div className="academy-continue__bar-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="academy-continue__pct">{pct}%</span>
      </div>
      <div className="academy-continue__footer">
        <button type="button" className="academy-btn academy-btn--gold" onClick={() => onContinue(slug)}>
          Devam Et →
        </button>
        {lastRead && (
          <span className="academy-continue__meta">Son okuma: {lastRead}</span>
        )}
      </div>
    </section>
  );
}
