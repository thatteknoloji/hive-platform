import React, { memo, useMemo } from "react";
import { HiveLiveEventStream } from "./HiveLiveEventStream";

function toneClass(score, invert = false) {
  const n = Number(score) || 0;
  if (invert) {
    if (n >= 70) return "danger";
    if (n >= 40) return "warning";
    return "success";
  }
  if (n >= 75) return "success";
  if (n >= 50) return "warning";
  return "danger";
}

export function HiveStatusPill({ label, tone = "neutral", size = "sm" }) {
  return <span className={`hive-pill hive-pill-${tone} hive-pill-${size}`}>{label}</span>;
}

function buildThreatFeed(dash) {
  const items = [];
  (dash?.active_threats || []).forEach((t, i) => {
    items.push({
      id: `serp-${i}`,
      category: "SERP",
      title: t.keyword || t.title || t.message || "SERP düşüşü",
      detail: t.reason || t.type || "Ranking pressure",
      severity: (t.severity || "").toLowerCase().includes("critical") ? "critical" : "warning",
      link: "serp_defense_engine",
    });
  });
  (dash?.audit_status?.top_critical || []).forEach((a, i) => {
    items.push({
      id: `audit-${i}`,
      category: "Audit",
      title: a.title || a.issue || a.message || "Kritik audit",
      detail: a.module || a.area || "Sistem denetimi",
      severity: "critical",
      link: "hive_audit_engine",
    });
  });
  (dash?.provider_status?.provider_alerts || []).forEach((p, i) => {
    items.push({
      id: `provider-${i}`,
      category: "Provider",
      title: p.provider || p.name || "Provider",
      detail: p.message || p.status || "API hatası",
      severity: (p.severity || "").toLowerCase().includes("critical") ? "critical" : "warning",
      link: "apikeys",
    });
  });
  const pub = dash?.publisher_status || {};
  if (Number(pub.failed) > 0) {
    items.push({
      id: "pub-failed",
      category: "Queue",
      title: `${pub.failed} yayın hatası`,
      detail: "Publisher Hub failed jobs",
      severity: "critical",
      link: "publisher_hub",
    });
  }
  if (Number(pub.queued) > 20) {
    items.push({
      id: "pub-queue",
      category: "Queue",
      title: `${pub.queued} kuyrukta`,
      detail: "Publish backlog",
      severity: "warning",
      link: "publisher_hub",
    });
  }
  if (Number(dash?.audit_status?.stuck_queues) > 0) {
    items.push({
      id: "stuck-queue",
      category: "Queue",
      title: `${dash.audit_status.stuck_queues} takılı kuyruk`,
      detail: "Stuck processing",
      severity: "warning",
      link: "publisher_hub",
    });
  }
  return items.slice(0, 12);
}

function MiniCampaignRoadmap({ progress = 0 }) {
  const weeks = ["W1", "W2", "W3", "W4", "W5+"];
  const activeIdx = Math.min(4, Math.floor(progress / 20));
  return (
    <div className="hive-war-mini-roadmap">
      {weeks.map((w, i) => (
        <div key={w} className={`hive-war-mini-week ${i <= activeIdx ? "lit" : ""} ${i === activeIdx ? "active" : ""}`}>
          <span>{w}</span>
        </div>
      ))}
    </div>
  );
}

export const WarRoomSkeleton = memo(function WarRoomSkeleton() {
  return (
    <div className="hive-war-room hive-war-skeleton" aria-busy="true">
      <div className="hive-war-header hive-skel-block" style={{ height: 72 }} />
      <div className="hive-war-metrics">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="hive-war-metric hive-skel-block" />
        ))}
      </div>
      <div className="hive-war-grid">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="hive-war-panel hive-skel-block" style={{ minHeight: 320 }} />
        ))}
      </div>
      <div className="hive-war-stream hive-skel-block" style={{ minHeight: 120 }} />
    </div>
  );
});

