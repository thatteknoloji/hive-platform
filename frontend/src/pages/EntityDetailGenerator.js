import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

const STEPS = [
  { id: "source", num: 1, label: "Kaynak Job Seç" },
  { id: "tier1", num: 2, label: "Tier 1 Adayları" },
  { id: "manual", num: 3, label: "Manuel Onay" },
  { id: "generate", num: 4, label: "Sayfa Üret" },
  { id: "astro", num: 5, label: "Astro'ya Gönder" },
  { id: "gate", num: 6, label: "Quality Gate" },
  { id: "report", num: 7, label: "Rapor" },
];

const S = {
  page: { maxWidth: 1200, margin: "0 auto" },
  hero: {
    background: "linear-gradient(135deg, rgba(168,85,247,0.12) 0%, rgba(99,102,241,0.08) 100%)",
    border: "1px solid var(--border)",
    borderRadius: 14,
    padding: "1.25rem 1.5rem",
    marginBottom: "1.25rem",
  },
  card: {
    background: "var(--bg-secondary, rgba(255,255,255,0.03))",
    border: "1px solid var(--border)",
    borderRadius: 12,
    padding: "1.25rem",
    marginBottom: "1rem",
  },
  stepBar: { display: "flex", gap: 4, marginBottom: "1.25rem", flexWrap: "wrap" },
  step: (active, done) => ({
    flex: "1 1 100px",
    padding: "0.5rem 0.6rem",
    borderRadius: 8,
    fontSize: "0.72rem",
    fontWeight: active ? 600 : 400,
    textAlign: "center",
    border: `1px solid ${active ? "#a855f7" : done ? "rgba(16,185,129,0.4)" : "var(--border)"}`,
    background: active ? "rgba(168,85,247,0.15)" : done ? "rgba(16,185,129,0.08)" : "transparent",
    cursor: "pointer",
  }),
  table: { width: "100%", fontSize: "0.8rem", borderCollapse: "collapse" },
  th: { padding: "8px", borderBottom: "1px solid var(--border)", textAlign: "left" },
  td: { padding: "8px", borderBottom: "1px solid var(--border)" },
  btnPrimary: { padding: "0.55rem 1.25rem", borderRadius: 8, fontWeight: 600, border: "none", cursor: "pointer" },
  alertErr: { background: "rgba(248,113,113,0.12)", border: "1px solid rgba(248,113,113,0.35)", borderRadius: 8, padding: "0.75rem", fontSize: "0.85rem" },
  alertOk: { background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.35)", borderRadius: 8, padding: "0.75rem", fontSize: "0.85rem" },
};

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  if (e?.response?.status === 404) return "Endpoint bulunamadı — backend yeniden başlatın";
  return e?.message || "Bilinmeyen hata";
}

