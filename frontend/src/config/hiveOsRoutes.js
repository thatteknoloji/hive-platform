/** HIVE OS sayfa id ↔ URL path eşlemesi (Phase 3 — full deep links) */

export const HIVE_OS_ROUTES = {
  dashboard: "/",
  mission_control_center: "/mission-control",
  hive_brain_engine: "/hive-brain",
  hive_academy: "/hive-academy",
  hive_mentor: "/hive-mentor",
  first_run_wizard: "/first-run-wizard",
  hive_success_path: "/success-path",
  executive_ai: "/executive-ai",
  autonomous_seo_agent: "/autonomous-agent",
  action_orchestrator: "/action-orchestrator",
  production_readiness_engine: "/production-readiness",
  projects: "/projects",
  users: "/users",
  provider_control_center: "/provider-control-center",
  hive_audit_engine: "/hive-audit-engine",
  campaign_engine: "/campaign-engine",
  citation_engine: "/citation-engine",
  authority_factory: "/authority-factory",
  revenue_lead_engine: "/revenue-leads",
  talon: "/talon",
  rank_index_watcher: "/rank-watcher",
  serp_defense_engine: "/serp-defense",
  opportunity_engine: "/opportunity",
  data_miner_engine: "/data-miner",
  crawl_gap_engine: "/crawl-gap",
  question_intelligence_engine: "/qie",
  content_refresh_engine: "/content-refresh",
  astro_factory: "/astro-factory",
  astro_auto_publisher: "/astro-auto-publisher",
  publisher_hub: "/publisher-hub",
  authority_mesh_engine: "/authority-mesh",
  support_network_engine: "/support-network",
  network_replicator: "/network-replicator",
  site_replicator: "/site-replicator",
  blogger: "/workers/blogger",
  tumblr: "/workers/tumblr",
  wordpress: "/workers/wordpress",
  apikeys: "/settings/api",
  listing_hub: "/utilities",
  seo_quality_gate: "/diagnostics",
  kefen: "/kefen",
  zeus: "/zeus",
  mystic: "/mystic",
  ranktracker: "/ranktracker",
  webscraper: "/webscraper",
  leadscraper: "/leadscraper",
  medium_bot: "/medium-bot",
  seo_poisoning: "/seo-poisoning",
  reddit: "/reddit",
  maps: "/maps",
  btk: "/btk",
  expireddomain: "/expired-domains",
  backlinkhijacker: "/backlink-hijacker",
  spambacklink: "/spam-backlink",
  apihunter: "/api-hunter",
  analytics: "/analytics",
  conversion: "/conversion",
  abtest: "/ab-test",
  heatmap: "/heatmap",
  funnel: "/funnel",
  citation: "/citation",
  review: "/review",
  trend: "/trend",
  sentiment: "/sentiment",
  forecast: "/forecast",
  alert: "/alerts",
  notification: "/notifications",
  report: "/reports",
  schedule: "/schedule",
  backup: "/backup",
  restore: "/restore",
  log: "/logs",
  monitor: "/monitor",
  debug: "/debug",
  place_seo_pipeline: "/place-seo",
  page_hub: "/page-hub",
  category_hub: "/category-hub",
  entity_geo_graph: "/entity-geo",
  entity_detail_generator: "/entity-detail",
  indexing_fix: "/indexing-fix",
  backlink_suite: "/backlink-suite",
  sss_automation: "/sss-automation",
  ai_chat: "/ai-chat",
  replicator: "/replicator",
  exposedkeyhunter: "/exposed-keys",
};

const PATH_TO_ID = Object.entries(HIVE_OS_ROUTES).reduce((acc, [id, path]) => {
  acc[path] = id;
  return acc;
}, {});

/** /projects, /projects/new, /projects/{id} */
export function parseProjectsPath(pathname) {
  const path = (pathname || "/").replace(/\/$/, "") || "/";
  if (path === "/projects") return { mode: "list" };
  if (path === "/projects/new") return { mode: "wizard" };
  const m = path.match(/^\/projects\/([^/]+)$/);
  if (m) {
    const projectId = decodeURIComponent(m[1]);
    if (projectId !== "new") return { mode: "detail", projectId };
  }
  return null;
}

export function gostergeFromPath(pathname, search = "") {
  const projectsRoute = parseProjectsPath(pathname);
  if (projectsRoute) {
    if (projectsRoute.mode === "wizard") return "project_wizard";
    if (projectsRoute.mode === "detail") return `project_detail:${projectsRoute.projectId}`;
    return "projects";
  }
  const path = (pathname || "/").replace(/\/$/, "") || "/";
  const id = PATH_TO_ID[path] || null;
  if (id === "authority_mesh_engine") {
    const tab = new URLSearchParams(search || "").get("tab");
    if (tab) {
      try {
        sessionStorage.setItem("hive_mesh_tab", tab);
        window.dispatchEvent(new Event("hive-mesh-tab"));
      } catch {
        /* ignore */
      }
    }
  }
  return id;
}

export function pathFromGosterge(id, opts = {}) {
  if (id === "project_wizard") return "/projects/new";
  if (id && String(id).startsWith("project_detail:")) {
    return `/projects/${String(id).slice("project_detail:".length)}`;
  }
  const base = HIVE_OS_ROUTES[id];
  if (!base) return null;
  if (id === "authority_mesh_engine" && opts.meshTab) {
    return `${base}?tab=${encodeURIComponent(opts.meshTab)}`;
  }
  return base;
}

export function hasDeepRoute(id) {
  return Boolean(HIVE_OS_ROUTES[id]);
}
