export function formatDuration(sec) {
  if (!sec) return "0 dk";
  const m = Math.round(sec / 60);
  if (m < 60) return `${m} dk`;
  return `${Math.floor(m / 60)} sa ${m % 60} dk`;
}

export function formatRelativeDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return "Bugün";
    if (days === 1) return "Dün";
    if (days < 7) return `${days} gün önce`;
    return d.toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
  } catch {
    return iso;
  }
}

export const DASHBOARD_LEARNING_PATH = [
  { id: "baslangic", label: "Başlangıç" },
  { id: "seo", label: "SEO" },
  { id: "geo", label: "GEO" },
  { id: "authority", label: "Authority" },
  { id: "publish", label: "Publish" },
  { id: "deploy", label: "Deploy" },
  { id: "advanced", label: "Advanced" },
  { id: "enterprise", label: "Enterprise" },
];

export const QUICK_ACCESS_ITEMS = [
  { id: "mission_control_center", label: "Command Center", icon: "◆", desc: "War Room" },
  { id: "projects", label: "Project Manager", icon: "🌐", desc: "Projeler" },
  { id: "publisher_hub", label: "Publisher Hub", icon: "📢", desc: "Yayın" },
  { id: "seo_quality_gate", label: "Quality Gate", icon: "🔬", desc: "Diagnostics" },
  { id: "rank_index_watcher", label: "Rank Watcher", icon: "📈", desc: "Sıra & Index" },
  { id: "authority_factory", label: "Authority Factory", icon: "🏭", desc: "Otorite" },
];

const STEP_MAP = {
  baslangic: "baslangic", firma: "baslangic", domain: "baslangic",
  seo: "seo", entity: "seo", geo: "geo",
  authority: "authority", publisher: "publish", publish: "publish",
  deploy: "deploy", advanced: "advanced", developer: "advanced",
  automation: "advanced", blackops: "advanced", enterprise: "enterprise",
};

export function mapToDashboardStep(apiStep) {
  return STEP_MAP[apiStep] || apiStep || "baslangic";
}
