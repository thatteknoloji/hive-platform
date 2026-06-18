import React, { memo, useMemo } from "react";

/** Mission Control kalitesinde panel hero */
export function HivePanelHero({ kicker, title, subtitle, children }) {
  return (
    <section className="hive-os-hero hive-viz-hero">
      <div className="hive-os-hero-glow" aria-hidden />
      <div className="hive-os-hero-top">
        <div>
          {kicker && <span className="hive-os-hero-kicker">{kicker}</span>}
          {title && <h1 className="hive-os-hero-title">{title}</h1>}
          {subtitle && <p className="hive-os-hero-sub">{subtitle}</p>}
        </div>
        {children}
      </div>
    </section>
  );
}

function toneFromScore(score, invert = false) {
  const n = Number(score) || 0;
  if (invert) {
    if (n >= 70) return "danger";
    if (n >= 45) return "warning";
    return "success";
  }
  if (n >= 75) return "success";
  if (n >= 50) return "warning";
  return "danger";
}

/** Campaign Engine — kampanya fazları ve görev timeline */
export const CampaignTimeline = memo(function CampaignTimeline({ campaigns = [], tasks = [], selected = null }) {
  const items = useMemo(() => {
    const camp = selected || campaigns[0];
    const campTasks = camp
      ? tasks.filter((t) => !t.campaign_id || t.campaign_id === camp.campaign_id)
      : tasks;

    const phases = [
      { id: "plan", label: "Plan", icon: "📋" },
      { id: "authority", label: "Authority", icon: "🔗" },
      { id: "citation", label: "Citation", icon: "📚" },
      { id: "revenue", label: "Revenue", icon: "💰" },
      { id: "orchestrate", label: "Execute", icon: "⚡" },
    ];

    const phaseFor = (t) => {
      const m = (t.module || "").toLowerCase();
      const it = (t.item_type || "").toLowerCase();
      if (m.includes("authority") || it.includes("authority")) return "authority";
      if (m.includes("citation") || it.includes("citation")) return "citation";
      if (m.includes("revenue") || it.includes("revenue")) return "revenue";
      if (m.includes("orchestr") || t.status === "sent_to_orchestrator") return "orchestrate";
      return "plan";
    };

    return phases.map((ph) => {
      const related = campTasks.filter((t) => phaseFor(t) === ph.id);
      const done = related.filter((t) => ["completed", "done", "published"].includes(t.status)).length;
      const total = related.length;
      const pct = total ? Math.round((done / total) * 100) : camp?.progress ?? 0;
      return { ...ph, total, done, pct, active: total > 0 && done < total };
    });
  }, [campaigns, tasks, selected]);

  const headline = selected?.name || selected?.target_keyword || "Kampanya seçin";

  return (
    <div className="hive-viz hive-viz-timeline hive-os-enter">
      <div className="hive-viz-head">
        <span className="hive-viz-kicker">Campaign Timeline</span>
        <h3 className="hive-viz-title">{headline}</h3>
        {selected && (
          <span className="hive-viz-meta">
            {selected.status} · {selected.progress ?? 0}% · {selected.goal || "—"}
          </span>
        )}
      </div>
      <div className="hive-viz-timeline-track">
        {items.map((item, i) => (
          <div
            key={item.id}
            className={`hive-viz-timeline-node ${item.active ? "active" : ""} ${item.done === item.total && item.total > 0 ? "done" : ""}`}
          >
            <div className="hive-viz-timeline-dot">{item.icon}</div>
            {i < items.length - 1 && <div className="hive-viz-timeline-line" />}
            <div className="hive-viz-timeline-label">{item.label}</div>
            <div className="hive-viz-timeline-stat">{item.done}/{item.total || "—"}</div>
            <div className="hive-viz-timeline-bar">
              <div className="hive-viz-timeline-fill" style={{ width: `${item.pct}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

/** SERP Defense — keyword savaş odası grid */
export const KeywordWarRoom = memo(function KeywordWarRoom({ keywords = [], title = "Keyword War Room" }) {
  const rows = useMemo(() => {
    return (keywords || []).slice(0, 12).map((k) => {
      const kw = k.keyword || k.term || "—";
      const fortress = k.fortress_score ?? k.score ?? 0;
      const pressure = k.pressure_score ?? k.pressure ?? 0;
      const level = (k.pressure_level || k.level || "").toUpperCase();
      const pos = k.position ?? k.rank ?? "—";
      return { kw, fortress, pressure, level, pos, tone: toneFromScore(pressure, true) };
    });
  }, [keywords]);

  if (!rows.length) {
    return (
      <div className="hive-viz hive-viz-warroom hive-os-enter">
        <div className="hive-viz-head">
          <span className="hive-viz-kicker">{title}</span>
          <p className="hive-viz-empty">Keyword analizi yapın — fortress verisi burada görünür</p>
        </div>
      </div>
    );
  }

  return (
    <div className="hive-viz hive-viz-warroom hive-os-enter">
      <div className="hive-viz-head">
        <span className="hive-viz-kicker">{title}</span>
        <h3 className="hive-viz-title">{rows.length} keyword izleniyor</h3>
      </div>
      <div className="hive-viz-war-grid">
        {rows.map((r) => (
          <div key={r.kw} className={`hive-viz-war-card hive-viz-war-${r.tone}`}>
            <div className="hive-viz-war-kw">{r.kw}</div>
            <div className="hive-viz-war-metrics">
              <span title="Fortress">🛡 {r.fortress}</span>
              <span title="Pressure">⚡ {r.pressure}</span>
              <span title="Position">#{r.pos}</span>
            </div>
            {r.level && <span className={`hive-viz-war-badge ${r.tone}`}>{r.level}</span>}
          </div>
        ))}
      </div>
    </div>
  );
});

/** Authority Mesh — ağ grafiği (SVG) */
export const AuthorityNetworkGraph = memo(function AuthorityNetworkGraph({
  sites = [],
  moneySite = "Money Site",
  plans = [],
}) {
  const graph = useMemo(() => {
    const center = { id: "hub", label: moneySite.replace(/^https?:\/\//, "").slice(0, 24) || "Hub", x: 200, y: 120 };
    const nodes = (sites || []).slice(0, 10).map((s, i) => {
      const angle = (i / Math.max(sites.length, 1)) * Math.PI * 2 - Math.PI / 2;
      const r = 95;
      return {
        id: s.site_id || s.id || `s${i}`,
        label: (s.domain || s.url || s.provider || `Site ${i + 1}`).replace(/^https?:\/\//, "").slice(0, 18),
        status: s.status || "active",
        provider: s.provider || "—",
        x: 200 + Math.cos(angle) * r,
        y: 120 + Math.sin(angle) * r,
      };
    });
    const edges = nodes.map((n) => ({ from: center, to: n }));
    return { center, nodes, edges, planCount: (plans || []).length };
  }, [sites, moneySite, plans]);

  return (
    <div className="hive-viz hive-viz-network hive-os-enter">
      <div className="hive-viz-head">
        <span className="hive-viz-kicker">Authority Network Graph</span>
        <h3 className="hive-viz-title">{graph.nodes.length} site · {graph.planCount} plan</h3>
      </div>
      <svg className="hive-viz-network-svg" viewBox="0 0 400 240" role="img" aria-label="Authority network">
        {graph.edges.map((e) => (
          <line
            key={e.to.id}
            x1={e.from.x}
            y1={e.from.y}
            x2={e.to.x}
            y2={e.to.y}
            className="hive-viz-network-edge"
          />
        ))}
        <g className="hive-viz-network-hub">
          <circle cx={graph.center.x} cy={graph.center.y} r="28" />
          <text x={graph.center.x} y={graph.center.y + 4} textAnchor="middle" className="hive-viz-network-label">
            {graph.center.label}
          </text>
        </g>
        {graph.nodes.map((n) => (
          <g key={n.id} className={`hive-viz-network-node status-${n.status}`}>
            <circle cx={n.x} cy={n.y} r="20" />
            <text x={n.x} y={n.y + 32} textAnchor="middle" className="hive-viz-network-sublabel">
              {n.label}
            </text>
          </g>
        ))}
      </svg>
      <div className="hive-viz-network-legend">
        <span>● Hub</span>
        <span>● Authority site</span>
        <span>— backlink mesh</span>
      </div>
    </div>
  );
});

/** Revenue Lead — huni görselleştirme */
export const RevenueFunnel = memo(function RevenueFunnel({ funnel = {}, leads = [] }) {
  const stages = useMemo(() => {
    const f = funnel || {};
    const base = [
      { key: "visits", label: "Visits", value: f.visits ?? 0 },
      { key: "clicks", label: "Clicks", value: f.clicks ?? 0 },
      { key: "leads", label: "Leads", value: f.leads ?? f.total_leads ?? leads.length ?? 0 },
      { key: "qualified", label: "Qualified", value: f.qualified ?? 0 },
      { key: "converted", label: "Converted", value: f.converted ?? 0 },
    ];
    const max = Math.max(...base.map((s) => s.value), 1);
    return base.map((s) => ({
      ...s,
      pct: Math.round((s.value / max) * 100),
      width: Math.max(18, Math.round((s.value / max) * 100)),
    }));
  }, [funnel, leads]);

  const conv = funnel?.conversion_rate ?? (
    stages[0].value ? Math.round((stages[4].value / Math.max(stages[2].value, 1)) * 100) : 0
  );

  return (
    <div className="hive-viz hive-viz-funnel hive-os-enter">
      <div className="hive-viz-head">
        <span className="hive-viz-kicker">Revenue Funnel</span>
        <h3 className="hive-viz-title">Conv. {conv}% · Est. {funnel?.estimated_revenue ?? 0}</h3>
      </div>
      <div className="hive-viz-funnel-stack">
        {stages.map((s) => (
          <div key={s.key} className="hive-viz-funnel-row">
            <span className="hive-viz-funnel-label">{s.label}</span>
            <div className="hive-viz-funnel-bar-wrap">
              <div className="hive-viz-funnel-bar" style={{ width: `${s.width}%` }}>
                <span>{s.value}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

/** Campaign Engine — haftalık ilerleme (Week 1–5+) */
export const CampaignWeekTimeline = memo(function CampaignWeekTimeline({
  campaigns = [],
  tasks = [],
  selected = null,
}) {
  const camp = selected || campaigns[0];
  const progress = Number(camp?.progress_pct ?? camp?.progress ?? 0);
  const weeks = useMemo(() => {
    const campTasks = camp
      ? tasks.filter((t) => !t.campaign_id || t.campaign_id === camp.campaign_id)
      : tasks;
    const total = campTasks.length || 1;
    const labels = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5+"];
    return labels.map((label, i) => {
      const slice = campTasks.filter((t) => {
        const w = Number(t.week ?? t.week_number ?? 0);
        if (w) return w === i + 1 || (i === 4 && w >= 5);
        const idx = campTasks.indexOf(t);
        const bucket = Math.floor((idx / total) * 5);
        return bucket === i;
      });
      const done = slice.filter((t) => (t.status || "").toLowerCase() === "completed").length;
      const pct = slice.length ? Math.round((done / slice.length) * 100) : Math.max(0, progress - i * 18);
      const active = progress >= i * 20 && progress < (i + 1) * 20 + 5;
      return { label, done, total: slice.length, pct: Math.min(100, pct), active };
    });
  }, [camp, tasks, progress]);

  return (
    <div className="hive-viz hive-viz-week-timeline hive-viz-roadmap hive-os-enter">
      <div className="hive-viz-head">
        <span className="hive-viz-kicker">Campaign Roadmap</span>
        <h3 className="hive-viz-title">{camp?.name || camp?.target_keyword || "Kampanya"} · {progress}%</h3>
        {camp?.status && <span className="hive-viz-meta">{camp.status} · score {camp.campaign_score ?? camp.score ?? progress}</span>}
      </div>
      <div className="hive-viz-roadmap-rail">
        <div className="hive-viz-roadmap-progress" style={{ width: `${progress}%` }} />
      </div>
      <div className="hive-viz-week-track">
        {weeks.map((w, i) => (
          <div key={w.label} className={`hive-viz-week-node ${w.active ? "active" : ""} ${w.pct >= 100 ? "done" : ""}`}>
            <div className="hive-viz-week-dot">{i + 1}</div>
            {i < weeks.length - 1 && <div className="hive-viz-week-line"><div style={{ width: `${w.pct}%` }} /></div>}
            <span className="hive-viz-week-label">{w.label}</span>
            <span className="hive-viz-week-stat">{w.done}/{w.total || "—"}</span>
            <div className="hive-viz-week-mini-bar"><div style={{ width: `${w.pct}%` }} /></div>
          </div>
        ))}
      </div>
    </div>
  );
});

/** Authority Mesh — interaktif SVG graph V2 (Money → Authority → Publishers → Traffic) */
export const AuthorityMeshInteractiveGraph = memo(function AuthorityMeshInteractiveGraph({
  sites = [],
  moneySite = "Money Site",
  publisherCount = 0,
  sources = [],
  traffic = 0,
  onNavigate,
}) {
  const [hover, setHover] = React.useState(null);
  const [selected, setSelected] = React.useState(null);
  const [layer, setLayer] = React.useState("all");
  const LAYERS = [
    { id: "all", label: "All" },
    { id: "money", label: "Money" },
    { id: "authority", label: "Authority" },
    { id: "publishers", label: "Publishers" },
    { id: "traffic", label: "Traffic" },
  ];

  const graph = useMemo(() => {
    const hubLabel = (moneySite || "Money Site").replace(/^https?:\/\//, "").slice(0, 22);
    const W = 520;
    const authorityNodes = (sites || []).slice(0, 8).map((s, i, arr) => {
      const n = arr.length || 1;
      const x = 80 + (i / Math.max(n - 1, 1)) * (W - 160);
      return {
        id: s.site_id || s.id || `a${i}`,
        label: (s.domain || s.url || s.provider || `Site ${i + 1}`).replace(/^https?:\/\//, "").slice(0, 14),
        status: s.status || "active",
        authorityScore: s.authority_score ?? s.score ?? s.mesh_score ?? 0,
        publishCount: s.publish_count ?? s.published_count ?? (s.status === "published" ? 1 : 0),
        linkedDomains: s.linked_domains ?? s.backlinks ?? s.link_count ?? 0,
        provider: s.provider || "—",
        url: s.url || s.domain || "",
        x,
        y: 118,
      };
    });
    const pubNodes = (sources || []).slice(0, 7).map((p, i, arr) => {
      const n = arr.length || 1;
      const x = 90 + (i / Math.max(n - 1, 1)) * (W - 180);
      return {
        id: p.id || `p${i}`,
        label: (p.label || p.source || p.channel || `Pub ${i + 1}`).slice(0, 14),
        x,
        y: 198,
      };
    });
    if (!pubNodes.length && publisherCount > 0) {
      pubNodes.push({ id: "pub-hub", label: `${publisherCount} channels`, x: W / 2, y: 198 });
    }
    const trafficVal = traffic || publisherCount * 120 || sites.length * 80 || 0;
    const center = { id: "money", label: hubLabel, x: W / 2, y: 42 };
    const trafficNode = { id: "traffic", label: `${trafficVal} visits`, x: W / 2, y: 278 };
    const edges = [];
    authorityNodes.forEach((a, ai) => {
      edges.push({ from: center, to: a, tier: "auth" });
      const pub = pubNodes[ai % Math.max(pubNodes.length, 1)];
      if (pub) edges.push({ from: a, to: pub, tier: "pub" });
    });
    pubNodes.forEach((p) => edges.push({ from: p, to: trafficNode, tier: "traffic" }));
    if (!authorityNodes.length) {
      edges.push({ from: center, to: trafficNode, tier: "direct" });
    }
    return { W, H: 310, center, authorityNodes, pubNodes, trafficNode, edges, trafficVal };
  }, [sites, moneySite, sources, publisherCount, traffic]);

  const layerVisible = (tier) => {
    if (layer === "all") return true;
    if (layer === "money") return tier === "auth" || tier === "direct";
    if (layer === "authority") return tier === "auth";
    if (layer === "publishers") return tier === "pub";
    if (layer === "traffic") return tier === "traffic" || tier === "direct";
    return true;
  };

  const hoverNode = hover === "money" ? graph.center
    : hover === "traffic" ? graph.trafficNode
      : (graph.authorityNodes.find((n) => n.id === hover) || graph.pubNodes.find((n) => n.id === hover) || null);

  const selectedNode = selected === "money" ? { type: "hub", ...graph.center, label: graph.center.label }
    : selected === "traffic" ? { type: "traffic", ...graph.trafficNode }
      : graph.authorityNodes.find((n) => n.id === selected)
        || graph.pubNodes.find((n) => n.id === selected)
        || null;

  return (
    <div className="hive-viz hive-viz-mesh-interactive hive-viz-mesh-v2 hive-mesh-with-panel hive-os-enter">
      <div className="hive-viz-head hive-viz-head-split">
        <div>
          <span className="hive-viz-kicker">Authority Mesh Graph V2</span>
          <h3 className="hive-viz-title">
            {graph.authorityNodes.length} authority · {graph.pubNodes.length || publisherCount} publisher · {graph.trafficVal} traffic
          </h3>
        </div>
        <div className="hive-mesh-layer-tabs">
          {LAYERS.map((l) => (
            <button
              key={l.id}
              type="button"
              className={`hive-mesh-layer-tab ${layer === l.id ? "active" : ""}`}
              onClick={() => setLayer(l.id)}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>
      <div className="hive-mesh-stats-row">
        <span>Hub <strong>1</strong></span>
        <span>Authority <strong>{graph.authorityNodes.length}</strong></span>
        <span>Publishers <strong>{graph.pubNodes.length}</strong></span>
        <span>Traffic <strong>{graph.trafficVal}</strong></span>
      </div>
      <div className="hive-mesh-graph-wrap">
      <svg
        className="hive-mesh-svg hive-mesh-svg-v2"
        viewBox={`0 0 ${graph.W} ${graph.H}`}
        role="img"
        aria-label="Authority mesh network"
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id="mesh-edge-gold" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(240,193,75,0.55)" />
            <stop offset="100%" stopColor="rgba(240,193,75,0.08)" />
          </linearGradient>
          <filter id="mesh-glow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {graph.edges.filter((e) => layerVisible(e.tier)).map((e, i) => (
          <line
            key={`e-${i}`}
            x1={e.from.x}
            y1={e.from.y}
            x2={e.to.x}
            y2={e.to.y}
            className={`hive-mesh-edge tier-${e.tier} ${hover && (hover === e.from.id || hover === e.to.id) ? "lit" : ""}`}
          />
        ))}
        <g className="hive-mesh-tier-labels">
          <text x="12" y="46" className="hive-mesh-tier-txt">Money Site</text>
          <text x="12" y="122" className="hive-mesh-tier-txt">Authority</text>
          <text x="12" y="202" className="hive-mesh-tier-txt">Publishers</text>
          <text x="12" y="282" className="hive-mesh-tier-txt">Traffic</text>
        </g>
        {(layer === "all" || layer === "money") && (
          <g
            className={`hive-mesh-node hub pulse ${hover === "money" ? "hover" : ""} ${selected === "money" ? "selected" : ""}`}
            onMouseEnter={() => setHover("money")}
            onClick={() => setSelected("money")}
            style={{ cursor: "pointer" }}
          >
            <circle cx={graph.center.x} cy={graph.center.y} r="26" filter="url(#mesh-glow)" />
            <text x={graph.center.x} y={graph.center.y + 4} textAnchor="middle">{graph.center.label}</text>
          </g>
        )}
        {(layer === "all" || layer === "authority") && graph.authorityNodes.map((n) => (
          <g
            key={n.id}
            className={`hive-mesh-node authority status-${n.status} ${hover === n.id ? "hover" : ""} ${selected === n.id ? "selected" : ""}`}
            onMouseEnter={() => setHover(n.id)}
            onClick={() => setSelected(n.id)}
            style={{ cursor: "pointer" }}
          >
            <circle cx={n.x} cy={n.y} r="18" />
            <text x={n.x} y={n.y + 30} textAnchor="middle">{n.label}</text>
          </g>
        ))}
        {(layer === "all" || layer === "publishers") && graph.pubNodes.map((n) => (
          <g
            key={n.id}
            className={`hive-mesh-node publisher ${hover === n.id ? "hover" : ""} ${selected === n.id ? "selected" : ""}`}
            onMouseEnter={() => setHover(n.id)}
            onClick={() => setSelected(n.id)}
            style={{ cursor: "pointer" }}
          >
            <rect x={n.x - 22} y={n.y - 12} width="44" height="24" rx="6" />
            <text x={n.x} y={n.y + 30} textAnchor="middle">{n.label}</text>
          </g>
        ))}
        {(layer === "all" || layer === "traffic") && (
          <g
            className={`hive-mesh-node traffic pulse ${hover === "traffic" ? "hover" : ""} ${selected === "traffic" ? "selected" : ""}`}
            onMouseEnter={() => setHover("traffic")}
            onClick={() => setSelected("traffic")}
            style={{ cursor: "pointer" }}
          >
            <circle cx={graph.trafficNode.x} cy={graph.trafficNode.y} r="22" />
            <text x={graph.trafficNode.x} y={graph.trafficNode.y + 4} textAnchor="middle">{graph.trafficNode.label}</text>
          </g>
        )}
      </svg>
      {hoverNode && (
        <div className="hive-mesh-tooltip hive-mesh-tooltip-v2">
          {hover === "money" && <>Hub · {graph.center.label}</>}
          {hover === "traffic" && <>Traffic · {graph.trafficVal} est. visits</>}
          {graph.authorityNodes.find((n) => n.id === hover) && (() => {
            const n = graph.authorityNodes.find((x) => x.id === hover);
            return <>Authority · score {n.authorityScore} · {n.publishCount} published · {n.linkedDomains} links · {n.status}</>;
          })()}
          {graph.pubNodes.find((n) => n.id === hover) && <>Publisher · {graph.pubNodes.find((x) => x.id === hover)?.label}</>}
        </div>
      )}
      </div>

      <aside className={`hive-mesh-detail-panel ${selectedNode ? "open" : ""}`} aria-hidden={!selectedNode}>
        <header className="hive-mesh-detail-head">
          <h4>{selectedNode?.label || "Node detail"}</h4>
          <button type="button" className="hive-mesh-detail-close" onClick={() => setSelected(null)} aria-label="Kapat">×</button>
        </header>
        {selectedNode && (
          <div className="hive-mesh-detail-body">
            {selectedNode.authorityScore != null && (
              <div className="hive-mesh-detail-row"><span>Authority score</span><strong>{selectedNode.authorityScore}</strong></div>
            )}
            {selectedNode.publishCount != null && (
              <div className="hive-mesh-detail-row"><span>Publish count</span><strong>{selectedNode.publishCount}</strong></div>
            )}
            {selectedNode.linkedDomains != null && (
              <div className="hive-mesh-detail-row"><span>Linked domains</span><strong>{selectedNode.linkedDomains}</strong></div>
            )}
            {selectedNode.status && (
              <div className="hive-mesh-detail-row"><span>Status</span><strong>{selectedNode.status}</strong></div>
            )}
            {selectedNode.provider && selectedNode.provider !== "—" && (
              <div className="hive-mesh-detail-row"><span>Provider</span><strong>{selectedNode.provider}</strong></div>
            )}
            {selected === "traffic" && (
              <div className="hive-mesh-detail-row"><span>Est. traffic</span><strong>{graph.trafficVal}</strong></div>
            )}
            <button
              type="button"
              className="hive-mesh-detail-action"
              onClick={() => onNavigate?.(selectedNode.type === "traffic" || selected === "traffic" ? "publisher_hub" : "authority_mesh_engine")}
            >
              Open module →
            </button>
          </div>
        )}
      </aside>
    </div>
  );
});

/** @deprecated use AuthorityMeshInteractiveGraph */
export const AuthorityMeshStackGraph = AuthorityMeshInteractiveGraph;

/** Publisher Hub — Kanban V2 */
export const PublisherKanban = memo(function PublisherKanban({
  drafts = [],
  queue = [],
  jobs = [],
  published = [],
  failed = [],
}) {
  const WIP = { draft: 20, queued: 15, publishing: 5, published: 999, failed: 10 };

  const columns = useMemo(() => {
    const publishing = (jobs || []).filter((j) => {
      const s = (j.status || "").toLowerCase();
      return s === "processing" || s === "publishing" || s === "running";
    });
    const failedItems = failed?.length
      ? failed
      : (jobs || []).filter((j) => (j.status || "").toLowerCase() === "failed");
    const makeCard = (colId) => (item, i) => ({
      id: item.id || item.job_id || item.draft_id || `item-${i}`,
      title: item.title || item.url || item.source || item.channel || "Item",
      provider: item.provider || item.channel || item.source || "—",
      target: item.target_url || item.url || item.title || "—",
      created: item.created_at || item.created || item.queued_at || "—",
      status: item.status || colId,
      meta: item.channel || item.provider || item.status || "",
      priority: (item.priority || item.quality || "").toLowerCase(),
    });
    return [
      { id: "draft", label: "Draft", items: (drafts || []).map(makeCard("draft")), wip: WIP.draft },
      { id: "queued", label: "Queued", items: (queue || []).map(makeCard("queued")), wip: WIP.queued },
      { id: "publishing", label: "Publishing", items: publishing.map(makeCard("publishing")), wip: WIP.publishing },
      { id: "published", label: "Published", items: (published || []).slice(0, 12).map(makeCard("published")), wip: WIP.published },
      { id: "failed", label: "Failed", items: failedItems.slice(0, 8).map(makeCard("failed")), wip: WIP.failed },
    ];
  }, [drafts, queue, jobs, published, failed]);

  const totalCards = columns.reduce((n, c) => n + c.items.length, 0);

  return (
    <div className="hive-viz hive-viz-kanban hive-viz-kanban-v2 hive-os-enter">
      <div className="hive-viz-head hive-viz-head-split">
        <div>
          <span className="hive-viz-kicker">Publisher Kanban V2</span>
          <h3 className="hive-viz-title">Draft → Published · {totalCards} items</h3>
        </div>
        <div className="hive-kanban-throughput">
          <span>Published <strong>{columns.find((c) => c.id === "published")?.items.length ?? 0}</strong></span>
          <span>Failed <strong>{columns.find((c) => c.id === "failed")?.items.length ?? 0}</strong></span>
        </div>
      </div>
      <div className="hive-viz-kanban-board hive-viz-kanban-board-v2">
        {columns.map((col) => {
          const overWip = col.items.length > col.wip;
          return (
            <div key={col.id} className={`hive-viz-kanban-col col-${col.id} ${overWip ? "over-wip" : ""}`}>
              <header>
                <span>{col.label}</span>
                <span className="hive-viz-kanban-count">{col.items.length}{col.wip < 999 ? `/${col.wip}` : ""}</span>
              </header>
              <ul>
                {col.items.length === 0 ? (
                  <li className="hive-viz-kanban-empty">
                    <span className="hive-kanban-empty-title">Boş kolon</span>
                    <span className="hive-kanban-empty-why">
                      {col.id === "draft" && "CRE veya içerik planından taslak oluşturun."}
                      {col.id === "queued" && "Publish Queue'ya içerik ekleyin veya tara çalıştırın."}
                      {col.id === "publishing" && "Aktif yayın job'u yok — kuyruğu işleyin."}
                      {col.id === "published" && "Henüz yayın yok — Publisher Hub'dan ilk gönderiyi yapın."}
                      {col.id === "failed" && "Hata yok — pipeline temiz."}
                    </span>
                  </li>
                ) : (
                  col.items.map((item, idx) => (
                    <li
                      key={item.id}
                      className={`hive-viz-kanban-card priority-${item.priority || "normal"}`}
                      style={{ animationDelay: `${idx * 35}ms` }}
                    >
                      <strong>{item.title}</strong>
                      <div className="hive-kanban-card-meta">
                        <span title="Provider">{item.provider}</span>
                        <span title="Target">{String(item.target).slice(0, 28)}</span>
                        <span title="Created">{item.created !== "—" ? String(item.created).slice(0, 16) : "—"}</span>
                        <span className={`hive-kanban-status status-${item.status}`}>{item.status}</span>
                      </div>
                    </li>
                  ))
                )}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
});

/** Revenue — Traffic → Revenue huni V2 */
export const RevenueFunnelOps = memo(function RevenueFunnelOps({ dash = {}, funnel = {} }) {
  const f = { ...dash, ...funnel };
  const stages = useMemo(() => {
    const base = [
      { key: "traffic", label: "Traffic", value: f.visits ?? f.traffic ?? f.total_visits ?? 0 },
      { key: "lead", label: "Lead", value: f.leads ?? f.total_leads ?? f.today_leads ?? 0 },
      { key: "qualified", label: "Qualified", value: f.qualified ?? 0 },
      { key: "won", label: "Won", value: f.converted ?? f.won ?? 0 },
      { key: "revenue", label: "Revenue", value: f.estimated_revenue ?? f.revenue_opportunity ?? 0 },
    ];
    const max = Math.max(...base.map((s) => s.value), 1);
    return base.map((s, i) => ({
      ...s,
      width: Math.max(22, Math.round((s.value / max) * 100)),
      drop: i > 0 && base[i - 1].value
        ? Math.round((1 - s.value / base[i - 1].value) * 100)
        : 0,
    }));
  }, [f]);

  const wonNotConverted = Math.max(0, (f.qualified ?? 0) - (f.converted ?? f.won ?? 0));
  const convRate = f.conversion_rate ?? (stages[1].value ? Math.round((stages[3].value / stages[1].value) * 100) : 0);
  const isEmpty = stages.every((s) => !s.value);

  const stageConv = stages.map((s, i) => {
    if (i === 0) return null;
    const prev = stages[i - 1].value;
    return prev ? Math.round((s.value / prev) * 100) : 0;
  });

  if (isEmpty) {
    return (
      <div className="hive-viz hive-viz-funnel-ops hive-viz-funnel-v2 hive-os-enter">
        <div className="hive-viz-head">
          <span className="hive-viz-kicker">Revenue Funnel V2</span>
          <h3 className="hive-viz-title">Traffic → Revenue</h3>
        </div>
        <div className="hive-funnel-empty-state">
          <p className="hive-funnel-empty-title">Henüz lead veya trafik verisi yok</p>
          <p className="hive-funnel-empty-why">Revenue Engine, Analytics veya Publisher trafiği bağlandığında huni dolacak.</p>
          <p className="hive-funnel-empty-action">→ Revenue / Lead Engine modülünden lead toplamayı başlatın</p>
        </div>
      </div>
    );
  }

  return (
    <div className="hive-viz hive-viz-funnel-ops hive-viz-funnel-v2 hive-os-enter">
      <div className="hive-viz-head hive-viz-head-split">
        <div>
          <span className="hive-viz-kicker">Revenue Funnel V2</span>
          <h3 className="hive-viz-title">Traffic → Revenue · Conv {convRate}%</h3>
        </div>
        {wonNotConverted > 0 && (
          <div className="hive-funnel-leak-badge" title="Qualified but not won">
            ⚠ {wonNotConverted} won-not-converted
          </div>
        )}
      </div>
      <div className="hive-viz-funnel-ops-stack hive-viz-funnel-v2-stack">
        {stages.map((s, i) => (
          <React.Fragment key={s.key}>
            {i > 0 && (
              <div className="hive-viz-funnel-ops-arrow hive-funnel-v2-arrow">
                ↓
                {stageConv[i] != null && (
                  <span className="hive-funnel-conv-pct">{stageConv[i]}% conv</span>
                )}
                {s.drop > 0 && <span className="hive-funnel-drop">−{s.drop}% drop</span>}
              </div>
            )}
            <div className="hive-viz-funnel-ops-row hive-funnel-v2-row">
              <span className="hive-viz-funnel-ops-label">{s.label}</span>
              <div className="hive-viz-funnel-ops-bar hive-funnel-v2-bar" style={{ width: `${s.width}%` }}>
                <span className="hive-funnel-v2-value">{s.value}</span>
              </div>
            </div>
          </React.Fragment>
        ))}
      </div>
      <div className="hive-funnel-v2-summary">
        <span>Pipeline <strong>{stages[1].value}</strong></span>
        <span>Qualified <strong>{stages[2].value}</strong></span>
        <span>Won <strong>{stages[3].value}</strong></span>
        <span>Revenue <strong>{stages[4].value}</strong></span>
      </div>
    </div>
  );
});

/** Executive AI — CEO dashboard */
export const ExecutiveCEODashboard = memo(function ExecutiveCEODashboard({ dash = {}, priorities = [] }) {
  const topOpp = priorities.find((p) => (p.category || "").toLowerCase().includes("growth"))
    || priorities[0];
  const topRisk = priorities.find((p) => (p.category || "").toLowerCase().includes("risk"))
    || priorities[1];
  const topCamp = dash?.top_campaign || dash?.campaign_highlight;

  const periods = [
    { id: "today", label: "Today", score: dash?.executive_score ?? "—", sub: `${dash?.missions_daily ?? 0} missions` },
    { id: "week", label: "This Week", score: dash?.performance_score ?? dash?.weekly_score ?? "—", sub: dash?.health_category || "—" },
    { id: "month", label: "This Month", score: dash?.revenue_forecast?.value ?? dash?.forecast_score ?? "—", sub: dash?.revenue_forecast?.label || "forecast" },
  ];

  return (
    <div className="hive-viz hive-viz-ceo hive-os-enter">
      <div className="hive-viz-head">
        <span className="hive-viz-kicker">CEO Dashboard</span>
        <h3 className="hive-viz-title">{dash?.latest_ceo_headline || "Executive overview"}</h3>
      </div>
      <div className="hive-viz-ceo-periods">
        {periods.map((p) => (
          <div key={p.id} className="hive-viz-ceo-period">
            <span className="hive-viz-ceo-period-label">{p.label}</span>
            <span className="hive-viz-ceo-period-score">{p.score}</span>
            <span className="hive-viz-ceo-period-sub">{p.sub}</span>
          </div>
        ))}
      </div>
      <div className="hive-viz-ceo-highlights">
        <div className="hive-viz-ceo-card opp">
          <span>Top Opportunity</span>
          <strong>{topOpp?.title || dash?.top_opportunity || "—"}</strong>
        </div>
        <div className="hive-viz-ceo-card risk">
          <span>Top Risk</span>
          <strong>{topRisk?.title || dash?.top_risk || dash?.performance_risk || "—"}</strong>
        </div>
        <div className="hive-viz-ceo-card camp">
          <span>Top Campaign</span>
          <strong>{topCamp?.name || topCamp || dash?.top_priority || "—"}</strong>
        </div>
      </div>
    </div>
  );
});

/** HIVE Brain — filtreli timeline V2 */
export const BrainEventTimeline = memo(function BrainEventTimeline({
  events = [],
  timeline = [],
  title = "Brain Timeline",
  onNavigate,
}) {
  const [filter, setFilter] = React.useState("all");
  const [severity, setSeverity] = React.useState("all");
  const [search, setSearch] = React.useState("");

  React.useEffect(() => {
    try {
      const q = sessionStorage.getItem("hive_brain_search");
      if (q) {
        setSearch(q);
        sessionStorage.removeItem("hive_brain_search");
        setFilter("all");
      }
    } catch { /* ignore */ }
  }, []);
  const FILTERS = [
    { id: "all", label: "All" },
    { id: "campaign", label: "Campaign" },
    { id: "authority", label: "Authority" },
    { id: "revenue", label: "Revenue" },
    { id: "citation", label: "Citation" },
    { id: "publisher", label: "Publisher" },
  ];
  const SEVERITIES = [
    { id: "all", label: "All" },
    { id: "critical", label: "Critical" },
    { id: "warning", label: "Warning" },
    { id: "info", label: "Info" },
    { id: "success", label: "Success" },
  ];

  const rows = useMemo(() => {
    const flatTimeline = (timeline || []).flatMap((day) =>
      (day.highlights || day.events || []).map((h, i) => ({
        event_id: `${day.date}-${i}`,
        timestamp: day.date,
        module: "timeline",
        summary: typeof h === "string" ? h : h.message || h.summary,
      }))
    );
    const merged = [...(events || []), ...flatTimeline];
    const seen = new Set();
    const unique = merged.filter((e) => {
      const id = e.id || e.event_id || `${e.timestamp}-${e.message}`;
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    });
    const matchFilter = (e) => {
      if (filter === "all") return true;
      const blob = `${e.module || ""} ${e.event_type || ""} ${e.category || ""} ${e.message || ""} ${e.summary || ""}`.toLowerCase();
      if (filter === "publisher") return blob.includes("publish") || blob.includes("publisher");
      return blob.includes(filter);
    };
    const q = search.trim().toLowerCase();
    return unique.filter(matchFilter).filter((e) => {
      if (!q) return true;
      const blob = `${e.module || ""} ${e.message || ""} ${e.summary || ""}`.toLowerCase();
      return blob.includes(q);
    }).slice(0, 60).map((e, i) => {
      const blob = `${e.severity || ""} ${e.level || ""} ${e.event_type || ""} ${e.status || ""}`.toLowerCase();
      const tone = blob.includes("critical") || blob.includes("error") || blob.includes("fail") ? "critical"
        : blob.includes("warn") || blob.includes("risk") ? "warning"
          : blob.includes("success") || blob.includes("complete") || blob.includes("won") ? "success" : "info";
      const ts = e.timestamp ? new Date(e.timestamp) : null;
      const dateKey = ts && !Number.isNaN(ts.getTime()) ? ts.toLocaleDateString("tr-TR") : "Unknown";
      return {
        id: e.id || e.event_id || `ev-${i}`,
        dateKey,
        time: ts ? ts.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }) : e.time || "—",
        module: e.module || e.source || "system",
        message: e.message || e.summary || e.title || "—",
        tone,
        navId: e.module?.includes("campaign") ? "campaign_engine"
          : e.module?.includes("publish") ? "publisher_hub"
            : e.module?.includes("revenue") ? "revenue_lead_engine" : null,
      };
    }).filter((r) => severity === "all" || r.tone === severity);
  }, [events, timeline, filter, search, severity]);

  const grouped = useMemo(() => {
    const map = {};
    rows.forEach((r) => {
      if (!map[r.dateKey]) map[r.dateKey] = [];
      map[r.dateKey].push(r);
    });
    return Object.entries(map);
  }, [rows]);

  return (
    <div className="hive-viz hive-viz-brain-tl hive-viz-brain-v2 hive-os-enter">
      <div className="hive-viz-head">
        <span className="hive-viz-kicker">{title} V2</span>
        <div className="hive-viz-brain-toolbar">
          <input
            type="search"
            className="hive-viz-brain-search"
            placeholder="Search events…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="hive-viz-brain-filters">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                className={`hive-viz-brain-filter ${filter === f.id ? "active" : ""}`}
                onClick={() => setFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="hive-viz-brain-severity">
            {SEVERITIES.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`hive-viz-brain-sev sev-${s.id} ${severity === s.id ? "active" : ""}`}
                onClick={() => setSeverity(s.id)}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="hive-viz-brain-stream hive-viz-brain-stream-v2">
        {grouped.length === 0 ? (
          <div className="hive-brain-empty-state">
            <p className="hive-brain-empty-title">Eşleşen olay yok</p>
            <p className="hive-brain-empty-why">
              {search || filter !== "all" || severity !== "all"
                ? "Filtreleri gevşetin veya arama terimini değiştirin."
                : "Modül aktivitesi veya backfill sonrası Brain timeline dolacak."}
            </p>
            <p className="hive-brain-empty-action">→ Campaign, Publisher veya Authority modüllerinden aksiyon alın</p>
          </div>
        ) : (
          grouped.map(([date, items]) => (
            <div key={date} className="hive-viz-brain-day-group">
              <div className="hive-viz-brain-day-label">{date}</div>
              {items.map((r, idx) => (
                <div
                  key={r.id}
                  className={`hive-viz-brain-event sev-${r.tone} ${r.navId ? "clickable" : ""}`}
                  style={{ animationDelay: `${idx * 30}ms` }}
                  onClick={() => r.navId && onNavigate?.(r.navId)}
                  role={r.navId ? "button" : undefined}
                  tabIndex={r.navId ? 0 : undefined}
                >
                  <span className="hive-viz-brain-dot" />
                  <time>{r.time}</time>
                  <span className="hive-viz-brain-mod">{r.module}</span>
                  <span className="hive-viz-brain-msg">{r.message}</span>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
});

/** Publisher Hub — yayın akışı */
export const PublisherFlow = memo(function PublisherFlow({
  sources = 0,
  drafts = 0,
  queue = 0,
  published = 0,
  failed = 0,
  jobs = 0,
}) {
  const steps = [
    { id: "sources", label: "Sources", count: sources, icon: "📥" },
    { id: "drafts", label: "Drafts", count: drafts, icon: "📝" },
    { id: "queue", label: "Queue", count: queue, icon: "⏳" },
    { id: "published", label: "Published", count: published, icon: "✅" },
  ];

  return (
    <div className="hive-viz hive-viz-flow hive-os-enter">
      <div className="hive-viz-head">
        <span className="hive-viz-kicker">Publisher Flow</span>
        <h3 className="hive-viz-title">
          {published} yayında · {failed > 0 ? `${failed} hata` : "pipeline aktif"}
          {jobs > 0 ? ` · ${jobs} job` : ""}
        </h3>
      </div>
      <div className="hive-viz-flow-pipeline">
        {steps.map((step, i) => (
          <React.Fragment key={step.id}>
            <div className={`hive-viz-flow-step ${step.count > 0 ? "has-items" : ""}`}>
              <span className="hive-viz-flow-icon">{step.icon}</span>
              <span className="hive-viz-flow-count">{step.count}</span>
              <span className="hive-viz-flow-label">{step.label}</span>
            </div>
            {i < steps.length - 1 && <div className="hive-viz-flow-arrow">→</div>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
});
