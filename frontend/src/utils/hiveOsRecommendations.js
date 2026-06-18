const MODULE_ROUTES = {
  serp_defense_engine: "serp_defense_engine",
  opportunity_engine: "opportunity_engine",
  crawl_gap_engine: "crawl_gap_engine",
  authority_mesh_engine: "authority_mesh_engine",
  publisher_hub: "publisher_hub",
  content_refresh_engine: "content_refresh_engine",
  rank_index_watcher: "rank_index_watcher",
  hive_brain_engine: "hive_brain_engine",
  autonomous_seo_agent: "autonomous_seo_agent",
  mission_control_center: "mission_control_center",
};

function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function healthNarrative(score) {
  const n = num(score);
  if (n >= 75) return "Sistem stabil, operasyonel";
  if (n >= 50) return "Dikkat gerektiren alanlar var";
  return "Acil müdahale önerilir";
}

export function buildOpsSummary(dash) {
  const score = dash?.system_health ?? "—";
  const threats = dash?.active_threats?.length ?? 0;
  const opps = dash?.growth_opportunities?.length ?? 0;
  const pending =
    num(dash?.authority_status?.queued_tasks)
    + num(dash?.publisher_status?.queued)
    + num(dash?.refresh_status?.queue_size);
  const auth = dash?.authority_status || {};
  const astro = dash?.worker_status?.astro_auto_publisher || {};
  const ghp = dash?.worker_status?.github_pages || {};
  const lastDeploy = astro.last_deploy_at
    || (ghp.published_count ? `${ghp.published_count} GHP yayında` : null)
    || "Henüz deploy yok";

  return [
    {
      key: "performance",
      label: "System Performance",
      value: `${dash?.performance_status?.performance_score ?? "—"}`,
      narrative: dash?.performance_status?.performance_risk != null
        ? `API ${dash?.performance_status?.api_avg_response_ms ?? "—"}ms · State ${dash?.performance_status?.total_state_kb ?? "—"}KB · risk ${dash.performance_status.performance_risk}`
        : "Performans ölçümü yükleniyor",
      tone: num(dash?.performance_status?.performance_score) >= 75 ? "success" : num(dash?.performance_status?.performance_score) >= 50 ? "warning" : "danger",
      link: "mission_control_center",
    },
    {
      key: "readiness",
      label: "Production Readiness",
      value: `${dash?.readiness_status?.overall_score ?? 0}%`,
      narrative: dash?.readiness_status?.recommendation || `${dash?.readiness_status?.launch_mode || "development"} — ${dash?.readiness_status?.blockers_count ?? 0} blocker`,
      tone: num(dash?.readiness_status?.overall_score) >= 80 && !(dash?.readiness_status?.blockers_count) ? "success" : num(dash?.readiness_status?.overall_score) >= 60 ? "warning" : "neutral",
      link: "production_readiness_engine",
    },
    {
      key: "success_path",
      label: "Success Path",
      value: `${dash?.success_path_status?.completion_percent ?? 0}%`,
      narrative: dash?.success_path_status?.next_action
        ? `${dash.success_path_status.current_goal || "Aktivasyon"} — ${String(dash.success_path_status.next_action).slice(0, 60)}`
        : "Kayıt → İlk lead yolculuğu",
      tone: num(dash?.success_path_status?.completion_percent) >= 75 ? "success" : num(dash?.success_path_status?.completion_percent) >= 40 ? "warning" : "neutral",
      link: "hive_success_path",
    },
    {
      key: "health",
      label: "System Health",
      value: score,
      narrative: `${score}/100 — ${healthNarrative(score)}`,
      tone: num(score) >= 75 ? "success" : num(score) >= 50 ? "warning" : "danger",
      link: "mission_control_center",
    },
    {
      key: "threats",
      label: "Critical Threats",
      value: threats,
      narrative: threats > 0
        ? `${threats} SERP riski aktif — savunma gerekli`
        : "Aktif tehdit tespit edilmedi",
      tone: threats > 0 ? "danger" : "success",
      link: "serp_defense_engine",
    },
    {
      key: "growth",
      label: "Growth Opportunities",
      value: opps,
      narrative: opps > 0
        ? `${opps} quick win hazır`
        : "Opportunity Engine analizi çalıştırın",
      tone: opps > 0 ? "success" : "neutral",
      link: "opportunity_engine",
    },
    {
      key: "pending",
      label: "Pending Actions",
      value: pending,
      narrative: pending > 0
        ? `${pending} görev kuyrukta bekliyor`
        : "Bekleyen operasyon yok",
      tone: pending > 0 ? "warning" : "success",
      link: "publisher_hub",
    },
    {
      key: "authority",
      label: "Authority Status",
      value: auth.sites_count ?? "—",
      narrative: `${auth.published_count ?? 0} yayında · ${auth.queued_tasks ?? 0} kuyruk`,
      tone: num(auth.login_required_tasks) > 0 ? "danger" : "info",
      link: "authority_mesh_engine",
    },
    {
      key: "deploy",
      label: "Last Deploy",
      value: typeof lastDeploy === "string" ? lastDeploy.slice(0, 18) : lastDeploy,
      narrative: astro.queued ? `${astro.queued} Astro kuyrukta` : "Worker durumu güncel",
      tone: "info",
      link: "astro_auto_publisher",
    },
  ];
}

