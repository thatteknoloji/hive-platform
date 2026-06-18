/** HIVE OS sidebar — grouped navigation (Phase 3 cleanup) */

export const HIVE_OS_NAV_GROUPS = [
  {
    id: "command",
    label: "COMMAND",
    defaultOpen: true,
    items: [
      { id: "mission_control_center", label: "Mission Control", short: "War Room", icon: "◆", primary: true },
      { id: "hive_brain_engine", label: "HIVE Brain", short: "Memory", icon: "🧠" },
      { id: "executive_ai", label: "Executive AI", short: "CEO", icon: "👔" },
      { id: "autonomous_seo_agent", label: "Autonomous Agent", short: "Agent", icon: "🤖" },
      { id: "action_orchestrator", label: "Action Orchestrator", short: "Ops", icon: "⚡", primary: true },
      { id: "production_readiness_engine", label: "Production Readiness", short: "Launch", icon: "🚀", primary: true },
      { id: "users", label: "Users & Roles", short: "RBAC", icon: "👥", primary: true },
    ],
  },
  {
    id: "seo_core",
    label: "SEO CORE",
    defaultOpen: true,
    items: [
      { id: "talon", label: "Talon", icon: "🎯" },
      { id: "rank_index_watcher", label: "Rank Watcher", icon: "📈" },
      { id: "serp_defense_engine", label: "SERP Defense", icon: "🛡" },
      { id: "opportunity_engine", label: "Opportunity", icon: "⚡" },
      { id: "data_miner_engine", label: "Data Miner", icon: "⛏" },
      { id: "citation_engine", label: "Citation Engine", icon: "📚" },
      { id: "campaign_engine", label: "Campaign Engine", icon: "🎯" },
      { id: "crawl_gap_engine", label: "Crawl Gap", icon: "🕷" },
    ],
  },
  {
    id: "content",
    label: "CONTENT",
    items: [
      { id: "question_intelligence_engine", label: "QIE", icon: "❓" },
      { id: "content_refresh_engine", label: "Content Refresh", icon: "♻️" },
      { id: "astro_factory", label: "Astro Factory", icon: "🏭" },
      { id: "astro_auto_publisher", label: "Astro Auto Publisher", icon: "🚀" },
      { id: "publisher_hub", label: "Publisher Hub", icon: "📢", primary: true },
    ],
  },
  {
    id: "network",
    label: "NETWORK",
    items: [
      { id: "authority_mesh_engine", label: "Authority Mesh", icon: "🌎", primary: true },
      { id: "authority_factory", label: "Authority Factory", icon: "🏭" },
      { id: "revenue_lead_engine", label: "Revenue / Lead Engine", icon: "💰", primary: true },
      { id: "support_network_engine", label: "Support Network", icon: "🌐" },
      { id: "network_replicator", label: "Network Replicator", icon: "🧬" },
      { id: "site_replicator", label: "Site Replicator", icon: "📋" },
    ],
  },
  {
    id: "workers",
    label: "WORKERS",
    items: [
      { id: "authority_mesh_engine", label: "Google Sites", icon: "📄", meshTab: "google_sites" },
      { id: "authority_mesh_engine", label: "GitHub Pages", icon: "🐙", meshTab: "github_pages" },
      { id: "blogger", label: "Blogger", icon: "📰" },
      { id: "tumblr", label: "Tumblr", icon: "📝" },
      { id: "wordpress", label: "WordPress", icon: "🌐" },
    ],
  },
  {
    id: "learn",
    label: "LEARN",
    defaultOpen: true,
    items: [
      { id: "hive_academy", label: "HIVE Academy", icon: "🎓", primary: true },
      { id: "hive_mentor", label: "HIVE Mentor", icon: "🧭" },
      { id: "first_run_wizard", label: "First Run Wizard", icon: "🚀" },
      { id: "hive_success_path", label: "Success Path", icon: "🛤", primary: true },
    ],
  },
  {
    id: "tools",
    label: "TOOLS",
    items: [
      { id: "apikeys", label: "API Settings", icon: "🔑" },
      { id: "provider_control_center", label: "Provider Control Center", icon: "🔌", primary: true },
      { id: "hive_audit_engine", label: "HIVE Audit Engine", icon: "🧪" },
      { id: "listing_hub", label: "Utilities", icon: "🧰" },
      { id: "seo_quality_gate", label: "Diagnostics", icon: "🔬" },
    ],
  },
];

export const HIVE_OS_DASHBOARD = { id: "dashboard", label: "Dashboard", icon: "📊", short: "Home" };
export const HIVE_OS_PROJECTS = { id: "projects", label: "Projects", icon: "🌐", short: "Domains" };

export const HIVE_OS_PRIMARY_IDS = new Set(
  [HIVE_OS_PROJECTS.id, ...HIVE_OS_NAV_GROUPS.flatMap((g) => g.items.map((i) => i.id))]
);

