import React from "react";
import { DESIGN_DNA_BY_ID, COLOR_BY_ID } from "../../config/brandWizard";

export default function DesignPreview({ designDna, colorIdentity, customColor }) {
  const dna = DESIGN_DNA_BY_ID[designDna];
  const color = COLOR_BY_ID[colorIdentity];
  const accent = colorIdentity === "custom" && customColor
    ? customColor
    : (color?.accent || "#6366f1");
  const swatch = color?.swatch || ["#1e1e2e", "#2d2d44", "#6366f1"];
  const layout = dna?.layout || "hero-center";
  const mood = dna?.mood || "dark";

  return (
    <div className={`hive-brand-preview hive-brand-preview--${mood}`} style={{ "--preview-accent": accent, "--preview-bg": swatch[0], "--preview-surface": swatch[1], "--preview-text": swatch[2] }}>
      <div className="hive-brand-preview-chrome">
        <span className="hive-brand-preview-dot" />
        <span className="hive-brand-preview-dot" />
        <span className="hive-brand-preview-dot" />
        <span className="hive-brand-preview-url">yourbrand.com</span>
      </div>
      <div className={`hive-brand-preview-body hive-brand-preview-layout--${layout}`}>
        <div className="hive-brand-preview-nav">
          <span className="hive-brand-preview-logo" />
          <span className="hive-brand-preview-nav-links">
            <i /><i /><i />
          </span>
        </div>
        {layout === "product-grid" ? (
          <div className="hive-brand-preview-grid">
            {[1, 2, 3].map((n) => <div key={n} className="hive-brand-preview-card" />)}
          </div>
        ) : (
          <>
            <div className="hive-brand-preview-hero">
              <div className="hive-brand-preview-headline" />
              <div className="hive-brand-preview-subline" />
              <div className="hive-brand-preview-cta" />
            </div>
            {layout === "editorial" && (
              <div className="hive-brand-preview-columns">
                <div /><div /><div />
              </div>
            )}
          </>
        )}
      </div>
      <div className="hive-brand-preview-caption">
        {dna ? dna.label : "Tasarım DNA seçin"}
        {color ? ` · ${color.label}` : ""}
      </div>
    </div>
  );
}
