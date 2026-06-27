/** HIVE Academy V2 — modül açma, öğrenme rotası, AI hazırlık sabitleri */

import { HIVE_OS_ROUTES } from "../../config/hiveOsRoutes";

export const LEARNING_PATH = [
  { id: "baslangic", label: "Başlangıç", sectionSlugs: ["baslangic", "ilk-gun"] },
  { id: "firma", label: "Firma", sectionSlugs: ["firma-proje", "ilk-gun"] },
  { id: "domain", label: "Domain", sectionSlugs: ["firma-proje", "ilk-gun"] },
  { id: "seo", label: "SEO", sectionSlugs: ["seo-geo-aeo", "ilk-gun"] },
  { id: "geo", label: "GEO", sectionSlugs: ["seo-geo-aeo"] },
  { id: "entity", label: "Entity", sectionSlugs: ["seo-geo-aeo", "modul-ansiklopedisi"] },
  { id: "authority", label: "Authority", sectionSlugs: ["authority"] },
  { id: "publisher", label: "Publisher", sectionSlugs: ["authority", "publish-pipeline"] },
  { id: "deploy", label: "Deploy", sectionSlugs: ["deploy"] },
  { id: "advanced", label: "Advanced", sectionSlugs: ["modul-ansiklopedisi"] },
  { id: "developer", label: "Developer", sectionSlugs: ["api"] },
  { id: "automation", label: "Automation", sectionSlugs: ["modul-ansiklopedisi"] },
  { id: "blackops", label: "BlackOps", sectionSlugs: ["modul-ansiklopedisi"] },
  { id: "enterprise", label: "Enterprise", sectionSlugs: ["certification"] },
];

/** slug veya modül id → HIVE OS gosterge id */
export const MODULE_LAUNCH_MAP = {
  authority_factory: "authority_factory",
  "authority-factory": "authority_factory",
  publisher_hub: "publisher_hub",
  "publisher-hub": "publisher_hub",
  projects: "projects",
  project: "projects",
  quality_gate: "seo_quality_gate",
  "quality-gate": "seo_quality_gate",
  rank_index_watcher: "rank_index_watcher",
  talon: "talon",
  mission_control_center: "mission_control_center",
  wordpress: "wordpress",
  astro_factory: "astro_factory",
  authority_mesh_engine: "authority_mesh_engine",
  seo_quality_gate: "seo_quality_gate",
};

export function resolveModuleNavId(token) {
  const key = (token || "").trim().toLowerCase().replace(/\s+/g, "_");
  return MODULE_LAUNCH_MAP[key] || (HIVE_OS_ROUTES[key] ? key : null);
}

/** Markdown içindeki hive://module/xxx linklerini yakala */
export const MODULE_LINK_RE = /hive:\/\/module\/([a-z0-9_-]+)/gi;

// TODO V3: Academy AI — RAG over docs/academy + quizzes + API catalog
// TODO V3: Voice Search
// TODO V3: Interactive Tutorials / Sandbox Mode
// TODO V3: Certification Exams (PDF)
// TODO V3: Partner Academy / Marketplace Learning
