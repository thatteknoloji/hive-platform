import React, { useState, useEffect } from "react";
import StoryForgeStudio from "./StoryForgeV2";
import StoryForgeUrlWizard from "./StoryForgeV3";

const MAIN_TABS = [
  {
    id: "url",
    label: "🔗 Link Çekici",
    hint: "fastCRW · önizle · kurallı düzenle · yayın kanıtı",
  },
  {
    id: "studio",
    label: "⚡ Stüdyo & Otomasyon",
    hint: "Yapıştır, toplu, AI üretim, foto havuzu",
  },
];

export default function StoryForge({ onOpenCategoryHub, initialTab = "url" }) {
  const [tab, setTab] = useState(initialTab === "studio" ? "studio" : "url");

  useEffect(() => {
    setTab(initialTab === "studio" ? "studio" : "url");
  }, [initialTab]);

  return (
    <div className="storyforge-panel storyforge-unified">
      <header className="storyforge-header">
        <h2>📖 StoryForge</h2>
        <p className="storyforge-sub">
          Hikaye çek, Kuşadası&apos;na uyarla, WordPress&apos;e yayınla — tek panel
        </p>
      </header>

      <div className="sf-main-tabs" role="tablist" aria-label="StoryForge modları">
        {MAIN_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`sf-main-tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            <span className="sf-main-tab-label">{t.label}</span>
            <span className="sf-main-tab-hint">{t.hint}</span>
          </button>
        ))}
      </div>

      {tab === "url" && <StoryForgeUrlWizard embedded />}
      {tab === "studio" && (
        <StoryForgeStudio
          embedded
          hideManualUrl
          onOpenCategoryHub={onOpenCategoryHub}
        />
      )}
    </div>
  );
}
