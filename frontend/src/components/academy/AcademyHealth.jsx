import React, { useEffect, useState } from "react";
import API from "../../api";

const API_PREFIX = "/api/academy";

export default function AcademyHealth({ onOpenDoc }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await API.get(`${API_PREFIX}/health`);
        setData(res.data);
      } catch {
        setData(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <p className="ha-muted">Documentation Health yükleniyor…</p>;
  if (!data) return <p className="ha-muted">Health verisi alınamadı.</p>;

  const s = data.stats || {};
  const cards = [
    { label: "Toplam Doküman", value: s.total },
    { label: "Tamamlanan (published)", value: s.published },
    { label: "Eksik (draft)", value: s.draft },
    { label: "Auto Draft", value: s.auto_draft },
    { label: "Eski Sürüm", value: s.stale_version },
    { label: "AI Güncellenecek", value: s.ai_update_pending },
    { label: "Screenshot Eksik", value: s.missing_screenshot },
    { label: "Video Eksik", value: s.missing_video },
    { label: "Quiz Eksik", value: s.missing_quiz },
    { label: "Düşük Kalite", value: s.low_quality },
  ];

  return (
    <div className="ha-health">
      <h2>Documentation Health</h2>
      {data.live_sync_warning && (
        <div className="ha-health-alert">
          ⚠️ {data.missing_module_count} modül için Academy dokümanı eksik — canlı senkron uyarısı
        </div>
      )}
      <div className="ha-dash-grid">
        {cards.map((c) => (
          <div key={c.label} className="ha-dash-card">
            <h3>{c.label}</h3>
            <p className="ha-stat">{c.value ?? 0}</p>
          </div>
        ))}
      </div>
      <h3>Düşük Kalite Skorları</h3>
      <ul className="ha-dash-list">
        {(data.items || []).slice(0, 15).map((item) => (
          <li key={item.slug}>
            <button type="button" className="ha-link-btn" onClick={() => onOpenDoc?.(item.slug)}>
              {item.title} — {item.quality}/100
            </button>
          </li>
        ))}
      </ul>
      <p className="ha-muted">Partner Academy · Marketplace Learning · Sandbox — TODO</p>
    </div>
  );
}
