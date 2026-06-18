/** 🏴‍☠️ BLACK FLAG — sidebar modül kaydı (27 adet) */

export const BLACK_FLAG_GROUP = "🏴‍☠️ BLACK FLAG";

export const BLACK_FLAG_MODULES = [
  { id: "zeus", label: "Zeus'un Yıldırımı", dedicated: true },
  { id: "kefen", label: "KEFEN (Catastrophe)", dedicated: true },
  { id: "mystic", label: "Mystic Return", dedicated: true },
  { id: "reddit_mcp", label: "Reddit MCP Yöneticisi", dedicated: true },
  { id: "medium_bot", label: "Medium Bot", dedicated: true },
  { id: "maps", label: "Maps Saldırı Botu (Sim)", dedicated: true },
  { id: "btk", label: "BTK Gargoyle", dedicated: true },
  { id: "phishing", label: "Phishing (Google Cloud)", dedicated: false },
  { id: "zeroday", label: "0-Day Exploit Avcısı", dedicated: false },
  { id: "blackops", label: "Full Black Ops", dedicated: false },
  { id: "backlinkhijacker", label: "Backlink Hijacker", dedicated: true },
  { id: "spambacklink", label: "Spam Backlink Zehirleyici", dedicated: true },
  { id: "competitor_hijacker", label: "Competitor Backlink Hijacker", dedicated: false },
  { id: "backlink_hunter", label: "Backlink Hunter (Free)", dedicated: false },
  { id: "backlink_suite", label: "Backlink Suite", dedicated: true },
  { id: "linksprayer", label: "LinkSprayer", dedicated: false },
  { id: "seo_poisoning", label: "SEO Poisoning", dedicated: true },
  { id: "click_fraud", label: "Click Fraud", dedicated: false },
  { id: "click_bombing", label: "Click Bombing", dedicated: false },
  { id: "fake_ilan", label: "Fake İlan Patlatma", dedicated: false },
  { id: "brute_force", label: "Brute Force", dedicated: false },
  { id: "sql_injection", label: "SQL Injection", dedicated: false },
  { id: "itibar_saldiri", label: "Trustpilot / Şikayetvar Saldırısı", dedicated: false },
  { id: "spam_backlink", label: "Negative SEO", gosterge: "spambacklink", dedicated: true },
  { id: "expireddomain", label: "Expired Domain Avcısı", dedicated: true },
  { id: "sosyal_medida_hijack", label: "Sosyal Medya Hesap Çalma", dedicated: false },
  { id: "deepfake", label: "Deepfake / İtibar Katliamı", dedicated: false },
];

export const BLACK_FLAG_IDS = new Set(BLACK_FLAG_MODULES.map((m) => m.id));

/** Sidebar path: /black/{id} */
export function blackFlagPath(moduleId) {
  return `/black/${moduleId}`;
}

/** gosterge state key (alias destekli) */
export function blackFlagGosterge(moduleId) {
  const mod = BLACK_FLAG_MODULES.find((m) => m.id === moduleId);
  return mod?.gosterge || moduleId;
}

export function parseBlackFlagPath(pathname) {
  const m = (pathname || "").match(/^\/black\/([a-z0-9_]+)\/?$/i);
  if (!m) return null;
  const id = m[1].toLowerCase();
  return BLACK_FLAG_IDS.has(id) ? id : null;
}
