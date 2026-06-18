import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import ProviderSelector from "../components/ProviderSelector";

const TABS = [
  { id: "projects", label: "Projects" },
  { id: "index", label: "Index Status" },
  { id: "rankings", label: "Rankings" },
  { id: "gsc", label: "Search Console" },
  { id: "ai", label: "AI Overview" },
  { id: "alerts", label: "Alerts" },
  { id: "opportunities", label: "Opportunities" },
];

function MetricCard({ label, value, sub }) {
  return (
    <div className="hive-stat" style={{ minWidth: 120 }}>
      <div className="hive-stat-label">{label}</div>
      <div className="hive-stat-value">{value ?? "—"}</div>
      {sub && <div className="hive-muted" style={{ fontSize: "0.72rem", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export default function RankIndexWatcher() {
  const [tab, setTab] = useState("projects");
  const [health, setHealth] = useState(null);
  const [projects, setProjects] = useState([]);
  const [astroProjects, setAstroProjects] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [project, setProject] = useState(null);

  const [registerDomain, setRegisterDomain] = useState("");
  const [indexUrl, setIndexUrl] = useState("");
  const [keyword, setKeyword] = useState("");
  const [domain, setDomain] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [opportunities, setOpportunities] = useState([]);

  const refresh = useCallback(async () => {
    try {
      const [h, pl, ap] = await Promise.all([
        API.get("/api/rank-watcher/health"),
        API.get("/api/rank-watcher/projects"),
        API.get("/api/astro-factory/projects").catch(() => ({ data: { projects: [] } })),
      ]);
      setHealth(h.data);
      setProjects(pl.data.projects || []);
      setAstroProjects(ap.data.projects || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  }, []);

  const loadProject = useCallback(async (pid) => {
    if (!pid) { setProject(null); return; }
    try {
      const res = await API.get(`/api/rank-watcher/project/${pid}`);
      setProject(res.data.project);
      setDomain(res.data.project?.domain?.replace(/^https?:\/\//, "") || "");
    } catch {
      setProject(null);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { loadProject(selectedId); }, [selectedId, loadProject]);

  const handleRegister = async () => {
    if (!selectedId || !registerDomain.trim()) {
      setError("Astro proje seçin ve domain girin");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/rank-watcher/register-project", {
        project_id: selectedId,
        domain: registerDomain.trim(),
      });
      setMessage(`Proje kaydedildi: ${res.data.project.domain}`);
      await refresh();
      await loadProject(selectedId);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkTrack = async () => {
    if (!selectedId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/rank-watcher/bulk-track", { project_id: selectedId });
      setMessage(`${res.data.keywords_added} keyword takibe alındı`);
      setLastResult(res.data);
      await loadProject(selectedId);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleIndexStatus = async () => {
    if (!indexUrl.trim()) { setError("URL gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/rank-watcher/index-status", {
        url: indexUrl.trim(),
        project_id: selectedId,
      });
      setLastResult(res.data);
      setMessage(`Index: ${res.data.indexed ? "evet" : "hayır"} — ${res.data.coverage}`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSitemap = async () => {
    const dom = domain || registerDomain;
    if (!dom.trim()) { setError("Domain gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/rank-watcher/sitemap-status", { domain: dom.trim() });
      setLastResult(res.data);
      setAlerts(res.data.alerts || []);
      setMessage(`Sitemap: ${res.data.url_count} URL · robots ${res.data.robots?.exists ? "✓" : "✗"}`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTrackKeyword = async () => {
    if (!keyword.trim() || !domain.trim()) {
      setError("Keyword ve domain gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/rank-watcher/track-keyword", {
        keyword: keyword.trim(),
        domain: domain.trim(),
        project_id: selectedId,
      });
      setLastResult(res.data);
      setMessage(`Pozisyon: ${res.data.position ?? "top 100 dışı"}`);
      await loadProject(selectedId);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePerformance = async () => {
    const dom = domain || registerDomain;
    if (!dom.trim()) { setError("Domain gerekli"); return; }
    if (!health?.search_console) {
      setError("Search Console yapılandırılmamış — .env OAuth bilgilerini ekleyin");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/rank-watcher/performance", {
        domain: dom.trim(),
        project_id: selectedId,
      });
      setLastResult(res.data);
      setMessage(`GSC: ${res.data.clicks} tık · ${res.data.impressions} gösterim`);
      await loadProject(selectedId);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAiOverview = async () => {
    if (!keyword.trim()) { setError("Keyword gerekli"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/rank-watcher/ai-overview", { keyword: keyword.trim() });
      setLastResult(res.data);
      setMessage(res.data.has_ai_overview ? "AI Overview var" : "AI Overview yok");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDecay = async () => {
    if (!selectedId) { setError("Proje seçin"); return; }
    setLoading(true);
    try {
      const res = await API.post("/api/rank-watcher/decay", { project_id: selectedId });
      setAlerts(res.data.alerts || []);
      setMessage(res.data.note || `${(res.data.alerts || []).length} uyarı`);
      await loadProject(selectedId);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOpportunities = async () => {
    if (!selectedId) { setError("Proje seçin"); return; }
    setLoading(true);
    try {
      const res = await API.post("/api/rank-watcher/opportunities", { project_id: selectedId });
      setOpportunities(res.data.opportunities || []);
      setMessage(`${(res.data.opportunities || []).length} fırsat bulundu`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (fmt) => {
    if (!selectedId) { setError("Proje seçin"); return; }
    try {
      const res = await API.post("/api/rank-watcher/export", { project_id: selectedId, format: fmt });
      setMessage(`Export: ${res.data.path}`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const perf = project?.performance_history?.[0];
  const indexedCount = (project?.index_status || []).filter((x) => x.indexed).length;
  const kwWithPos = (project?.keywords || []).filter((k) => k.last_position != null);
  const avgPos = kwWithPos.length
    ? (kwWithPos.reduce((s, k) => s + k.last_position, 0) / kwWithPos.length).toFixed(1)
    : null;

  return (
    <div className="storyforge-panel">
      <header className="storyforge-header">
        <h2>📈 Rank &amp; Index Watcher</h2>
        <p className="storyforge-sub">Yayınlanan sayfalar — index, sıra, GSC, AI Overview</p>
      </header>

      <div className="storyforge-stats">
        <span className={health?.search_console ? "sf-ok" : "sf-warn"}>
          GSC: {health?.search_console ? "✓" : "○ yapılandır"}
        </span>
        <span className={health?.rank_provider ? "sf-ok" : "sf-warn"}>
          Rank: {health?.rank_provider ? "✓ DataForSEO" : "○ DFS opsiyonel (API Ayarları)"}
        </span>
        <span>Projeler: {health?.project_count ?? projects.length}</span>
      </div>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <ProviderSelector category="rank" label="Sıra" compact />
        <ProviderSelector category="ai_overview" label="AI Overview" compact />
      </div>

      <div className="sf-main-tabs" style={{ marginBottom: "1rem" }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`sf-main-tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            <span className="sf-main-tab-label">{t.label}</span>
          </button>
        ))}
      </div>

      <div className="storyforge-meta-row" style={{ marginBottom: "1rem" }}>
        <div>
          <label className="storyforge-label">Proje</label>
          <select
            className="storyforge-input"
            value={selectedId}
            onChange={(e) => {
              setSelectedId(e.target.value);
              const ap = astroProjects.find((p) => p.id === e.target.value);
              if (ap?.domain) setRegisterDomain(ap.domain);
            }}
          >
            <option value="">— seç —</option>
            {astroProjects.map((p) => (
              <option key={p.id} value={p.id}>{p.site_name || p.slug} ({p.id})</option>
            ))}
            {projects.filter((p) => !astroProjects.some((a) => a.id === p.project_id)).map((p) => (
              <option key={p.project_id} value={p.project_id}>{p.domain}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="storyforge-label">Domain</label>
          <input
            className="storyforge-input"
            value={registerDomain}
            onChange={(e) => setRegisterDomain(e.target.value)}
            placeholder="https://kusadasigecehayati.com"
          />
        </div>
      </div>

      <div className="storyforge-stats" style={{ flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
        <MetricCard label="Indexed URLs" value={indexedCount || "—"} />
        <MetricCard label="Avg Position" value={avgPos || perf?.avg_position || "—"} />
        <MetricCard label="CTR" value={perf?.ctr != null ? `${(perf.ctr * 100).toFixed(2)}%` : "—"} />
        <MetricCard label="Impressions" value={perf?.impressions ?? "—"} />
        <MetricCard label="Clicks" value={perf?.clicks ?? "—"} />
        <MetricCard label="AI Overview" value={lastResult?.has_ai_overview != null ? (lastResult.has_ai_overview ? "Var" : "Yok") : "—"} />
      </div>

      {tab === "projects" && (
        <section>
          <button type="button" className="btn btn-primary" onClick={handleRegister} disabled={loading}>
            Projeyi İzlemeye Al
          </button>
          <button type="button" className="btn btn-secondary" style={{ marginLeft: 8 }} onClick={handleBulkTrack} disabled={loading}>
            Astro JSON → Bulk Track
          </button>
          <button type="button" className="btn btn-outline btn-small" style={{ marginLeft: 8 }} onClick={() => handleExport("json")}>
            Export JSON
          </button>
          <button type="button" className="btn btn-outline btn-small" style={{ marginLeft: 4 }} onClick={() => handleExport("md")}>
            Export MD
          </button>
          {project && (
            <ul className="storyforge-photo-list" style={{ marginTop: "1rem" }}>
              <li>Keywords: {project.keywords?.length || 0}</li>
              <li>SEO Gate flags: {project.seo_gate_flags?.length || 0}</li>
              <li>Performance snapshots: {project.performance_history?.length || 0}</li>
            </ul>
          )}
        </section>
      )}

      {tab === "index" && (
        <section>
          <input className="storyforge-input" placeholder="https://..." value={indexUrl} onChange={(e) => setIndexUrl(e.target.value)} style={{ width: "100%", marginBottom: 8 }} />
          <button type="button" className="btn btn-primary" onClick={handleIndexStatus} disabled={loading}>Index Kontrol</button>
          <button type="button" className="btn btn-secondary" style={{ marginLeft: 8 }} onClick={handleSitemap} disabled={loading}>Sitemap + robots</button>
        </section>
      )}

      {tab === "rankings" && (
        <section>
          <div className="storyforge-meta-row">
            <input className="storyforge-input" placeholder="keyword" value={keyword} onChange={(e) => setKeyword(e.target.value)} />
            <input className="storyforge-input" placeholder="domain" value={domain} onChange={(e) => setDomain(e.target.value)} />
          </div>
          <button type="button" className="btn btn-primary" onClick={handleTrackKeyword} disabled={loading || !health?.rank_provider}>
            Keyword Track
          </button>
          {!health?.rank_provider && <p className="sf-dim">DataForSEO opsiyonel — API Ayarlarından ekleyin veya &quot;Ücretsiz&quot; mod seçin</p>}
          {(project?.keywords || []).length > 0 && (
            <div style={{ overflowX: "auto", marginTop: "1rem" }}>
              <table className="ch-table" style={{ width: "100%", fontSize: "0.8rem" }}>
                <thead>
                  <tr>
                    <th>Keyword</th><th>Pos</th><th>Velocity</th><th>Momentum</th>
                    <th>Decay</th><th>Strength</th><th>Trend</th>
                  </tr>
                </thead>
                <tbody>
                  {project.keywords.map((k) => (
                    <tr key={k.keyword}>
                      <td>{k.keyword}</td>
                      <td>{k.last_position ?? "—"}</td>
                      <td>{k.ranking_velocity ?? "—"}</td>
                      <td>{k.ranking_momentum ?? "—"}</td>
                      <td>{k.ranking_decay_score ?? 0}</td>
                      <td>{k.keyword_strength_score ?? "—"}</td>
                      <td>{k.trend_direction ?? "flat"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {tab === "gsc" && (
        <section>
          <button type="button" className="btn btn-primary" onClick={handlePerformance} disabled={loading || !health?.search_console}>
            GSC Performance Çek
          </button>
          {!health?.search_console && (
            <p className="sf-dim">GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, GOOGLE_SEARCH_CONSOLE_SITE_URL</p>
          )}
        </section>
      )}

      {tab === "ai" && (
        <section>
          <input className="storyforge-input" placeholder="keyword" value={keyword} onChange={(e) => setKeyword(e.target.value)} style={{ width: "100%", marginBottom: 8 }} />
          <button type="button" className="btn btn-primary" onClick={handleAiOverview} disabled={loading || !health?.rank_provider}>
            AI Overview Kontrol
          </button>
        </section>
      )}

      {tab === "alerts" && (
        <section>
          <button type="button" className="btn btn-primary" onClick={handleDecay} disabled={loading}>Decay Analizi</button>
          <ul className="storyforge-photo-list" style={{ marginTop: "1rem" }}>
            {(alerts.length ? alerts : project?.alerts || []).map((a, i) => (
              <li key={i} className={a.level === "critical" ? "sf-fail" : ""}>
                [{a.level}] {a.type}: {a.message}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "opportunities" && (
        <section>
          <button type="button" className="btn btn-primary" onClick={handleOpportunities} disabled={loading}>Fırsatları Bul</button>
          <ul className="storyforge-photo-list" style={{ marginTop: "1rem" }}>
            {opportunities.map((o, i) => (
              <li key={i}>
                <strong>{o.keyword}</strong>
                {o.position != null && ` · #${o.position}`}
                {" — "}{(o.suggestions || []).join(", ")}
              </li>
            ))}
          </ul>
        </section>
      )}

      {lastResult && (
        <pre className="ch-preview-snippet" style={{ marginTop: "1rem", maxHeight: 240, overflow: "auto", fontSize: 11 }}>
          {JSON.stringify(lastResult, null, 2)}
        </pre>
      )}

      {error && <p className="storyforge-error">{error}</p>}
      {message && <p className="storyforge-ok">{message}</p>}
    </div>
  );
}
