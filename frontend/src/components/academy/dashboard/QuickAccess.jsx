import React from "react";
import { QUICK_ACCESS_ITEMS } from "./academyUtils";

export default function QuickAccess({ items, onNavigate }) {
  const list = items?.length
    ? items.map((item) => ({
      id: item.route || item.id,
      label: item.title || item.label,
      icon: item.icon || "◆",
      desc: item.desc || "",
    }))
    : QUICK_ACCESS_ITEMS;

  return (
    <section className="academy-quick academy-fade-up">
      <header className="academy-panel__header">
        <h2 className="academy-panel__title">Hızlı Erişim</h2>
      </header>
      <div className="academy-quick-grid academy-quick-grid--hex">
        {list.map((item) => (
          <button
            key={item.id}
            type="button"
            className="academy-quick-hex academy-card-lift"
            onClick={() => onNavigate?.(item.id)}
            title={item.label}
          >
            <span className="academy-quick-hex__shape" aria-hidden />
            <span className="academy-quick-hex__icon">{item.icon}</span>
            <span className="academy-quick-hex__label">{item.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
