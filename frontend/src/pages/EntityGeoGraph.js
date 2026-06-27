import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField } from "../hooks/useProjectSiteField";
import {
  HiveShell,
  HiveAlert,
  HiveBtn,
  HiveSkeleton,
  HiveEmptyState,
  HiveTooltip,
  HiveToast,
} from "../components/HiveModuleUI";

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

const EMPTY_TOOLTIP = "Proje ve keyword seçtikten sonra graph oluşturun. Entity & GEO Graph, sayfalar ve lokasyonlar arasındaki ilişkileri çıkarır.";

export default function EntityGeoGraph() {
  const [tab, setTab] = useState("build");
  const [health, setHealth] = useState(null);
  const [astroProjects, setAstroProjects] = useState([]);
  const [graphs, setGraphs] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [seedKeyword, setSeedKeyword] = useState("kuşadası gece hayatı");
  const [location, setLocation] = useState("Kuşadası");
  const [domain, setDomain] = useState("");
  const [mainSiteUrl, setMainSiteUrl] = useProjectSiteField();
  const [analyzeUrl, setAnalyzeUrl] = useState("");
  const [graph, setGraph] = useState(null);
  const [geoResult, setGeoResult] = useState(null);
  const [clusters, setClusters] = useState(null);
  const [linkPlan, setLinkPlan] = useState(null);
  const [missing, setMissing] = useState(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

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
      setError("");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setInitialLoading(false);
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
    try {
      const res = await API.post("/api/entity-geo-graph/build-project-graph", {
        project_id: projectId, domain, seed_keyword: seedKeyword, location, main_site_url: mainSiteUrl,
      });
      setGraph(res.data);
      setToast(`Graph oluşturuldu: ${res.data.graph_id}`);
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
      const res = await API.post("/api/entity-geo-graph/geo-expand", { location, seed_keyword: seedKeyword, radius_km: 30 });
      setGeoResult(res.data);
      setToast("GEO genişletme tamamlandı");
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
      setToast("Topic cluster analizi tamamlandı");
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
      const res = await API.post("/api/entity-geo-graph/internal-link-plan", { project_id: projectId, max_links_per_page: 5 });
      setLinkPlan(res.data);
      setToast("İç link planı oluşturuldu");
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
      const res = await API.post("/api/entity-geo-graph/missing-entities", { project_id: projectId || undefined, location, seed_keyword: seedKeyword });
      setMissing(res.data);
      setToast("Eksik entity analizi tamamlandı");
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
      const res = await API.post("/api/entity-geo-graph/analyze-url", { url: analyzeUrl.trim(), seed_keyword: seedKeyword, location });
      setToast(`URL analizi: ${res.data.title || analyzeUrl}`);
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
      setToast(`Export: ${res.data.path}`);
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
      setTab("summary");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const sm = graph?.summary || {};

  if (initialLoading) {
    return (
      <HiveShell title="🌍 Entity & GEO Graph" subtitle="Sayfa, lokasyon, entity ve keyword ilişki grafiği — pillar/cluster, GEO fırsatları, iç link planı">
        <HiveSkeleton lines={6} />
      </HiveShell>
    );
  }

  return (
    <HiveShell
      title="🌍 Entity & GEO Graph"
      subtitle="Sayfa, lokasyon, entity ve keyword ilişki grafiği — pillar/cluster, GEO fırsatları, iç link planı"
    >
      <HiveAlert variant="info" style={{ marginBottom: "0.75rem" }}>
        <HiveTooltip content={EMPTY_TOOLTIP}>Nasıl çalışır?</HiveTooltip>
      </HiveAlert>

      {error && <HiveAlert variant="error">{error}</HiveAlert>}
      {toast && <HiveToast message={toast} onClose={() => setToast("")} />}

      {health && (
        <p style={{ fontSize: "0.8rem", marginBottom: "1rem", opacity: 0.6 }}>
          Nominatim: {health.nominatim_reachable ? "✓ erişilebilir" : "✗ erişilemiyor"}
          {health.nominatim_error && ` — ${health.nominatim_error}`}
          {" · "}Graph sayısı: {health.graphs_count}
        </p>
      )}

      <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        {TABS.map((t) => (
          <button key={t.id} type="button" onClick={() => setTab(t.id)}
            className={tab === t.id ? "btn-primary" : ""} style={{ fontSize: "0.85rem" }}>
            {t.label}
          </button>
        ))}
      </div>

      {astroProjects.length === 0 ? (
        <HiveEmptyState title="Astro proje bulunamadı" message="Önce bir Astro projesi oluşturun veya seçin." />
      ) : (
        <>
          <div style={{ display: "grid", gap: "0.5rem", maxWidth: 640, marginBottom: "1rem" }}>
            <label>
              <span style={{ fontSize: "0.85rem", opacity: 0.6 }}>
                <HiveTooltip content="Graph'ın bağlanacağı Astro projesi">Astro Proje</HiveTooltip>
              </span>
              <select value={projectId} onChange={(e) => setProjectId(e.target.value)}
                style={{ width: "100%", padding: "0.5rem" }}>
                <option value="">— Seçin —</option>
                {astroProjects.map((p) => (
                  <option key={p.id} value={p.id}>{p.site_name || p.slug} ({p.id})</option>
                ))}
              </select>
            </label>
            <label>
              <span style={{ fontSize: "0.85rem", opacity: 0.6 }}>
                <HiveTooltip content="Graph'ın merkez keyword'ü. Bu keyword etrafında entity'ler ve ilişkiler oluşturulur.">Seed Keyword</HiveTooltip>
              </span>
              <input value={seedKeyword} onChange={(e) => setSeedKeyword(e.target.value)}
                style={{ width: "100%", padding: "0.5rem" }} placeholder="ör: kuşadası gece hayatı" />
            </label>
            <label>
              <span style={{ fontSize: "0.85rem", opacity: 0.6 }}>
                <HiveTooltip content="GEO analizi için hedef lokasyon">Lokasyon</HiveTooltip>
              </span>
              <input value={location} onChange={(e) => setLocation(e.target.value)}
                style={{ width: "100%", padding: "0.5rem" }} />
            </label>
            <label>
              <span style={{ fontSize: "0.85rem", opacity: 0.6 }}>
                <HiveTooltip content="Hedef domain adı">Domain</HiveTooltip>
              </span>
              <input value={domain} onChange={(e) => setDomain(e.target.value)}
                style={{ width: "100%", padding: "0.5rem" }} placeholder="ör: demo.thiqos.com" />
            </label>
          </div>

          {tab === "build" && (
            <div>
              <HiveBtn onClick={handleBuild} disabled={loading}>
                {loading ? "Oluşturuluyor…" : "Build Graph"}
              </HiveBtn>
              <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <input value={analyzeUrl} onChange={(e) => setAnalyzeUrl(e.target.value)}
                  placeholder="https://… URL analizi" style={{ flex: 1, minWidth: 200, padding: "0.5rem" }} />
                <HiveBtn variant="secondary" onClick={handleAnalyzeUrl} disabled={loading}>Analyze URL</HiveBtn>
              </div>
            </div>
          )}

          {tab === "summary" && !graph && (
            <HiveEmptyState title="Graph bulunamadı" message="Build Graph ile yeni graph oluşturun veya kayıtlı bir graph seçin." />
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
              <HiveBtn onClick={handleGeoExpand} disabled={loading}>GEO Expand</HiveBtn>
              {geoResult && (
                <div style={{ marginTop: "1rem" }}>
                  {geoResult.warnings?.length > 0 && (
                    <HiveAlert variant="warning">{geoResult.warnings.join(" · ")}</HiveAlert>
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
                      <tr><th align="left">Başlık</th><th align="left">Slug</th><th align="left">Keyword</th></tr>
                    </thead>
                    <tbody>
                      {(geoResult.suggested_geo_pages || []).map((p, i) => (
                        <tr key={i}><td>{p.title}</td><td>{p.slug}</td><td>{p.target_keyword}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {!geoResult && !loading && (
                <HiveEmptyState title="GEO expand yapılmadı" message="GEO Expand butonuna tıklayarak lokasyon bazlı entity genişletmesi yapın." />
              )}
            </div>
          )}

          {tab === "clusters" && (
            <div>
              <HiveBtn onClick={handleClusters} disabled={loading}>Topic Clusters</HiveBtn>
              {clusters && (
                <div style={{ marginTop: "1rem" }}>
                  <p><strong>Pillar:</strong> {clusters.pillar}</p>
                  <h4>Clusters</h4>
                  <ul>{(clusters.clusters || []).map((c, i) => <li key={i}>{c}</li>)}</ul>
                </div>
              )}
              {!clusters && !loading && (
                <HiveEmptyState title="Cluster analizi yapılmadı" message="Topic Clusters butonuna tıklayarak keyword cluster analizi yapın." />
              )}
            </div>
          )}

          {tab === "links" && (
            <div>
              <HiveBtn onClick={handleLinkPlan} disabled={loading}>Internal Link Plan</HiveBtn>
              {linkPlan?.links?.length > 0 && (
                <table style={{ width: "100%", marginTop: "1rem", fontSize: "0.85rem", borderCollapse: "collapse" }}>
                  <thead>
                    <tr><th align="left">From</th><th align="left">To</th><th align="left">Anchor</th><th align="left">Reason</th></tr>
                  </thead>
                  <tbody>
                    {linkPlan.links.map((l, i) => (
                      <tr key={i}><td>{l.from_page}</td><td>{l.to_page}</td><td>{l.anchor}</td><td>{l.reason}</td></tr>
                    ))}
                  </tbody>
                </table>
              )}
              {(!linkPlan || linkPlan?.links?.length === 0) && !loading && (
                <HiveEmptyState title="İç link planı yok" message="Internal Link Plan butonuna tıklayarak otomatik iç link önerileri alın." />
              )}
            </div>
          )}

          {tab === "missing" && (
            <div>
              <HiveBtn onClick={handleMissing} disabled={loading}>Missing Entities</HiveBtn>
              {missing && (
                <div style={{ marginTop: "1rem" }}>
                  {missing.warnings?.length > 0 && (
                    <p style={{ opacity: 0.6, fontSize: "0.85rem" }}>{missing.warnings.join(" · ")}</p>
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
              {!missing && !loading && (
                <HiveEmptyState title="Eksik entity analizi yapılmadı" message="Missing Entities butonuna tıklayarak rakiplerin sahip olduğu sizin eksik entity'lerinizi keşfedin." />
              )}
            </div>
          )}

          {tab === "export" && (
            <div>
              <HiveEmptyState title="Graph'ı Dışa Aktar" message="Graph verilerini JSON veya Markdown formatında dışa aktarın." />
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                <HiveBtn onClick={() => handleExport("json")} disabled={loading}>Export JSON</HiveBtn>
                <HiveBtn variant="secondary" onClick={() => handleExport("md")} disabled={loading}>Export Markdown</HiveBtn>
              </div>
            </div>
          )}
        </>
      )}

      {graphs.length > 0 && (
        <details style={{ marginTop: "1.5rem" }}>
          <summary>Kayıtlı graphlar ({graphs.length})</summary>
          <ul style={{ fontSize: "0.85rem" }}>
            {graphs.map((g) => (
              <li key={g.graph_id}>
                <button type="button" className="btn-link" onClick={() => loadGraph(g.graph_id)}>
                  {g.graph_id}
                </button>
                {" — "}{g.node_count} node · {g.domain}
              </li>
            ))}
          </ul>
        </details>
      )}
    </HiveShell>
  );
}
