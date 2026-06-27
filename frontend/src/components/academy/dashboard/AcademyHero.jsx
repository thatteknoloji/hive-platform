import React from "react";
import PhoenixVisual from "./PhoenixVisual";

export default function AcademyHero() {
  return (
    <section className="academy-hero academy-hero--phoenix" aria-label="HIVE Academy">
      <div className="academy-hero__bg" aria-hidden />
      <div className="academy-hero__hex" aria-hidden />
      <div className="academy-hero__glow academy-hero__glow--left" aria-hidden />
      <div className="academy-hero__glow academy-hero__glow--right" aria-hidden />

      <div className="academy-hero__inner academy-hero__inner--phoenix">
        <div className="academy-hero__content academy-fade-up">
          <div className="academy-hero__eyebrow">
            <span className="academy-pill academy-pill--gold">Operation Phoenix</span>
            <span className="academy-pill">Production Learning</span>
          </div>
          <h1 className="academy-hero__title">HIVE Academy</h1>
          <p className="academy-hero__subtitle-line">Production Learning — Operation Phoenix</p>
          <p className="academy-hero__desc">
            HIVE&apos;ın gücünü keşfet — yaşayan dokümantasyon, interaktif görevler ve enterprise
            öğrenme yolları ile ilk müşteri demosuna hazır ol.
          </p>
        </div>

        <div className="academy-hero__center academy-fade-up academy-fade-up--delay">
          <PhoenixVisual />
        </div>

        <blockquote className="academy-hero__quote academy-fade-up academy-fade-up--delay2">
          <p>&ldquo;Küllerinden doğan sadece efsaneler değildir. Sistemler de doğar.&rdquo;</p>
          <footer>— Operation Phoenix</footer>
        </blockquote>
      </div>
    </section>
  );
}
