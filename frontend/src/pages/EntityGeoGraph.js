import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

const TABS = [
  { id: "build", label: "Build Graph" },
  { id: "summary", label: "Graph Summary" },
  { id: "geo", label: "GEO Expand" },
  { id: "clusters", label: "Topic Clusters" },
  { id: "links", label: "Internal Link Plan" },
  { id: "missing", label: "Missing Entities" },
  { id: "export", label: "Export" },
];

function ScoreCard({ label, value }) {
  return (
    <div className="hive-stat" style={{ minWidth: 130 }}>
      <div className="hive-stat-label">{label}</div>
      <div className="hive-stat-value">{value ?? "—"}</div>
    </div>
  );
}

export default function EntityGeoGraph() {
  const [tab, setTab] = useState("build");
  const [health, setHealth] = useState(null);
  const [astroProjects, setAstroProjects] = useState([]);
  const [graphs, setGraphs] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [seedKeyword, setSeedKeyword] = useState("kuşadası gece hayatı");
  const [location, setLocation] = useState("Kuşadası");
  const [domain, setDomain] = useState("");
  const [mainSiteUrl, setMainSiteUrl] = useState("https://www.balkutusu.com");
  const [analyzeUrl, setAnalyzeUrl] = useState("");
  const [graph, setGraph] = useState(null);
  const [geoResult, setGeoResult] = useState(null);
  const [clusters, setClusters] = useState(null);
  const [linkPlan, setLinkPlan] = useState(null);
  const [missing, setMissing] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [h, ap, gl] = await Promise.all([
        API.get("/api/entity-geo-graph/health"),
        API.get("/api/astro-factory/projects").catch(() => ({ data: { projects: [] } })),
        API.get("/api/entity-geo-graph/graphs"),
      ]);
      setHealth(h.data);
      setAstroProjects(ap.data.projects || []);
      setGraphs(gl.data.graphs || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    const p = astroProjects.find((x) => x.id === projectId);
    if (p) {
      setSeedKeyword(p.seed_keyword || seedKeyword);
      setLocation(p.location || location);
      setDomain(p.domain || "");
      setMainSiteUrl(p.main_site_url || mainSiteUrl);
    }
  }, [projectId, astroProjects]);

  const handleBuild = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/entity-geo-graph/build-project-graph", {
        project_id: projectId,
        domain,
        seed_keyword: seedKeyword,
        location,
        main_site_url: mainSiteUrl,
      });
      setGraph(res.data);
      setMessage(`Graph oluşturuldu: ${res.data.graph_id}`);
      await refresh();
      setTab("summary");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGeoExpand = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/entity-geo-graph/geo-expand", {
        location,
        seed_keyword: seedKeyword,
        radius_km: 30,
      });
      setGeoResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClusters = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/entity-geo-graph/topic-clusters", { project_id: projectId });
      setClusters(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLinkPlan = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/entity-geo-graph/internal-link-plan", {
        project_id: projectId,
        max_links_per_page: 5,
      });
      setLinkPlan(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMissing = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/entity-geo-graph/missing-entities", {
        project_id: projectId || undefined,
        location,
        seed_keyword: seedKeyword,
      });
      setMissing(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeUrl = async () => {
    if (!analyzeUrl.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/entity-geo-graph/analyze-url", {
        url: analyzeUrl.trim(),
        seed_keyword: seedKeyword,
        location,
      });
      setMessage(`URL analizi: ${res.data.title || analyzeUrl} — ${res.data.word_count} kelime`);
      setGraph({ nodes: res.data.nodes, summary: { node_count: res.data.nodes?.length } });
      setTab("summary");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (fmt) => {
    const gid = graph?.graph_id || graphs[0]?.graph_id;
    if (!gid) { setError("Önce graph oluşturun"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/entity-geo-graph/export", { graph_id: gid, format: fmt });
      setMessage(`Export: ${res.data.path}`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadGraph = async (gid) => {
    try {
      const res = await API.get(`/api/entity-geo-graph/graph/${gid}`);
      setGraph(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const sm = graph?.summary || {};

  return (
    <div className="modul-sayfa" style={{ padding: "1.5rem" }}>
      <h2>🌍 Entity &amp; GEO Graph</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
        Sayfa, lokasyon, entity ve keyword ilişki grafiği — pillar/cluster, GEO fırsatları, iç link planı
      </p>

      {health && (
        <div style={{ fontSize: "0.8rem", marginBottom: "1rem", color: "var(--text-muted)" }}>
          Nominatim: {health.nominatim_reachable ? "✓ erişilebilir" : "✗ erişilemiyor"}
          {health.nominatim_error && ` — ${health.nominatim_error}`}
          {" · "}Graph sayısı: {health.graphs_count}
        </div>
      )}

      <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={tab === t.id ? "btn-primary" : ""}
            style={{ fontSize: "0.85rem" }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gap: "0.5rem", maxWidth: 640, marginBottom: "1rem" }}>
        <label>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Astro Proje</span>
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ width: "100%", padding: "0.5rem" }}>
            <option value="">— Seçin —</option>
            {astroProjects.map((p) => (
              <option key={p.id} value={p.id}>{p.site_name || p.slug} ({p.id})</option>
            ))}
          </select>
        </label>
        <label>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Seed Keyword</span>
          <input value={seedKeyword} onChange={(e) => setSeedKeyword(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
        </label>
        <label>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Lokasyon</span>
          <input value={location} onChange={(e) => setLocation(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
        </label>
        <label>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Domain</span>
          <input value={domain} onChange={(e) => setDomain(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
        </label>
      </div>

      {error && <div className="hata-kutu" style={{ marginBottom: "1rem" }}>{String(error)}</div>}
      {message && <div style={{ marginBottom: "1rem", color: "var(--accent)" }}>{message}</div>}

      {tab === "build" && (
        <div>
          <button onClick={handleBuild} disabled={loading} className="btn-primary" style={{ marginRight: "0.5rem" }}>
            {loading ? "Oluşturuluyor…" : "Build Graph"}
          </button>
          <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <input
              value={analyzeUrl}
              onChange={(e) => setAnalyzeUrl(e.target.value)}
              placeholder="https://… URL analizi"
              style={{ flex: 1, minWidth: 200, padding: "0.5rem" }}
            />
            <button onClick={handleAnalyzeUrl} disabled={loading}>Analyze URL</button>
          </div>
        </div>
      )}

      {tab === "summary" && graph && (
        <div>
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
            <ScoreCard label="Nodes" value={sm.node_count} />
            <ScoreCard label="Edges" value={sm.edge_count} />
            <ScoreCard label="Entity Strength" value={sm.entity_strength_score} />
            <ScoreCard label="GEO Coverage" value={sm.geo_coverage_score} />
            <ScoreCard label="Topic Authority" value={sm.topic_authority_score} />
          </div>
          {sm.pillar_pages?.length > 0 && (
            <p><strong>Pillar:</strong> {sm.pillar_pages.join(", ")}</p>
          )}
          {sm.orphan_entities?.length > 0 && (
            <details>
              <summary>Orphan entities ({sm.orphan_entities.length})</summary>
              <ul>{sm.orphan_entities.map((e, i) => <li key={i}>{e}</li>)}</ul>
            </details>
          )}
          {(graph.nodes || []).filter((n) => n.type === "entity" && n.entity_strength != null).length > 0 && (
            <div style={{ overflowX: "auto", marginTop: "1rem" }}>
              <strong>Entity Research Scores</strong>
              <table className="ch-table" style={{ width: "100%", fontSize: "0.8rem", marginTop: 8 }}>
                <thead>
                  <tr><th>Entity</th><th>Authority</th><th>Visibility</th><th>Gap</th><th>Strength</th></tr>
                </thead>
                <tbody>
                  {graph.nodes.filter((n) => n.type === "entity").slice(0, 25).map((n) => (
                    <tr key={n.id}>
                      <td>{n.label}</td>
                      <td>{n.entity_authority ?? "—"}</td>
                      <td>{n.entity_visibility ?? "—"}</td>
                      <td>{n.entity_gap ?? "—"}</td>
                      <td>{n.entity_strength ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <details style={{ marginTop: "1rem" }} open>
            <summary>Graph JSON</summary>
            <pre style={{ fontSize: "0.75rem", maxHeight: 360, overflow: "auto" }}>
              {JSON.stringify({ nodes: graph.nodes?.slice(0, 30), edges: graph.edges?.slice(0, 30) }, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {tab === "geo" && (
        <div>
          <button onClick={handleGeoExpand} disabled={loading} className="btn-primary">GEO Expand</button>
          {geoResult && (
            <div style={{ marginTop: "1rem" }}>
              {geoResult.warnings?.length > 0 && (
                <div className="hata-kutu" style={{ marginBottom: "0.75rem" }}>
                  {geoResult.warnings.join(" · ")}
                </div>
              )}
              <h4>GEO Entities ({geoResult.geo_entities?.length})</h4>
              <ul style={{ fontSize: "0.9rem" }}>
                {(geoResult.geo_entities || []).slice(0, 20).map((g, i) => (
                  <li key={i}>{g.name} <span style={{ opacity: 0.6 }}>({g.type || g.source})</span></li>
                ))}
              </ul>
              <h4>Önerilen GEO Sayfaları</h4>
              <table style={{ width: "100%", fontSize: "0.85rem", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th align="left">Başlık</th>
                    <th align="left">Slug</th>
                    <th align="left">Keyword</th>
                  </tr>
                </thead>
                <tbody>
                  {(geoResult.suggested_geo_pages || []).map((p, i) => (
                    <tr key={i}>
                      <td>{p.title}</td>
                      <td>{p.slug}</td>
                      <td>{p.target_keyword}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "clusters" && (
        <div>
          <button onClick={handleClusters} disabled={loading} className="btn-primary">Topic Clusters</button>
          {clusters && (
            <div style={{ marginTop: "1rem" }}>
              <p><strong>Pillar:</strong> {clusters.pillar}</p>
              <h4>Clusters</h4>
              <ul>{(clusters.clusters || []).map((c, i) => <li key={i}>{c}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      {tab === "links" && (
        <div>
          <button onClick={handleLinkPlan} disabled={loading} className="btn-primary">Internal Link Plan</button>
          {linkPlan?.links?.length > 0 && (
            <table style={{ width: "100%", marginTop: "1rem", fontSize: "0.85rem", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th align="left">From</th>
                  <th align="left">To</th>
                  <th align="left">Anchor</th>
                  <th align="left">Reason</th>
                </tr>
              </thead>
              <tbody>
                {linkPlan.links.map((l, i) => (
                  <tr key={i}>
                    <td>{l.from_page}</td>
                    <td>{l.to_page}</td>
                    <td>{l.anchor}</td>
                    <td>{l.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "missing" && (
        <div>
          <button onClick={handleMissing} disabled={loading} className="btn-primary">Missing Entities</button>
          {missing && (
            <div style={{ marginTop: "1rem" }}>
              {missing.warnings?.length > 0 && (
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>{missing.warnings.join(" · ")}</p>
              )}
              <h4>Eksik Entityler</h4>
              <ul>{(missing.missing_entities || []).map((m, i) => (
                <li key={i}>{m.entity} ({m.source})</li>
              ))}</ul>
              <h4>Önerilen Sayfalar</h4>
              <table style={{ width: "100%", fontSize: "0.85rem", borderCollapse: "collapse" }}>
                <thead>
                  <tr><th align="left">Başlık</th><th align="left">Slug</th><th align="left">Tip</th></tr>
                </thead>
                <tbody>
                  {(missing.recommended_pages || []).map((p, i) => (
                    <tr key={i}><td>{p.title}</td><td>{p.slug}</td><td>{p.page_type}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "export" && (
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button onClick={() => handleExport("json")} disabled={loading}>Export JSON</button>
          <button onClick={() => handleExport("md")} disabled={loading}>Export Markdown</button>
        </div>
      )}

      {graphs.length > 0 && (
        <details style={{ marginTop: "1.5rem" }}>
          <summary>Kayıtlı graphlar ({graphs.length})</summary>
          <ul style={{ fontSize: "0.85rem" }}>
            {graphs.map((g) => (
              <li key={g.graph_id}>
                <button type="button" onClick={() => { loadGraph(g.graph_id); setTab("summary"); }}>
                  {g.graph_id}
                </button>
                {" — "}{g.node_count} node · {g.domain}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