function EntityTable({ entities, showSelect, onToggle }) {
  if (!entities?.length) return <p className="hive-muted">Entity yok</p>;
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="hive-table">
        <thead>
          <tr>
            {showSelect && <th>Seç</th>}
            <th>Entity</th>
            <th>Kategori</th>
            <th>Lokasyon</th>
            <th>Web</th>
            <th>IG</th>
            <th>Skor</th>
            <th>Durum</th>
            <th>Sayfa</th>
            <th>Q.Skor</th>
          </tr>
        </thead>
        <tbody>
          {entities.map((e) => (
            <tr key={e.id}>
              {showSelect && (
                <td>
                  <input type="checkbox" checked={!!e.tier1_selected} onChange={() => onToggle?.(e.id, !e.tier1_selected)} />
                </td>
              )}
              <td>{e.name}</td>
              <td>{e.category}</td>
              <td>{e.location}</td>
              <td>{e.website ? "✓" : "—"}</td>
              <td>{e.instagram ? "✓" : "—"}</td>
              <td><strong>{e.tier1_score}</strong></td>
              <td>{e.tier1_selected ? "✅ Tier1" : "—"}</td>
              <td>{e.page_status || "pending"}</td>
              <td>{e.quality_score || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function EntityDetailGenerator() {
  const [step, setStep] = useState("source");
  const [health, setHealth] = useState(null);
  const [placeJobs, setPlaceJobs] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [sourceJobId, setSourceJobId] = useState("");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState(null);
  const [mainSiteUrl, setMainSiteUrl] = useState("https://www.balkutusu.com");
  const [threshold, setThreshold] = useState(70);
  const [astroProjectId, setAstroProjectId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [forcePublish, setForcePublish] = useState(false);

  const loadJob = useCallback(async (id) => {
    if (!id) return null;
    const res = await API.get(`/api/entity-detail/job/${id}`);
    setJob(res.data.job);
    return res.data.job;
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [h, jl, pjl] = await Promise.all([
        API.get("/api/entity-detail/health"),
        API.get("/api/entity-detail/jobs?limit=20"),
        API.get("/api/place-seo/jobs?limit=30"),
      ]);
      setHealth(h.data);
      setJobs(jl.data.jobs || []);
      setPlaceJobs(pjl.data.jobs || []);
      setError("");
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  useEffect(() => {
    refresh();
    const stored = sessionStorage.getItem("entity_detail_job_id");
    if (stored) setJobId(stored);
  }, [refresh]);

  useEffect(() => {
    if (jobId) {
      loadJob(jobId).catch((e) => setError(apiError(e)));
      sessionStorage.setItem("entity_detail_job_id", jobId);
    }
  }, [jobId, loadJob]);

  const handleSelectTier1 = async () => {
    if (!sourceJobId.trim()) {
      setError("Place SEO Pipeline job seçin");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/entity-detail/select-tier1", {
        source_job_id: sourceJobId.trim(),
        main_site_url: mainSiteUrl,
        threshold,
      });
      setJobId(res.data.job_id);
      setMessage(`${res.data.entity_count} entity · ${res.data.tier1_selected} Tier 1 seçildi`);
      await loadJob(res.data.job_id);
      setStep("tier1");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (entityId, selected) => {
    if (!jobId) return;
    setLoading(true);
    try {
      await API.post("/api/entity-detail/manual-selection", {
        job_id: jobId,
        selections: { [entityId]: selected },
      });
      await loadJob(jobId);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!jobId) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/entity-detail/generate-pages", {
        job_id: jobId,
        main_site_url: mainSiteUrl,
        publish_wordpress: true,
        force: forcePublish,
      });
      setMessage(`${res.data.generated_count} sayfa üretildi · ${res.data.published_count} WordPress'te yayında`);
      await loadJob(jobId);
      setStep("gate");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleAstro = async () => {
    if (!jobId) return;
    setLoading(true);
    try {
      const res = await API.post("/api/entity-detail/create-astro-pages", {
        job_id: jobId,
        project_id: astroProjectId,
        main_site_url: mainSiteUrl,
      });
      setMessage(`Astro: ${res.data.entity_pages_written} entity sayfası yazıldı`);
      await loadJob(jobId);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleGate = async () => {
    if (!jobId) return;
    setLoading(true);
    try {
      const res = await API.post("/api/entity-detail/run-quality-gate", { job_id: jobId });
      setMessage(`Quality Gate: deploy_allowed=${res.data.deploy_allowed}`);
      await loadJob(jobId);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!jobId) return;
    setLoading(true);
    try {
      const res = await API.post("/api/entity-detail/export-report", { job_id: jobId });
      setMessage(`Rapor: ${res.data.report_path}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const entities = job?.entities || [];

  return (
    <div className="hive-page">
      <div className="hive-hero">
        <h2>🧩 Entity Detail Generator</h2>
        <p>Tier 1 mekan/entity rehber sayfaları — ilan değil, derin SEO/GEO/AEO içerik</p>
        <div className="hive-hero-meta" style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <span>WP: {health?.wordpress_connected ? "✅ bağlı" : "❌ bağlı değil"}</span>
          <span>Mod: {health?.publish_mode || "real"}</span>
          <span>Tier1 eşik: {health?.tier1_threshold ?? 70}</span>
          <span>Listing Hub: ❌ kullanılmaz</span>
        </div>
      </div>

      {error && <div className="hive-alert-err">{error}</div>}
      {message && <div className="hive-alert-ok">{message}</div>}

      <div className="hive-step-bar">
        {STEPS.map((s) => (
          <button key={s.id} type="button" className={`hive-step ${step === s.id ? "active" : ""}`} onClick={() => setStep(s.id)}>
            {s.num}. {s.label}
          </button>
        ))}
      </div>

      {step === "source" && (
        <div className="hive-card">
          <h3 style={{ marginTop: 0 }}>Place SEO Pipeline Kaynak Job</h3>
          <label style={{ display: "block", marginBottom: "0.75rem", fontSize: "0.85rem" }}>
            Ana site URL
            <input className="hive-input" value={mainSiteUrl} onChange={(e) => setMainSiteUrl(e.target.value)} />
          </label>
          <label style={{ display: "block", marginBottom: "0.75rem", fontSize: "0.85rem" }}>
            Tier 1 eşik skoru
            <input className="hive-input" type="number" min={0} max={100} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} style={{ maxWidth: 120 }} />
          </label>
          <label style={{ display: "block", marginBottom: "1rem", fontSize: "0.85rem" }}>
            Place SEO job
            <select className="hive-input" value={sourceJobId} onChange={(e) => setSourceJobId(e.target.value)}>
              <option value="">— seç —</option>
              {placeJobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.id} · {j.status} · {(j.signals?.entities || []).length} entity
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="btn-primary" disabled={loading || !sourceJobId} onClick={handleSelectTier1} style={S.btnPrimary}>
            Tier 1 Adaylarını Hesapla
          </button>
          {jobs.length > 0 && (
            <div style={{ marginTop: "1.25rem" }}>
              <strong style={{ fontSize: "0.85rem" }}>Önceki Entity Detail job&apos;ları</strong>
              <ul style={{ fontSize: "0.82rem", marginTop: 8 }}>
                {jobs.map((j) => (
                  <li key={j.id}>
                    <button type="button" className="hive-link-btn" onClick={() => { setJobId(j.id); setStep("tier1"); }}>
                      {j.id}
                    </button>
                    {" "}· {(j.entities || []).length} entity
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {step === "tier1" && (
        <div className="hive-card">
          <h3 style={{ marginTop: 0 }}>Tier 1 Adayları {jobId && <code style={{ fontSize: "0.75rem" }}>{jobId}</code>}</h3>
          <EntityTable entities={entities} showSelect={false} />
        </div>
      )}

      {step === "manual" && (
        <div className="hive-card">
          <h3 style={{ marginTop: 0 }}>Manuel Onay</h3>
          <p style={{ fontSize: "0.85rem", opacity: 0.75 }}>Düşük skorlu entity&apos;leri manuel seçebilir veya yüksek skorluları çıkarabilirsiniz.</p>
          <EntityTable entities={entities} showSelect onToggle={handleToggle} />
        </div>
      )}

      {step === "generate" && (
        <div className="hive-card">
          <h3 style={{ marginTop: 0 }}>Sayfa Üret & WordPress Yayınla</h3>
          {!health?.wordpress_connected && (
            <div style={{ ...S.alertErr, marginBottom: "1rem" }}>WordPress bağlı değil — .env kimlik bilgilerini kontrol edin</div>
          )}
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "1rem", fontSize: "0.85rem" }}>
            <input type="checkbox" checked={forcePublish} onChange={(e) => setForcePublish(e.target.checked)} />
            WP yayın zorla (force)
          </label>
          <p style={{ fontSize: "0.85rem" }}>
            Seçili Tier 1: <strong>{entities.filter((e) => e.tier1_selected).length}</strong> entity
          </p>
          <button type="button" className="btn-primary" disabled={loading || !jobId || !entities.some((e) => e.tier1_selected)} onClick={handleGenerate} style={S.btnPrimary}>
            {loading ? "Üretiliyor…" : "Rehber Sayfalarını Üret & Yayınla"}
          </button>
        </div>
      )}

      {step === "astro" && (
        <div className="hive-card">
          <h3 style={{ marginTop: 0 }}>Astro Destek Sitesine Gönder</h3>
          <label style={{ display: "block", marginBottom: "1rem", fontSize: "0.85rem" }}>
            Astro project_id
            <input value={astroProjectId} onChange={(e) => setAstroProjectId(e.target.value)} placeholder="Place SEO astro veya manuel ID" style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }} />
          </label>
          <button type="button" className="btn-primary" disabled={loading || !jobId} onClick={handleAstro} style={S.btnPrimary}>
            entity_pages.json Yaz
          </button>
        </div>
      )}

      {step === "gate" && (
        <div className="hive-card">
          <h3 style={{ marginTop: 0 }}>SEO GEO AEO Quality Gate</h3>
          <button type="button" disabled={loading || !jobId} onClick={handleGate}>Quality Gate Çalıştır</button>
          {job?.quality_gate && (
            <p style={{ marginTop: 12, fontSize: "0.85rem" }}>
              deploy_allowed: <strong style={{ color: job.quality_gate.deploy_allowed ? "#10b981" : "#f87171" }}>{String(job.quality_gate.deploy_allowed)}</strong>
            </p>
          )}
          <EntityTable entities={entities} showSelect={false} />
        </div>
      )}

      {step === "report" && (
        <div className="hive-card">
          <h3 style={{ marginTop: 0 }}>Rapor</h3>
          <button type="button" className="btn-primary" disabled={loading || !jobId} onClick={handleExport} style={S.btnPrimary}>
            JSON Rapor İndir
          </button>
          {job && (
            <pre style={{ marginTop: "1rem", fontSize: "0.75rem", overflow: "auto", maxHeight: 300, background: "rgba(0,0,0,0.2)", padding: 12, borderRadius: 8 }}>
              {JSON.stringify({
                job_id: job.id,
                source_job_id: job.source_job_id,
                tier1_selected: entities.filter((e) => e.tier1_selected).length,
                pages: entities.filter((e) => e.page_status === "published" || e.page_status === "generated").length,
                listing_hub_called: false,
              }, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