export function buildPrimaryRecommendation(dash, extra = {}) {
  const crawl = extra.crawlGap || {};
  const opp = extra.opportunity || {};
  const agent = extra.agent || {};

  const faqGaps = num(crawl.faq_gaps ?? crawl.gap_stats?.faq_gap_count);
  const criticalGaps = num(crawl.critical_gaps ?? crawl.gap_stats?.critical_gap_count);
  const quickWinList = opp.quick_wins || opp.top_opportunities || dash?.growth_opportunities || [];
  const quickWinCount = quickWinList.length || num(opp.quick_wins ?? opp.dashboard?.quick_wins);

  if (dash?.active_threats?.length) {
    const t = dash.active_threats[0];
    return {
      headline: `${dash.active_threats.length} aktif SERP tehdidi`,
      detail: t.keyword || t.title || "Keyword riski",
      estimatedGain: t.pressure_score ? `Risk ${t.pressure_score}` : `Fortress ${t.fortress_score ?? "—"}`,
      estimatedGainLabel: "Tehdit seviyesi",
      actionLabel: "SERP Defense Aç",
      executeLabel: "Savun",
      target: "serp_defense_engine",
      source: "serp_defense_engine",
      priority: "CRITICAL",
    };
  }

  if (faqGaps > 0) {
    return {
      headline: `${faqGaps} adet FAQ açığı bulundu`,
      detail: criticalGaps > 0 ? `${criticalGaps} kritik gap birlikte` : "Crawl Gap analizi tamamlandı",
      estimatedGain: `+${Math.round(faqGaps * 156).toLocaleString("tr-TR")}`,
      estimatedGainLabel: "Tahmini trafik artışı",
      actionLabel: "Generate Cluster",
      executeLabel: "Execute Plan",
      target: "crawl_gap_engine",
      source: "crawl_gap_engine",
      priority: "HIGH",
    };
  }

  if (quickWinCount > 0) {
    const top = quickWinList[0] || {};
    return {
      headline: `${quickWinCount} Quick Win fırsatı`,
      detail: top.title || top.label || top.keyword || "Yüksek etkili anahtar kelimeler",
      estimatedGain: top.traffic_score ? `+${top.traffic_score}` : `Skor ${top.opportunity_score ?? "—"}`,
      estimatedGainLabel: "Beklenen trafik etkisi",
      actionLabel: "Opportunity Aç",
      executeLabel: "Execute Plan",
      target: "opportunity_engine",
      source: "opportunity_engine",
      priority: "HIGH",
    };
  }

  const agentActions = agent.suggested_actions || agent.recommendations || [];
  if (agentActions.length) {
    const a = agentActions[0];
    return {
      headline: a.title || a.recommended_action || "Autonomous Agent önerisi",
      detail: a.reason || a.agent_type || "Agent günlük plan üretti",
      estimatedGain: a.priority_score ? `Öncelik ${a.priority_score}` : "Yüksek etki",
      estimatedGainLabel: "Agent skoru",
      actionLabel: "Agent Planını Aç",
      executeLabel: "Execute Plan",
      target: "autonomous_seo_agent",
      source: "autonomous_seo_agent",
      priority: "HIGH",
    };
  }

  const refreshCritical = num(dash?.refresh_status?.critical_pages);
  if (refreshCritical > 0) {
    return {
      headline: `${refreshCritical} sayfa acil refresh gerektiriyor`,
      detail: "Content decay kritik eşiği aştı",
      estimatedGain: `${dash?.refresh_status?.queue_size ?? 0} kuyrukta`,
      estimatedGainLabel: "Refresh kuyruğu",
      actionLabel: "Content Refresh Aç",
      executeLabel: "Execute Plan",
      target: "content_refresh_engine",
      source: "content_refresh_engine",
      priority: "CRITICAL",
    };
  }

  return {
    headline: "Henüz analiz yapılmadı",
    detail: "Crawl Gap ve Rank Watcher ile veri toplayın — HIVE Brain otomatik öneri üretecek.",
    estimatedGain: "—",
    estimatedGainLabel: "Tahmini kazanç",
    actionLabel: "Crawl Gap Başlat",
    executeLabel: "Modüle Git",
    target: "crawl_gap_engine",
    source: "mission_control_center",
    priority: "MEDIUM",
    isGuidance: true,
  };
}

