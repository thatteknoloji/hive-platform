/** HIVE V3 Project Engine — sektör listesi (wizard adım 1) */

export const PROJECT_SECTORS = [
  { id: "otel", label: "Otel", icon: "🏨" },
  { id: "ecommerce", label: "E-Ticaret", icon: "🛒" },
  { id: "emlak", label: "Emlak", icon: "🏠" },
  { id: "klinik", label: "Klinik", icon: "🏥" },
  { id: "veteriner", label: "Veteriner", icon: "🐾" },
  { id: "restoran", label: "Restoran", icon: "🍽" },
  { id: "rentacar", label: "Rent A Car", icon: "🚗" },
  { id: "ilan", label: "İlan Sitesi", icon: "📋" },
  { id: "blog", label: "Blog", icon: "✍️" },
  { id: "kurumsal", label: "Kurumsal", icon: "🏢" },
  { id: "ozel", label: "Özel", icon: "⚙️" },
];

export const SECTOR_BY_ID = Object.fromEntries(PROJECT_SECTORS.map((s) => [s.id, s]));

export const DEPLOY_MODES = [
  { id: "hive_cloud", label: "HIVE Cloud", desc: "Tam yönetilen HIVE altyapısı" },
  { id: "customer_agent", label: "Customer Agent", desc: "Müşteri sunucusunda HIVE agent" },
  { id: "enterprise_agent", label: "Enterprise Agent", desc: "Kurumsal izole agent dağıtımı" },
];

export const DESIGN_LAYOUTS = [
  { id: "classic", label: "Klasik" },
  { id: "modern", label: "Modern" },
  { id: "minimal", label: "Minimal" },
  { id: "bold", label: "Bold" },
];

export const COLOR_MOODS = [
  { id: "warm", label: "Sıcak" },
  { id: "cool", label: "Serin" },
  { id: "neutral", label: "Nötr" },
  { id: "vibrant", label: "Canlı" },
];

export const PROJECT_STATUSES = [
  { id: "", label: "Tümü" },
  { id: "draft", label: "Taslak" },
  { id: "building", label: "Kurulum" },
  { id: "active", label: "Aktif" },
  { id: "paused", label: "Duraklatıldı" },
  { id: "error", label: "Hata" },
];

export function sectorLabel(id) {
  return SECTOR_BY_ID[id]?.label || id || "—";
}

export function deployLabel(id) {
  return DEPLOY_MODES.find((d) => d.id === id)?.label || id || "—";
}

export function statusLabel(id) {
  return PROJECT_STATUSES.find((s) => s.id === id)?.label || id || "—";
}
