import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";


const TABS = [
  { id: "networks", label: "Networks" },
  { id: "domains", label: "Domains" },
  { id: "clone", label: "Clone Site" },
  { id: "rewrite", label: "Rewrite" },
  { id: "retheme", label: "Retheme" },
  { id: "blueprint", label: "Blueprint" },
  { id: "variants", label: "Variants" },
  { id: "deploy", label: "Build & Deploy" },
  { id: "reports", label: "Reports" },
];

const REWRITE_MODES = ["light", "balanced", "heavy", "full_rebuild"];
const RETHEME_STYLES = ["modern", "magazine", "directory", "corporate", "travel", "nightlife", "tourism", "minimal"];

export default function NetworkReplicator() {
  const [tab, setTab] = useState("networks");
  const [health, setHealth] = useState(null);
  const [networks, setNetworks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [activeNet, setActiveNet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [blueprint, setBlueprint] = useState(null);

  const [mainDomain, setMainDomain] = useProjectDomainField();
  const [mainSiteUrl] = useProjectSiteField();
  const [cloneForm, setCloneForm] = useState({ source_project_id: "", target_domain: "", target_site_name: "" });
  const [manyDomains, setManyDomains] = useState("");
  const [rewriteProject, setRewriteProject] = useState("");
  const [rewriteMode, setRewriteMode] = useState("balanced");
  const [rethemeProject, setRethemeProject] = useState("");
  const [rethemeStyle, setRethemeStyle] = useState("modern");
  const [competitorUrl, setCompetitorUrl] = useState("");
  const [variantForm, setVariantForm] = useState({ blueprint_id: "", target_domain: "", site_name: "", role: "brand_hub" });

  const refresh = useCallback(async () => {
    try {
      const [h, nl, pl] = await Promise.all([
        API.get("/api/network-replicator/health"),
        API.get("/api/network-replicator/networks"),
        API.get("/api/astro-factory/projects"),
      ]);
      setHealth(h.data);
      setNetworks(nl.data.networks || []);
      setProjects(pl.data.projects || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const loadNetwork = async (id) => {
    const res = await API.get(`/api/network-replicator/network/${id}`);
    setActiveNet(res.data.network);
  };

  const handleCreateNetwork = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/network-replicator/create-network", { main_domain: mainDomain, name: `${mainDomain} Network` });
      setActiveNet(res.data.network);
      setMessage(`Network oluşturuldu: ${res.data.network.network_id}`);
      await refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCloneMany = async () => {
    if (!cloneForm.source_project_id) return;
    setLoading(true);
    const domains = manyDomains.split("\n").map((d) => d.trim()).filter(Boolean);
    try {
      const res = await API.post("/api/network-replicator/clone-to-many", {
        source_project_id: cloneForm.source_project_id,
        domains,
        network_id: activeNet?.network_id || "",
        rewrite_mode: rewriteMode,
        retheme_style: rethemeStyle,
        auto_build: true,
        auto_deploy: false,
      });
      setMessage(`${res.data.cloned} domain klonlandı · job ${res.data.job_id}`);
      if (activeNet) await loadNetwork(activeNet.network_id);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRewrite = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/network-replicator/rewrite-content", { project_id: rewriteProject, mode: rewriteMode });
      setMessage(`Rewrite (${rewriteMode}): ${res.data.rewritten_fields} alan`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRetheme = async () => {
    setLoading(true);
    try {
      await API.post("/api/network-replicator/retheme-site", { project_id: rethemeProject, style: rethemeStyle });
      setMessage(`Retheme: ${rethemeStyle}`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBlueprint = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/network-replicator/analyze-blueprint", { url: competitorUrl });
      setBlueprint(res.data);
      setVariantForm((f) => ({ ...f, blueprint_id: res.data.blueprint_id }));
      setMessage("Blueprint çıkarıldı — içerik kopyalanmadı");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBuildDeploy = async (deploy = false) => {
    if (!activeNet) return;
    setLoading(true);
    try {
      if (!deploy) {
        await API.post("/api/network-replicator/build-network", { network_id: activeNet.network_id });
        setMessage("Network build tamamlandı");
      } else {
        const res = await API.post("/api/network-replicator/deploy-network", { network_id: activeNet.network_id });
        setMessage(`Deploy: ${res.data.deployed} site`);
      }
      await loadNetwork(activeNet.network_id);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="hive-page">
      <div className="hive-hero">
        <h2>🧬 Network Replicator & Blueprint Engine</h2>
        <p>Multi-domain clone · rewrite · retheme · blueprint · gerçek build & Cloudflare deploy</p>
        {health && (
          <p className="hive-hero-meta">
            Networks: {health.network_count} · Min deploy skor: {health.min_deploy_score}
          </p>
        )}
      </div>

      {error && <div className="hive-alert-err">{error}</div>}
      {message && <div className="hive-alert-ok">{message}</div>}

      <div className="hive-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`hive-tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "networks" && (
        <div className="hive-card">
          <h3>Networks</h3>
          <label>
            Ana domain
            <input className="hive-input" value={mainDomain} onChange={(e) => setMainDomain(e.target.value)} />
          </label>
          <button type="button" className="btn-primary" disabled={loading} onClick={handleCreateNetwork}>
            Network Oluştur
          </button>
          <ul style={{ marginTop: "1rem", fontSize: "0.82rem" }}>
            {networks.map((n) => (
              <li key={n.network_id}>
                <button
                  type="button"
                  className="hive-link-btn"
                  onClick={() => { setActiveNet(n); loadNetwork(n.network_id); }}
                >
                  {n.name} ({n.main_domain})
                </button>
                {" "}· {n.domains?.length || 0} domain
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "domains" && activeNet && (
        <div className="hive-card">
          <h3>Domains — {activeNet.main_domain}</h3>
          <div style={{ overflowX: "auto" }}>
            <table className="hive-table">
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Role</th>
                  <th>Build</th>
                  <th>Deploy</th>
                  <th>Q.Skor</th>
                </tr>
              </thead>
              <tbody>
                {(activeNet.domains || []).map((d) => (
                  <tr key={d.domain}>
                    <td>{d.domain}</td>
                    <td>{d.role}</td>
                    <td>{d.build_status || "—"}</td>
                    <td>{d.deploy_status || "—"}</td>
                    <td>{d.quality_score || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "domains" && !activeNet && (
        <div className="hive-card">
          <p className="hive-muted">Önce Networks sekmesinden bir network seçin.</p>
        </div>
      )}

      {tab === "clone" && (
        <div className="hive-card">
          <h3>Clone to Many</h3>
          <label>
            Kaynak proje
            <select
              className="hive-input"
              value={cloneForm.source_project_id}
              onChange={(e) => setCloneForm({ ...cloneForm, source_project_id: e.target.value })}
            >
              <option value="">— seç —</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.site_name}</option>)}
            </select>
          </label>
          <label>
            Hedef domainler (satır başına)
            <textarea className="hive-input" value={manyDomains} onChange={(e) => setManyDomains(e.target.value)} rows={5} />
          </label>
          <button type="button" className="btn-primary" disabled={loading || !cloneForm.source_project_id} onClick={handleCloneMany}>
            Clone to Many + Rewrite + Retheme + Build
          </button>
        </div>
      )}

      {tab === "rewrite" && (
        <div className="hive-card">
          <label>
            Project ID
            <input className="hive-input" value={rewriteProject} onChange={(e) => setRewriteProject(e.target.value)} />
          </label>
          <label>
            Mode
            <select className="hive-input" value={rewriteMode} onChange={(e) => setRewriteMode(e.target.value)}>
              {REWRITE_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </label>
          <button type="button" disabled={loading || !rewriteProject} onClick={handleRewrite}>
            Rewrite Content
          </button>
        </div>
      )}

      {tab === "retheme" && (
        <div className="hive-card">
          <label>
            Project ID
            <input className="hive-input" value={rethemeProject} onChange={(e) => setRethemeProject(e.target.value)} />
          </label>
          <label>
            Style
            <select className="hive-input" value={rethemeStyle} onChange={(e) => setRethemeStyle(e.target.value)}>
              {RETHEME_STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <button type="button" disabled={loading || !rethemeProject} onClick={handleRetheme}>
            Retheme Site
          </button>
        </div>
      )}

      {tab === "blueprint" && (
        <div className="hive-card">
          <label>
            URL (yapı analizi only)
            <input className="hive-input" value={competitorUrl} onChange={(e) => setCompetitorUrl(e.target.value)} />
          </label>
          <button type="button" className="btn-primary" disabled={loading || !competitorUrl} onClick={handleBlueprint}>
            Analyze Blueprint
          </button>
          {blueprint && (
            <pre style={{ fontSize: "0.72rem", overflow: "auto", maxHeight: 240, marginTop: "1rem" }}>
              {JSON.stringify(blueprint, null, 2)}
            </pre>
          )}
        </div>
      )}

      {tab === "variants" && (
        <div className="hive-card">
          <label>
            Blueprint ID
            <input className="hive-input" value={variantForm.blueprint_id} onChange={(e) => setVariantForm({ ...variantForm, blueprint_id: e.target.value })} />
          </label>
          <label>
            Domain
            <input className="hive-input" value={variantForm.target_domain} onChange={(e) => setVariantForm({ ...variantForm, target_domain: e.target.value })} />
          </label>
          <label>
            Site adı
            <input className="hive-input" value={variantForm.site_name} onChange={(e) => setVariantForm({ ...variantForm, site_name: e.target.value })} />
          </label>
          <button
            type="button"
            disabled={loading || !variantForm.blueprint_id}
            onClick={async () => {
              setLoading(true);
              try {
                const res = await API.post("/api/network-replicator/generate-variant", {
                  ...variantForm,
                  network_id: activeNet?.network_id || "",
                  main_site_url: mainSiteUrl || "",
                });
                setMessage(`Variant: ${res.data.project_id || "OK"}`);
              } catch (e) {
                setError(e.response?.data?.detail || e.message);
              } finally {
                setLoading(false);
              }
            }}
          >
            Generate Variant
          </button>
        </div>
      )}

      {tab === "deploy" && (
        <div className="hive-card">
          {!activeNet && <p className="hive-muted">Önce bir network seçin</p>}
          {activeNet && (
            <>
              <button type="button" disabled={loading} onClick={() => handleBuildDeploy(false)} style={{ marginRight: 8 }}>
                Build Network
              </button>
              <button type="button" className="btn-primary" disabled={loading} onClick={() => handleBuildDeploy(true)}>
                Deploy Network (Gate ≥85)
              </button>
              <p className="hive-muted" style={{ marginTop: 8 }}>
                Quality Gate fail olan domainler deploy edilmez.
              </p>
            </>
          )}
        </div>
      )}

      {tab === "reports" && activeNet && (
        <div className="hive-card">
          <button
            type="button"
            disabled={loading}
            onClick={async () => {
              const res = await API.post("/api/network-replicator/export-report", { network_id: activeNet.network_id });
              setMessage(`Rapor: ${res.data.report_path}`);
            }}
          >
            Export Network Report
          </button>
        </div>
      )}

      {tab === "reports" && !activeNet && (
        <div className="hive-card">
          <p className="hive-muted">Önce bir network seçin.</p>
        </div>
      )}
    </div>
  );
}