export function enrichTodayMission(dash) {
  const items = [];
  let order = 1;

  for (const t of (dash?.active_threats || []).slice(0, 1)) {
    items.push({
      id: `serp-${t.keyword || order}`,
      order: order++,
      module: "SERP Defense",
      title: t.keyword || t.title || "Keyword",
      detail: `Fortress: ${t.fortress_score ?? "—"}`,
      priority: "CRITICAL",
      impact: "high",
      gain: t.pressure_level || t.risk_type || "Position Loss",
      deep_link: "serp_defense_engine",
    });
  }

  const oppCount = dash?.growth_opportunities?.length || 0;
  if (oppCount > 0) {
    items.push({
      id: "opp-quick-wins",
      order: order++,
      module: "Opportunity",
      title: `${oppCount} Quick Win bulundu`,
      detail: dash.growth_opportunities[0]?.title || "Yüksek etki fırsatları",
      priority: "HIGH",
      impact: "high",
      gain: `Skor ${dash.growth_opportunities[0]?.opportunity_score ?? "—"}`,
      deep_link: "opportunity_engine",
    });
  }

  const queued = num(dash?.authority_status?.queued_tasks);
  if (queued > 0) {
    items.push({
      id: "auth-queued",
      order: order++,
      module: "Authority Mesh",
      title: `${queued} support site bekliyor`,
      detail: `${dash?.authority_status?.sites_count ?? 0} site ağında`,
      priority: "MEDIUM",
      impact: "medium",
      gain: `${dash?.authority_status?.published_count ?? 0} yayında`,
      deep_link: "authority_mesh_engine",
    });
  }

  const pubQ = num(dash?.publisher_status?.queued);
  if (pubQ > 0) {
    items.push({
      id: "pub-queue",
      order: order++,
      module: "Publisher",
      title: `${pubQ} içerik yayın bekliyor`,
      detail: `${dash?.publisher_status?.drafts ?? 0} taslak`,
      priority: "MEDIUM",
      impact: "high",
      gain: `${dash?.publisher_status?.published ?? 0} yayında`,
      deep_link: "publisher_hub",
    });
  }

  const seen = new Set(items.map((i) => i.title?.toLowerCase()));
  for (const m of dash?.today_mission || []) {
    if (items.length >= 8) break;
    const key = (m.title || "").toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    items.push({
      id: m.item_id || `api-${order}`,
      order: order++,
      module: (m.source_module || "Mission").replace(/_/g, " "),
      title: m.title,
      detail: m.reason,
      priority: m.priority || "MEDIUM",
      impact: "medium",
      gain: "—",
      deep_link: m.deep_link || MODULE_ROUTES[m.source_module] || "autonomous_seo_agent",
    });
  }

  return items.slice(0, 8);
}

