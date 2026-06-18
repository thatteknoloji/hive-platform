/** HIVE Academy glossary — tooltip metinleri (Academy API ile senkron tutulabilir). */

export const HIVE_CONCEPTS = {
  authority_score: {
    label: "Authority Score",
    text: "Support site ağının money site'e sağladığı güven sinyali. Yüksek skor = daha güçlü link equity dağılımı.",
    academyModule: "authority_mesh_engine",
  },
  fortress_score: {
    label: "Fortress Score",
    text: "Keyword'ün SERP'te savunma gücü (0–100). Düşük fortress = position loss riski yüksek.",
    academyModule: "serp_defense_engine",
  },
  opportunity_score: {
    label: "Opportunity Score",
    text: "Keyword büyüme potansiyeli; trafik, zorluk ve mevcut pozisyon birleşiminden hesaplanır.",
    academyModule: "opportunity_engine",
  },
  publish_queue: {
    label: "Publish Queue",
    text: "Yayına hazır içeriklerin beklediği Publisher Hub kuyruğu. Boş kuyruk = deploy fırsatı kaçırılıyor olabilir.",
    academyModule: "publisher_hub",
  },
  rank_drop: {
    label: "Rank Drop",
    text: "Rank Watcher'ın tespit ettiği pozisyon düşüşü. SERP Defense ile birlikte değerlendirilmelidir.",
    academyModule: "rank_index_watcher",
  },
  gap_score: {
    label: "Gap Score",
    text: "Crawl Gap analizinde içerik/cluster eksiklik derecesi. Yüksek gap = acil içerik ihtiyacı.",
    academyModule: "crawl_gap_engine",
  },
  quick_win: {
    label: "Quick Win",
    text: "Düşük zorluk + yüksek trafik potansiyelli keyword fırsatı.",
    academyModule: "opportunity_engine",
  },
};

export const ACADEMY_GUIDE_MODULES = {
  publisher_hub: { guideId: "guide_publisher", label: "Publisher Rehberini Aç" },
  serp_defense_engine: { guideId: "guide_serp_defense", label: "SERP Savunma Rehberini Aç" },
  opportunity_engine: { guideId: "guide_opportunity", label: "Opportunity Rehberini Aç" },
  crawl_gap_engine: { guideId: "guide_crawl_gap", label: "Crawl Gap Rehberini Aç" },
  rank_index_watcher: { guideId: "guide_rank_watcher", label: "Rank Watcher Rehberini Aç" },
  authority_mesh_engine: { guideId: "guide_authority_mesh", label: "Authority Mesh Rehberini Aç" },
};
