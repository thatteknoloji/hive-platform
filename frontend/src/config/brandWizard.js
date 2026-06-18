/** HIVE V3 Brand Wizard — Sprint 2 UX constants */

export const BRAND_PERSONALITIES = [
  { id: "guven_veren", label: "Güven Veren", icon: "🛡", desc: "Sağlam, güvenilir, profesyonel" },
  { id: "premium", label: "Premium", icon: "✦", desc: "Seçkin, kaliteli, üst segment" },
  { id: "kurumsal", label: "Kurumsal", icon: "🏢", desc: "Resmi, ciddi, kurumsal kimlik" },
  { id: "samimi", label: "Samimi", icon: "🤝", desc: "Sıcak, yakın, insan odaklı" },
  { id: "eglenceli", label: "Eğlenceli", icon: "🎉", desc: "Enerjik, neşeli, dinamik" },
  { id: "genc", label: "Genç", icon: "⚡", desc: "Trend, cesur, dijital native" },
  { id: "otoriter", label: "Otoriter", icon: "👑", desc: "Lider, güçlü, uzman" },
  { id: "ultra_luks", label: "Ultra Lüks", icon: "💎", desc: "Eksklüzif, sofistike, elit" },
  { id: "yerel", label: "Yerel", icon: "📍", desc: "Mahalle ruhu, yerel bağ" },
  { id: "modern", label: "Modern", icon: "◆", desc: "Çağdaş, temiz, yenilikçi" },
];

export const DESIGN_DNA = [
  { id: "luxury", label: "Luxury", icon: "✦", tagline: "Altın detaylar, serif tipografi", layout: "hero-split", mood: "dark" },
  { id: "premium", label: "Premium", icon: "◇", tagline: "Geniş boşluk, zarif hiyerarşi", layout: "hero-center", mood: "light" },
  { id: "modern_startup", label: "Modern Startup", icon: "🚀", tagline: "Bold başlıklar, gradient aksan", layout: "hero-gradient", mood: "vibrant" },
  { id: "corporate", label: "Corporate", icon: "🏛", tagline: "Grid düzen, güven veren yapı", layout: "grid-corporate", mood: "neutral" },
  { id: "minimal", label: "Minimal", icon: "○", tagline: "Az element, maksimum netlik", layout: "minimal", mood: "light" },
  { id: "editorial", label: "Editorial", icon: "📰", tagline: "Magazin akışı, tipografi odaklı", layout: "editorial", mood: "paper" },
  { id: "bold", label: "Bold", icon: "▣", tagline: "Güçlü kontrast, büyük tipografi", layout: "bold-stack", mood: "contrast" },
  { id: "dark_elite", label: "Dark Elite", icon: "🌑", tagline: "Koyu tema, neon aksanlar", layout: "dark-hero", mood: "dark" },
  { id: "hotel_luxury", label: "Hotel Luxury", icon: "🏨", tagline: "Tam ekran görsel, rezervasyon CTA", layout: "hotel-hero", mood: "warm-dark" },
  { id: "fashion_elegant", label: "Fashion Elegant", icon: "👗", tagline: "Lookbook grid, ince çizgiler", layout: "fashion-grid", mood: "mono" },
  { id: "marketplace", label: "Marketplace", icon: "🛒", tagline: "Ürün kartları, filtre bar", layout: "product-grid", mood: "commerce" },
  { id: "medical_clean", label: "Medical Clean", icon: "🏥", tagline: "Temiz beyaz, güven ikonları", layout: "medical", mood: "clinical" },
  { id: "nightlife", label: "Nightlife", icon: "🌃", tagline: "Koyu arka plan, canlı renkler", layout: "night-hero", mood: "neon" },
];

