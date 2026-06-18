export const ROLE_NAV = {
  super_admin: "*",
  admin: new Set(["mission_control_center", "campaign_engine", "authority_factory", "publisher_hub", "data_miner_engine", "projects"]),
  seo_manager: new Set(["mission_control_center", "campaign_engine", "citation_engine", "authority_factory", "rank_index_watcher"]),
  editor: new Set(["publisher_hub", "data_miner_engine", "content_refresh_engine", "question_intelligence_engine"]),
  viewer: new Set(["dashboard", "mission_control_center"]),
};

export function canViewNav(role, navId) {
  const rule = ROLE_NAV[role] || ROLE_NAV.viewer;
  if (rule === "*") return true;
  return rule.has(navId) || navId === "dashboard";
}
