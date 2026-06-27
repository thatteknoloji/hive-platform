import React from "react";
import { formatDuration } from "./academyUtils";

function StatCard({ icon, label, value, sub, progress, delay = 0, iconClass = "" }) {
  return (
    <article
      className="academy-stat-card academy-card-lift academy-fade-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`academy-stat-card__icon ${iconClass}`}>{icon}</div>
      <div className="academy-stat-card__body">
        <span className="academy-stat-card__label">{label}</span>
        <span className="academy-stat-card__value">{value}</span>
        {sub && <span className="academy-stat-card__sub">{sub}</span>}
        {progress != null && (
          <div className="academy-stat-card__bar" aria-hidden>
            <div className="academy-stat-card__bar-fill" style={{ width: `${Math.min(100, progress)}%` }} />
          </div>
        )}
      </div>
    </article>
  );
}

export default function AcademyStats({ data }) {
  if (!data) return null;
  const p = data.progress || {};
  const pct = data.percent ?? p.academy_percent ?? 0;
  const earned = p.earned_badges ?? (data.badges || []).filter((b) => b.earned).length;
  const totalBadges = p.total_badges ?? 28;
  const exam = data.upcoming_exam || {};
  const todayLearn = p.today_learning || formatDuration(data.total_read_seconds);
  const todayTarget = p.today_learning_target || "3s 00d";

  return (
    <section className="academy-stats" aria-label="Özet metrikler">
      <StatCard
        icon="📊"
        label="Academy İlerleme"
        value={`%${pct}`}
        progress={pct}
        delay={0}
      />
      <StatCard
        icon="⏱"
        iconClass="academy-stat-card__icon--timer"
        label="Bugün Öğrenme Süresi"
        value={todayLearn}
        sub={`Hedef: ${todayTarget}`}
        progress={72}
        delay={60}
      />
      <StatCard
        icon="🏆"
        label="Rozetler"
        value={`${earned} / ${totalBadges}`}
        sub={`Level ${data.level || 1}`}
        progress={Math.min(100, (earned / totalBadges) * 100)}
        delay={120}
      />
      <StatCard
        icon="🎓"
        iconClass="academy-stat-card__icon--exam"
        label="Yaklaşan Sınav"
        value={exam.title || "Authority Uzmanı"}
        sub={exam.date || "27 Haziran 2026"}
        progress={40}
        delay={180}
      />
      <StatCard
        icon="✓"
        iconClass="academy-stat-card__icon--check"
        label="Tamamlanan Modüller"
        value={`${data.completed_count ?? p.completed_modules ?? 0} / ${data.total_docs ?? p.total_modules ?? 116}`}
        sub="Published içerik"
        progress={pct}
        delay={240}
      />
    </section>
  );
}
