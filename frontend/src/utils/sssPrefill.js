/** Talon → SSS Otomasyon form aktarımı */

export const SSS_PREFILL_KEY = "hive_sss_prefill";

const IL_ILCE = {
  kuşadası: { city: "Aydın", district: "Kuşadası" },
  kusadasi: { city: "Aydın", district: "Kuşadası" },
  aydın: { city: "Aydın", district: "Efeler" },
  aydin: { city: "Aydın", district: "Efeler" },
  istanbul: { city: "İstanbul", district: "Kadıköy" },
  izmir: { city: "İzmir", district: "Konak" },
  ankara: { city: "Ankara", district: "Çankaya" },
  antalya: { city: "Antalya", district: "Muratpaşa" },
  bursa: { city: "Bursa", district: "Nilüfer" },
  muğla: { city: "Muğla", district: "Bodrum" },
  mugla: { city: "Muğla", district: "Bodrum" },
  mersin: { city: "Mersin", district: "Mezitli" },
  adana: { city: "Adana", district: "Seyhan" },
};

const SEKTOR_META = {
  escort: { category: "Escort", subcategory: "Escort ve companion hizmetleri" },
  gece_hayati: { category: "Gece Hayatı", subcategory: "Barlar, kulüpler, eğlence mekanları" },
  otel_turizm: { category: "Otel & Turizm", subcategory: "Konaklama ve tatil rehberleri" },
  restoran: { category: "Restoran & Yeme-İçme", subcategory: "Restoran, kafe ve gastronomi" },
  emlak: { category: "Emlak", subcategory: "Satılık, kiralık ve yatırım rehberleri" },
  seo_dijital: { category: "SEO & Dijital", subcategory: "Dijital pazarlama ve SEO hizmetleri" },
  saglik: { category: "Sağlık", subcategory: "Sağlık ve wellness rehberleri" },
  egitim: { category: "Eğitim", subcategory: "Kurs, eğitim ve akademi rehberleri" },
};

function normKey(s) {
  return (s || "")
    .toLowerCase()
    .replace(/ı/g, "i")
    .replace(/ü/g, "u")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c")
    .replace(/ş/g, "s")
    .replace(/ğ/g, "g");
}

function resolveLocation(sehir, seedKeyword) {
  const key = normKey(sehir);
  if (IL_ILCE[key]) return IL_ILCE[key];

  const seed = (seedKeyword || "").toLowerCase();
  for (const [k, v] of Object.entries(IL_ILCE)) {
    if (seed.includes(k) || seed.includes(v.district.toLowerCase())) return v;
  }
  return { city: sehir || "Aydın", district: sehir || "Kuşadası" };
}

function resolveCategory(sektor, sektorler) {
  const fromList = (sektorler || []).find((s) => s.id === sektor);
  if (fromList) {
    return {
      category: fromList.ad,
      subcategory: fromList.ad,
    };
  }
  return SEKTOR_META[sektor] || SEKTOR_META.gece_hayati;
}

function uniqueStrings(items, limit = 80) {
  const seen = new Set();
  const out = [];
  for (const item of items || []) {
    const s = (typeof item === "string" ? item : item?.kelime || item?.keyword || item?.title || "").trim();
    if (!s) continue;
    const k = s.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(s);
    if (out.length >= limit) break;
  }
  return out;
}

/**
 * Full SEO Research veya keyword listesinden SSS form payload üretir.
 */
export function buildSSSPrefill({
  researchSonuc = null,
  sehir = "kuşadası",
  sektor = "gece_hayati",
  sektorler = [],
  kelimeler = [],
  researchQuery = "",
  anaKelime = "",
}) {
  const seedKeyword =
    researchSonuc?.seedKeyword ||
    researchQuery?.trim() ||
    anaKelime?.trim() ||
    "kuşadası gece hayatı";

  const loc = resolveLocation(sehir, seedKeyword);
  const cat = resolveCategory(sektor, sektorler);

  const autocomplete = researchSonuc?.autocompleteKeywords || [];
  const faq = researchSonuc?.faqIdeas || researchSonuc?.peopleAlsoAskQuestions || [];
  const geoPages = (researchSonuc?.recommendedPages || []).map((p) => p.title).filter(Boolean);
  const contentAngles = researchSonuc?.contentAngles || [];
  const talonKws = kelimeler.map((k) => k.kelime).filter(Boolean);

  const extraKeywords = uniqueStrings([
    seedKeyword,
    ...autocomplete,
    ...faq.map((q) => q.replace(/\?$/, "").trim()),
    ...geoPages,
    ...contentAngles,
    ...talonKws,
  ], 100);

  const secondary = uniqueStrings([
    ...autocomplete.slice(0, 15),
    ...faq.slice(0, 10),
    ...(researchSonuc?.geoEntities || [])
      .map((g) => g.location?.neighbourhood || g.location?.district || g.title)
      .filter(Boolean),
  ], 20);

  const keywordCount = Math.min(100, Math.max(50, extraKeywords.length || 50));

  return {
    city: loc.city,
    district: loc.district,
    category: cat.category,
    subcategory: cat.subcategory,
    main_keyword: seedKeyword,
    secondary_keywords: secondary.join(", "),
    keyword_count: keywordCount,
    extra_keywords: extraKeywords,
    source: "talon",
    research_summary: {
      seedKeyword,
      serpCount: researchSonuc?.serpResults?.length || 0,
      competitorCount: researchSonuc?.competitors?.length || 0,
      faqCount: faq.length,
      geoPageCount: geoPages.length,
    },
  };
}

export function saveSSSPrefill(payload, { autoStart = false } = {}) {
  sessionStorage.setItem(
    SSS_PREFILL_KEY,
    JSON.stringify({ ...payload, autoStart, importedAt: new Date().toISOString() })
  );
}

export function loadSSSPrefill() {
  try {
    const raw = sessionStorage.getItem(SSS_PREFILL_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearSSSPrefill() {
  sessionStorage.removeItem(SSS_PREFILL_KEY);
}
