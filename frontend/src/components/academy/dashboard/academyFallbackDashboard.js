/** Phoenix Academy dashboard — local fallback when API 404/offline */
export const FALLBACK_DASHBOARD = {
  success: true,
  fallback: true,
  title: "HIVE Academy",
  subtitle: "Production Learning — Operation Phoenix",
  operation: "Operation Phoenix",
  progress: {
    academy_percent: 64,
    completed_modules: 74,
    total_modules: 116,
    today_learning: "2s 47d",
    today_learning_target: "3s 00d",
    earned_badges: 12,
    total_badges: 28,
  },
  continue_learning: {
    title: "Authority Factory",
    description: "Otorite ağları oluştur, güçlendir ve yönet.",
    progress: 63,
    last_read: "26 Haziran 2026 20:45",
    slug: "authority-factory-nedir",
  },
  recent_docs: [
    { title: "Publisher Hub", version: "v2.1.0", badge: "Yeni", updated_at: "2 saat önce", slug: "publisher-hub-nedir" },
    { title: "Entity Graph", version: "v1.8.3", updated_at: "5 saat önce", slug: "entity_geo_graph" },
    { title: "Quality Gate", version: "v3.0.2", updated_at: "8 saat önce", slug: "quality-gate-nedir" },
    { title: "Index Watcher", version: "v2.2.1", updated_at: "12 saat önce", slug: "rank_index_watcher" },
    { title: "Astro Site Factory", version: "v1.6.0", updated_at: "1 gün önce", slug: "astro_factory" },
  ],
  recommended_topics: [
    { title: "Entity Graph Advanced", level: "İleri Seviye", minutes: 18, slug: "entity_geo_graph" },
    { title: "Internal Linking Strategy", level: "Orta Seviye", minutes: 14, slug: "internal-linking-strategy" },
    { title: "SERP Defense", level: "İleri Seviye", minutes: 16, slug: "serp_defense_engine" },
  ],
  learning_path_steps: [
    { title: "Başlangıç", status: "completed", id: "baslangic" },
    { title: "SEO", status: "completed", id: "seo" },
    { title: "GEO", status: "completed", id: "geo" },
    { title: "Authority", status: "active", id: "authority" },
    { title: "Publish", status: "pending", id: "publish" },
    { title: "Deploy", status: "pending", id: "deploy" },
    { title: "Advanced", status: "pending", id: "advanced" },
  ],
  recently_viewed: [
    { title: "Entity Factory", progress: 92, slug: "entity_geo_graph" },
    { title: "Site Deploy", progress: 48, slug: "astro_factory" },
  ],
  quick_access: [
    { title: "Command Center", route: "mission_control_center", icon: "◆" },
    { title: "Project Manager", route: "projects", icon: "🌐" },
    { title: "Publisher Hub", route: "publisher_hub", icon: "📢" },
    { title: "Quality Gate", route: "seo_quality_gate", icon: "🔬" },
    { title: "Rank Watcher", route: "rank_index_watcher", icon: "📈" },
    { title: "Authority Factory", route: "authority_factory", icon: "🏭" },
  ],
  upcoming_exam: { title: "Authority Uzmanı", date: "27 Haziran 2026" },
  percent: 64,
  completed_count: 74,
  total_docs: 116,
  current_learning_step: "authority",
};

export function normalizeDashboard(raw) {
  if (!raw) return { ...FALLBACK_DASHBOARD };
  const p = raw.progress || {};
  const cont = raw.continue_learning || raw.continue || raw.last_read || {};
  const pct = raw.percent ?? p.academy_percent ?? 64;
  return {
    ...FALLBACK_DASHBOARD,
    ...raw,
    percent: pct,
    completed_count: raw.completed_count ?? p.completed_modules ?? 74,
    total_docs: raw.total_docs ?? p.total_modules ?? 116,
    progress: { ...FALLBACK_DASHBOARD.progress, ...p },
    continue_learning: {
      ...FALLBACK_DASHBOARD.continue_learning,
      ...cont,
      title: cont.title || FALLBACK_DASHBOARD.continue_learning.title,
      slug: cont.slug || FALLBACK_DASHBOARD.continue_learning.slug,
      progress: cont.progress ?? pct,
    },
    recent_docs: raw.recent_docs?.length ? raw.recent_docs : FALLBACK_DASHBOARD.recent_docs,
    recommended_topics: raw.recommended_topics?.length
      ? raw.recommended_topics
      : (raw.recommended?.length ? raw.recommended.map((r) => ({
        title: r.title,
        slug: r.slug,
        level: r.level || "Orta Seviye",
        minutes: r.minutes || 10,
      })) : FALLBACK_DASHBOARD.recommended_topics),
    learning_path_steps: raw.learning_path_steps?.length
      ? raw.learning_path_steps
      : FALLBACK_DASHBOARD.learning_path_steps,
    recently_viewed: raw.recently_viewed?.length
      ? raw.recently_viewed
      : FALLBACK_DASHBOARD.recently_viewed,
    quick_access: raw.quick_access?.length ? raw.quick_access : FALLBACK_DASHBOARD.quick_access,
    upcoming_exam: raw.upcoming_exam || FALLBACK_DASHBOARD.upcoming_exam,
  };
}

export function isDashboardApiError(err) {
  const status = err?.response?.status;
  return status === 404 || status === 0 || !err?.response;
}
