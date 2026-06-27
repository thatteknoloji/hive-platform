import React, { useMemo } from "react";

export default function RecentlyViewed({ items: propItems, progress, index, onOpenDoc }) {
  const items = useMemo(() => {
    if (propItems?.length) return propItems;
    const prog = progress?.progress || {};
    const slugMap = {};
    (index?.sections || []).forEach((sec) => {
      (sec.items || []).forEach((item) => {
        slugMap[item.slug] = { ...item, section: sec.title };
      });
    });
    return Object.entries(prog)
      .filter(([, p]) => p.last_read_at)
      .sort((a, b) => (b[1].last_read_at || "").localeCompare(a[1].last_read_at || ""))
      .slice(0, 5)
      .map(([slug, p]) => ({
        slug,
        title: slugMap[slug]?.title || slug,
        progress: p.completed ? 100 : p.read_count ? 40 : 10,
      }));
  }, [propItems, progress, index]);

  return (
    <section className="academy-panel academy-glass academy-fade-up">
      <header className="academy-panel__header">
        <h2 className="academy-panel__title">Son İzlenen Konular</h2>
      </header>
      <ul className="academy-viewed-list">
        {items.map((item) => (
          <li key={item.slug || item.title}>
            <button type="button" className="academy-viewed-row" onClick={() => onOpenDoc(item.slug)}>
              <span className="academy-viewed-row__title">{item.title}</span>
              <div className="academy-viewed-row__bar">
                <div className="academy-viewed-row__fill" style={{ width: `${item.progress}%` }} />
              </div>
            </button>
          </li>
        ))}
        {!items.length && (
          <li className="academy-muted" style={{ padding: "12px 0" }}>Henüz konu açılmadı</li>
        )}
      </ul>
    </section>
  );
}