function formatEventTime(ts) {
  if (!ts) return "--:--";
  const raw = String(ts).replace(" UTC", "Z").replace(" ", "T");
  const d = new Date(raw);
  if (!Number.isNaN(d.getTime())) {
    return d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  }
  const slice = String(ts).slice(11, 16);
  return slice || "--:--";
}

function humanizeEvent(ev) {
  const type = (ev.event_type || ev.type || "").toLowerCase();
  const mod = (ev.module || "").replace(/_/g, " ");
  if (type.includes("publish")) return "Publisher completed";
  if (type.includes("deploy")) return "Deploy completed";
  if (type.includes("threat") || type.includes("serp")) return "SERP threat detected";
  if (type.includes("refresh")) return "Content refresh completed";
  if (type.includes("mesh") || type.includes("authority")) return "Authority Mesh task created";
  if (type.includes("google")) return "Google Site published";
  if (type.includes("github")) return "GitHub Pages published";
  if (ev.reason) return ev.reason.slice(0, 72);
  if (mod) return `${mod} activity`;
  return "System event";
}

export function formatLiveEvents(events) {
  return (events || []).slice(0, 12).map((ev, i) => ({
    id: ev.id || `ev-${i}`,
    time: formatEventTime(ev.timestamp || ev.at),
    label: humanizeEvent(ev),
    module: ev.module || "hive_brain_engine",
    deep_link: MODULE_ROUTES[ev.module] || "hive_brain_engine",
  }));
}

function scoreToStatus(score) {
  const n = num(score);
  if (!n && score !== 0) return "unknown";
  if (n >= 75) return "ok";
  if (n >= 50) return "warn";
  return "err";
}

function sourceWallStatus(dash, key, scoreKey) {
  const ss = dash?.source_status?.[key];
  if (ss?.status === "not_configured") return { status: "unknown", detail: ss.message };
  if (ss?.status === "degraded") return { status: "warn", detail: ss.message };
  return { status: scoreToStatus(dash?.health_components?.[scoreKey]), detail: null };
}

export function buildModuleStatusWall(dash) {
  const c = dash?.health_components || {};
  const workers = dash?.worker_status || {};
  const gsOk = workers.google_sites?.provider_ready;
  const ghOk = workers.github_pages?.provider_ready;
  const gsSource = dash?.source_status?.google_sites;
  const ghSource = dash?.source_status?.github_pages;
  const workerDetail = gsOk && ghOk
    ? "Workers hazır"
    : (gsSource?.message || ghSource?.message || "Worker dikkat gerekli");

  const authority = sourceWallStatus(dash, "authority_mesh", "authority_health");
  const publisher = sourceWallStatus(dash, "publisher", "publish_health");
  const refresh = sourceWallStatus(dash, "refresh", "refresh_health");
  const rank = sourceWallStatus(dash, "rank", "rank_health");
  const brain = sourceWallStatus(dash, "brain", "brain_activity");

  return [
    {
      name: "Authority Mesh",
      status: authority.status,
      detail: authority.detail || `${dash?.authority_status?.queued_tasks ?? 0} kuyruk`,
      link: "authority_mesh_engine",
    },
    {
      name: "Publisher Hub",
      status: publisher.status,
      detail: publisher.detail || `${dash?.publisher_status?.queued ?? 0} bekleyen`,
      link: "publisher_hub",
    },
    {
      name: "Content Refresh",
      status: refresh.status,
      detail: refresh.detail || `${dash?.refresh_status?.critical_pages ?? 0} kritik`,
      link: "content_refresh_engine",
    },
    {
      name: "Rank Watcher",
      status: rank.status,
      detail: rank.detail || `${dash?.rank_status?.rank_drops ?? 0} düşüş`,
      link: "rank_index_watcher",
    },
    {
      name: "Workers",
      status: gsOk && ghOk ? "ok" : (gsSource?.status === "not_configured" || ghSource?.status === "not_configured" ? "unknown" : "warn"),
      detail: workerDetail,
      link: "authority_mesh_engine",
    },
    {
      name: "Brain",
      status: brain.status,
      detail: brain.detail || `${(dash?.recent_events || []).length} event`,
      link: "hive_brain_engine",
    },
  ];
}