/** Flat nav items for command palette + search */
export function flattenNavItems() {
  const items = [
    { ...HIVE_OS_DASHBOARD, group: "Home", keys: ["home", "dashboard"] },
    { ...HIVE_OS_PROJECTS, group: "Home", keys: ["projects", "domains"] },
  ];
  HIVE_OS_NAV_GROUPS.forEach((g) => {
    g.items.forEach((item) => {
      items.push({
        ...item,
        group: g.label,
        keys: [
          item.id.replace(/_/g, " "),
          item.label.toLowerCase(),
          item.short?.toLowerCase(),
          g.label.toLowerCase(),
        ].filter(Boolean),
      });
    });
  });
  return items;
}

/** Palette quick actions (no navigation id — action handlers in palette) */
export const HIVE_OS_QUICK_ACTIONS = [
  { id: "action:refresh-mcc", label: "Refresh War Room", group: "Quick Actions", keys: ["refresh", "reload", "war room"], icon: "↻" },
  { id: "action:open-mcc", label: "Open Mission Control", group: "Quick Actions", keys: ["open mission", "war room", "mcc"], icon: "◆", navId: "mission_control_center" },
  { id: "action:open-campaigns", label: "Open Campaign Engine", group: "Quick Actions", keys: ["open campaign", "campaigns"], icon: "🎯", navId: "campaign_engine" },
  { id: "action:open-mesh", label: "Open Authority Mesh", group: "Quick Actions", keys: ["open authority", "authority mesh", "mesh"], icon: "🌎", navId: "authority_mesh_engine" },
  { id: "action:open-revenue", label: "Open Revenue Engine", group: "Quick Actions", keys: ["open revenue", "search revenue", "leads"], icon: "💰", navId: "revenue_lead_engine" },
  { id: "action:open-brain", label: "Open HIVE Brain", group: "Quick Actions", keys: ["open brain", "search brain", "memory"], icon: "🧠", navId: "hive_brain_engine" },
  { id: "action:open-providers", label: "Open Provider Control", group: "Quick Actions", keys: ["open provider", "search providers", "api"], icon: "🔌", navId: "provider_control_center" },
  { id: "action:open-serp", label: "Open SERP Defense", group: "Quick Actions", keys: ["serp", "defense", "fortress"], icon: "🛡", navId: "serp_defense_engine" },
  { id: "action:open-publish", label: "Open Publisher Hub", group: "Quick Actions", keys: ["publish", "publisher"], icon: "📢", navId: "publisher_hub" },
];

/** Build dynamic palette rows from War Room dashboard (no extra API) */
export function buildPaletteContextItems(dash) {
  if (!dash) return [];
  const items = [];

  (dash.campaign_status?.recent_campaigns || []).slice(0, 8).forEach((c, i) => {
    const kw = c.keyword || c.primary_keyword || c.name || "";
    items.push({
      id: `ctx:campaign:${c.campaign_id || i}`,
      label: `Campaign · ${c.name || kw || "Untitled"}`,
      group: "Open Campaign",
      keys: [kw, c.name, "campaign", "open campaign"].filter(Boolean).map(String),
      icon: "🎯",
      navId: "campaign_engine",
      hint: kw,
    });
  });

  (dash.growth_opportunities || []).slice(0, 8).forEach((o, i) => {
    const kw = o.keyword || o.title || o.opportunity || "";
    items.push({
      id: `ctx:keyword:${i}`,
      label: `Keyword · ${kw}`,
      group: "Open Keyword",
      keys: [kw, "keyword", "open keyword"].filter(Boolean).map(String),
      icon: "⚔",
      navId: "serp_defense_engine",
    });
  });

  const domains = new Set();
  (dash.authority_status?.by_provider ? Object.keys(dash.authority_status.by_provider) : []).forEach((d) => domains.add(d));
  (dash.revenue_status?.no_lead_high_traffic_pages || []).slice(0, 5).forEach((p) => {
    const d = typeof p === "string" ? p : p.domain || p.url || p.page;
    if (d) domains.add(String(d).replace(/^https?:\/\//, "").split("/")[0]);
  });
  [...domains].slice(0, 8).forEach((d, i) => {
    items.push({
      id: `ctx:domain:${i}`,
      label: `Domain · ${d}`,
      group: "Open Domain",
      keys: [d, "domain", "open domain"],
      icon: "🌐",
      navId: "authority_mesh_engine",
    });
  });

  (dash.recent_events || []).slice(0, 10).forEach((e, i) => {
    const msg = e.message || e.summary || e.title || "Event";
    items.push({
      id: `ctx:event:${e.id || i}`,
      label: `Event · ${msg.slice(0, 48)}`,
      group: "Search Events",
      keys: [msg, e.module, "event", "search events"].filter(Boolean).map(String),
      icon: "📡",
      navId: "hive_brain_engine",
      hint: msg,
    });
  });

  (dash.provider_status?.provider_alerts || []).slice(0, 6).forEach((p, i) => {
    items.push({
      id: `ctx:provider:${i}`,
      label: `Provider · ${p.provider || p.name || "Alert"}`,
      group: "Search Providers",
      keys: [p.provider, p.name, p.message, "provider"].filter(Boolean).map(String),
      icon: "🔌",
      navId: "provider_control_center",
    });
  });

  return items;
}