export const HiveWarRoom = memo(function HiveWarRoom({
  dash,
  loading,
  onNavigate,
  onRefresh,
  onLoadFull,
  onOpenPalette,
}) {
  const metrics = useMemo(() => {
    const d = dash || {};
    const rev = d.revenue_status || {};
    const camp = d.campaign_status || {};
    const auth = d.authority_status || {};
    const threats = (d.active_threats?.length || 0) + (d.audit_status?.critical_audit_issues || 0);
    return [
      { key: "health", label: "Global Health", value: d.system_health ?? "—", unit: "/100", tone: toneClass(d.system_health), link: "mission_control_center" },
      { key: "readiness", label: "Production Readiness", value: d.readiness_status?.overall_score ?? "—", unit: "%", tone: toneClass(d.readiness_status?.overall_score), link: "production_readiness_engine" },
      { key: "campaigns", label: "Active Campaigns", value: camp.active_campaigns ?? 0, unit: `score ${camp.campaign_progress_avg ?? 0}`, tone: Number(camp.active_campaigns) > 0 ? "success" : "neutral", link: "campaign_engine" },
      { key: "threats", label: "Critical Threats", value: threats, unit: threats > 0 ? "live" : "clear", tone: threats > 0 ? "danger" : "success", link: "serp_defense_engine" },
      { key: "revenue", label: "Today's Revenue", value: rev.revenue_opportunity ?? rev.today_leads ?? 0, unit: `${rev.today_leads ?? 0} leads`, tone: Number(rev.today_leads) > 0 ? "success" : "neutral", link: "revenue_lead_engine" },
      { key: "authority", label: "Authority Sources", value: auth.sites_count ?? 0, unit: `${auth.published_count ?? 0} live`, tone: Number(auth.sites_count) > 0 ? "accent" : "neutral", link: "authority_mesh_engine" },
    ];
  }, [dash]);

  const threats = useMemo(() => buildThreatFeed(dash), [dash]);
  const campStatus = dash?.campaign_status || {};
  const campaigns = useMemo(() => {
    const recent = campStatus.recent_campaigns || [];
    const top = campStatus.top_campaign;
    const list = top && !recent.find((c) => c.campaign_id === top.campaign_id) ? [top, ...recent] : recent;
    return list.slice(0, 5).map((c) => ({
      id: c.campaign_id || c.id || c.name,
      name: c.name || c.keyword || "Campaign",
      progress: c.progress_pct ?? c.progress ?? campStatus.campaign_progress_avg ?? 0,
      score: c.score ?? c.campaign_score ?? campStatus.campaign_progress_avg ?? 0,
      status: c.status || "active",
      keyword: c.keyword || c.primary_keyword,
    }));
  }, [dash, campStatus]);

  const keywordWars = useMemo(() => (
    (dash?.growth_opportunities || []).slice(0, 6).map((o, i) => ({
      id: `kw-${i}`,
      keyword: o.keyword || o.title || o.opportunity || "—",
      score: o.score ?? o.potential ?? 0,
      action: o.action || o.recommendation || "Attack",
    }))
  ), [dash]);

  const revenue = dash?.revenue_status || {};
  const topCampaign = campaigns[0];
  const sourceStatus = dash?.source_status || {};
  const go = (link) => { if (link && onNavigate) onNavigate(link); };

  const opsTiles = useMemo(() => [
    {
      key: "providers",
      label: "Providers",
      value: dash?.provider_status?.healthy_providers ?? dash?.provider_status?.healthy_count ?? "—",
      sub: `${dash?.provider_status?.failed_providers ?? dash?.provider_status?.errors ?? 0} failed`,
      tone: Number(dash?.provider_status?.failed_providers ?? dash?.provider_status?.errors) > 0 ? "danger" : "success",
      link: "provider_control_center",
    },
    {
      key: "readiness",
      label: "Readiness",
      value: dash?.readiness_status?.overall_score ?? "—",
      sub: dash?.readiness_status?.launch_mode || "beta",
      tone: toneClass(dash?.readiness_status?.overall_score),
      link: "production_readiness_engine",
    },
    {
      key: "brain",
      label: "Brain Events",
      value: (dash?.recent_events || []).length,
      sub: "last 24h stream",
      tone: "accent",
      link: "hive_brain_engine",
    },
    {
      key: "orchestrator",
      label: "Actions Queue",
      value: (dash?.next_best_actions || []).length,
      sub: "next best",
      tone: Number(dash?.next_best_actions?.length) > 0 ? "warning" : "neutral",
      link: "action_orchestrator",
    },
  ], [dash]);

  const healthStrip = useMemo(() => {
    const auth = dash?.authority_status || {};
    const cit = dash?.citation_status || {};
    const prov = dash?.provider_status || {};
    const audit = dash?.audit_status || {};
    return [
      {
        key: "authority",
        label: "Authority Health",
        score: auth.sites_count ? Math.round((Number(auth.published_count || 0) / Math.max(auth.sites_count, 1)) * 100) : 0,
        meta: `${auth.published_count ?? 0}/${auth.sites_count ?? 0} live · ${auth.queued_tasks ?? 0} queued`,
        tone: Number(auth.login_required_tasks) > 0 ? "warning" : toneClass(auth.sites_count ? 70 : 30),
        link: "authority_mesh_engine",
      },
      {
        key: "citation",
        label: "Citation Health",
        score: cit.citation_health_score ?? 0,
        meta: `${cit.pages_tracked ?? 0} pages · ${cit.citation_risks ?? 0} risks`,
        tone: toneClass(cit.citation_health_score ?? 0),
        link: "citation_engine",
      },
      {
        key: "provider",
        label: "Provider Health",
        score: prov.provider_health_score ?? 0,
        meta: `${prov.healthy_providers ?? 0} ok · ${prov.failed_providers ?? 0} fail`,
        tone: Number(prov.failed_providers) > 0 ? "danger" : toneClass(prov.provider_health_score ?? 50),
        link: "provider_control_center",
      },
      {
        key: "audit",
        label: "Audit Status",
        score: audit.audit_score ?? 0,
        meta: `${audit.critical_audit_issues ?? 0} critical · ${audit.broken_routes ?? 0} routes`,
        tone: Number(audit.critical_audit_issues) > 0 ? "danger" : toneClass(audit.audit_score ?? 50),
        link: "hive_audit_engine",
      },
    ];
  }, [dash]);

  const sourceChips = useMemo(() => {
    return Object.entries(sourceStatus).slice(0, 10).map(([key, entry]) => ({
      key,
      label: key.replace(/_/g, " "),
      status: entry?.status || "unknown",
    }));
  }, [sourceStatus]);

  const quickLaunch = [
    { id: "campaign_engine", label: "Campaigns", icon: "🎯" },
    { id: "publisher_hub", label: "Publish", icon: "📢" },
    { id: "authority_mesh_engine", label: "Authority", icon: "🌎" },
    { id: "serp_defense_engine", label: "Defense", icon: "🛡" },
    { id: "executive_ai", label: "Executive", icon: "👔" },
    { id: "hive_brain_engine", label: "Brain", icon: "🧠" },
  ];

  if (loading && !dash) return <WarRoomSkeleton />;

  return (
    <div className="hive-war-room hive-os-enter">
      <header className="hive-war-header">
        <div className="hive-war-brand">
          <span className="hive-war-kicker">HIVE SEO OS · OPERATIONS</span>
          <h1 className="hive-war-title">WAR ROOM</h1>
          <p className="hive-war-sub">
            NASA Mission Control × Palantir — canlı operasyon merkezi
            {dash?.lite_mode && (
              <span className="hive-pill hive-pill-warning hive-pill-sm" style={{ marginLeft: 8 }}>
                Lite {dash?.response_time_ms ? `${Math.round(dash.response_time_ms)}ms` : ""}
              </span>
            )}
          </p>
        </div>
        <div className="hive-war-actions">
          {onOpenPalette && (
            <button type="button" className="hive-war-action-btn primary" onClick={onOpenPalette} title="⌘K">
              <span>⌘K</span> Command
            </button>
          )}
          <button type="button" className="hive-war-action-btn" onClick={() => go("campaign_engine")}>Campaigns</button>
          <button type="button" className="hive-war-action-btn" onClick={() => go("publisher_hub")}>Publish</button>
          <button type="button" className="hive-war-action-btn" onClick={onRefresh}>↻</button>
          {dash?.lite_mode && onLoadFull && (
            <button type="button" className="hive-war-action-btn" onClick={onLoadFull} title="Tam dashboard (ağır)">
              Full
            </button>
          )}
        </div>
      </header>

      <div className="hive-war-metrics">
        {metrics.map((m) => (
          <button key={m.key} type="button" className={`hive-war-metric tone-${m.tone}`} onClick={() => go(m.link)}>
            <span className="hive-war-metric-label">{m.label}</span>
            <span className="hive-war-metric-value">{m.value}<small>{m.unit}</small></span>
          </button>
        ))}
      </div>

      <div className="hive-war-health-strip" aria-label="Subsystem health">
        {healthStrip.map((h) => (
          <button
            key={h.key}
            type="button"
            className={`hive-war-health-tile tone-${h.tone}`}
            onClick={() => go(h.link)}
          >
            <span className="hive-war-health-label">{h.label}</span>
            <strong className="hive-war-health-score">{h.score}<small>/100</small></strong>
            <span className="hive-war-health-meta">{h.meta}</span>
          </button>
        ))}
      </div>

      <div className="hive-war-ops-strip">
        {opsTiles.map((t) => (
          <button key={t.key} type="button" className={`hive-war-ops-tile tone-${t.tone}`} onClick={() => go(t.link)}>
            <span className="hive-war-ops-label">{t.label}</span>
            <strong>{t.value}</strong>
            <span className="hive-war-ops-sub">{t.sub}</span>
          </button>
        ))}
      </div>

      {sourceChips.length > 0 && (
        <div className="hive-war-sources">
          <span className="hive-war-sources-title">Source mesh</span>
          <div className="hive-war-source-chips">
            {sourceChips.map((s) => (
              <span key={s.key} className={`hive-war-source-chip status-${s.status}`} title={s.key}>
                {s.label}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="hive-war-quick-launch">
        {quickLaunch.map((q) => (
          <button key={q.id} type="button" className="hive-war-quick-btn" onClick={() => go(q.id)}>
            <span>{q.icon}</span>
            {q.label}
          </button>
        ))}
      </div>

      <div className="hive-war-grid">
        <section className="hive-war-panel hive-war-threats">
          <header className="hive-war-panel-head">
            <span className="hive-war-panel-icon">🔥</span>
            <div><h2>THREATS</h2><p>SERP · Audit · Provider · Queue</p></div>
            <HiveStatusPill label={`${threats.length}`} tone={threats.length ? "danger" : "success"} />
          </header>
          <ul className="hive-war-threat-list">
            {threats.length === 0 ? (
              <li className="hive-war-empty">Savunma hattı temiz — tehdit yok</li>
            ) : threats.map((t) => (
              <li key={t.id}>
                <button type="button" className={`hive-war-threat-item sev-${t.severity}`} onClick={() => go(t.link)}>
                  <div className="hive-war-threat-top">
                    <HiveStatusPill label={t.category} tone={t.severity === "critical" ? "danger" : "warning"} size="xs" />
                    <HiveStatusPill label={t.severity} tone={t.severity === "critical" ? "danger" : "warning"} size="xs" />
                  </div>
                  <strong>{t.title}</strong>
                  <span>{t.detail}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="hive-war-panel hive-war-campaign">
          <header className="hive-war-panel-head">
            <span className="hive-war-panel-icon">🎯</span>
            <div><h2>ACTIVE CAMPAIGNS</h2><p>Timeline · score · keyword wars</p></div>
            <HiveStatusPill label={`${campStatus.active_campaigns ?? 0}`} tone="accent" />
          </header>

          {topCampaign && (
            <div className="hive-war-campaign-hero" onClick={() => go("campaign_engine")} role="button" tabIndex={0}>
              <div className="hive-war-campaign-hero-top">
                <strong>{topCampaign.name}</strong>
                <span className="hive-war-campaign-score">Score {topCampaign.score}</span>
              </div>
              <MiniCampaignRoadmap progress={Number(topCampaign.progress) || 0} />
              <div className="hive-war-progress lg">
                <div className="hive-war-progress-fill" style={{ width: `${Math.min(100, Number(topCampaign.progress) || 0)}%` }} />
              </div>
              <span className="hive-war-progress-label">{topCampaign.progress}% · {topCampaign.keyword || "—"}</span>
            </div>
          )}

          <div className="hive-war-campaign-list">
            {campaigns.slice(topCampaign ? 1 : 0).map((c) => (
              <button key={c.id} type="button" className="hive-war-campaign-row" onClick={() => go("campaign_engine")}>
                <div className="hive-war-campaign-top">
                  <strong>{c.name}</strong>
                  <HiveStatusPill label={`${c.score}`} tone="accent" size="xs" />
                </div>
                <div className="hive-war-progress"><div className="hive-war-progress-fill" style={{ width: `${Math.min(100, Number(c.progress) || 0)}%` }} /></div>
              </button>
            ))}
          </div>

          {keywordWars.length > 0 && (
            <div className="hive-war-keyword-wars">
              <h3>⚔ Keyword Wars</h3>
              {keywordWars.map((k) => (
                <button key={k.id} type="button" className="hive-war-kw-row" onClick={() => go("serp_defense_engine")}>
                  <span>{k.keyword}</span>
                  <HiveStatusPill label={`${k.score}`} tone="accent" size="xs" />
                  <HiveStatusPill label={k.action} tone="neutral" size="xs" />
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="hive-war-panel hive-war-revenue">
          <header className="hive-war-panel-head">
            <span className="hive-war-panel-icon">💰</span>
            <div><h2>REVENUE PULSE</h2><p>Leads · qualified · won · revenue</p></div>
          </header>
          <div className="hive-war-revenue-funnel">
            {[
              { label: "Leads", value: revenue.today_leads ?? revenue.total_leads ?? 0, tone: "accent" },
              { label: "Qualified", value: revenue.high_value_leads ?? revenue.qualified ?? 0, tone: "neutral" },
              { label: "Won", value: revenue.converted ?? revenue.won ?? 0, tone: "success" },
              { label: "Revenue", value: revenue.revenue_opportunity ?? revenue.estimated_revenue ?? 0, tone: "success" },
            ].map((s, i) => (
              <React.Fragment key={s.label}>
                {i > 0 && <span className="hive-war-rev-arrow">↓</span>}
                <button type="button" className={`hive-war-rev-stage tone-${s.tone}`} onClick={() => go("revenue_lead_engine")}>
                  <span className="hive-war-rev-num">{s.value}</span>
                  <span className="hive-war-rev-label">{s.label}</span>
                </button>
              </React.Fragment>
            ))}
          </div>
          {(revenue.recent_leads || []).slice(0, 5).map((l, i) => (
            <div key={l.id || i} className="hive-war-lead-row">
              <span>{l.source || l.page || "Lead"}</span>
              <HiveStatusPill label={l.quality || l.status || "new"} tone="neutral" size="xs" />
            </div>
          ))}
        </section>
      </div>

      <HiveLiveEventStream
        events={dash?.recent_events || []}
        onNavigate={go}
        title="Live Event Stream · Brain Timeline"
      />
    </div>
  );
});