export const COLOR_IDENTITIES = [
  { id: "gold_luxury", label: "Gold Luxury", icon: "✦", swatch: ["#c9a962", "#1a1410", "#f5f0e8"], accent: "#c9a962" },
  { id: "midnight_black", label: "Midnight Black", icon: "🌑", swatch: ["#0a0a0f", "#1e1e2e", "#6366f1"], accent: "#6366f1" },
  { id: "emerald_green", label: "Emerald Green", icon: "🌿", swatch: ["#064e3b", "#10b981", "#ecfdf5"], accent: "#10b981" },
  { id: "ocean_blue", label: "Ocean Blue", icon: "🌊", swatch: ["#0c4a6e", "#0ea5e9", "#e0f2fe"], accent: "#0ea5e9" },
  { id: "sunset_orange", label: "Sunset Orange", icon: "🌅", swatch: ["#7c2d12", "#f97316", "#fff7ed"], accent: "#f97316" },
  { id: "royal_purple", label: "Royal Purple", icon: "👑", swatch: ["#3b0764", "#a855f7", "#faf5ff"], accent: "#a855f7" },
  { id: "titanium_gray", label: "Titanium Gray", icon: "⚙", swatch: ["#1f2937", "#6b7280", "#f3f4f6"], accent: "#6b7280" },
  { id: "pure_white", label: "Pure White", icon: "◻", swatch: ["#ffffff", "#f8fafc", "#0f172a"], accent: "#0f172a" },
  { id: "custom", label: "Custom", icon: "🎨", swatch: ["#6366f1", "#8b5cf6", "#ec4899"], accent: "#6366f1" },
];

export const CONVERSION_GOALS = [
  { id: "lead_topla", label: "Lead Topla", icon: "📋", desc: "Form doldurma, iletişim bilgisi" },
  { id: "rezervasyon", label: "Rezervasyon Al", icon: "📅", desc: "Randevu ve rezervasyon akışı" },
  { id: "urun_sat", label: "Ürün Sat", icon: "🛒", desc: "E-ticaret dönüşümü" },
  { id: "telefon", label: "Telefon Çaldır", icon: "📞", desc: "Doğrudan arama CTA" },
  { id: "whatsapp", label: "WhatsApp Mesajı Al", icon: "💬", desc: "Anlık mesajlaşma" },
  { id: "marka", label: "Marka Oluştur", icon: "✨", desc: "Marka bilinirliği ve prestij" },
  { id: "seo_dominasyon", label: "SEO Dominasyonu", icon: "📈", desc: "Organik arama liderliği" },
  { id: "geo_dominasyon", label: "GEO Dominasyonu", icon: "🌍", desc: "Yerel ve AI arama görünürlüğü" },
  { id: "yerel_liderlik", label: "Yerel Liderlik", icon: "📍", desc: "Bölgesel pazar hakimiyeti" },
];

export const PERSONALITY_BY_ID = Object.fromEntries(BRAND_PERSONALITIES.map((p) => [p.id, p]));
export const DESIGN_DNA_BY_ID = Object.fromEntries(DESIGN_DNA.map((d) => [d.id, d]));
export const COLOR_BY_ID = Object.fromEntries(COLOR_IDENTITIES.map((c) => [c.id, c]));
export const GOAL_BY_ID = Object.fromEntries(CONVERSION_GOALS.map((g) => [g.id, g]));

export function personalityLabels(ids = []) {
  return (ids || []).map((id) => PERSONALITY_BY_ID[id]?.label || id).filter(Boolean);
}

export function designDnaLabel(id) {
  return DESIGN_DNA_BY_ID[id]?.label || id || "—";
}

export function colorIdentityLabel(id) {
  return COLOR_BY_ID[id]?.label || id || "—";
}

export function conversionGoalLabel(id) {
  return GOAL_BY_ID[id]?.label || id || "—";
}

export function buildDesignPayload(form) {
  return {
    wizard_version: 2,
    brand_personality: form.brand_personality || [],
    design_dna: form.design_dna || "",
    color_identity: form.color_identity || "",
    custom_color: form.custom_color || "",
    conversion_goal: form.conversion_goal || "",
    creative_director_brief: form.creative_director_brief || "",
  };
}
