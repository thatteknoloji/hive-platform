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
  HiveStatGrid,
} from "../components/HiveModuleUI";

const STATUS_STYLE = {
  pass: { label: "PASS", color: "#4ade80" },
  warning: { label: "WARNING", color: "#fbbf24" },
  fail: { label: "FAIL", color: "#f87171" },
};

function ScoreCard({ label, value, invert }) {
  const v = value ?? 0;
  const color = invert
    ? (v <= 30 ? "#4ade80" : v <= 60 ? "#fbbf24" : "#f87171")
    : (v >= 85 ? "#4ade80" : v >= 70 ? "#fbbf24" : "#f87171");
  return (
    <div className="hive-stat" style={{ minWidth: 100 }}>
      <div className="hive-stat-label">{label}</div>
      <div className="hive-stat-value" style={{ color }}>{v}</div>
    </div>
  );
}

const QG_TOOLTIP = "Quality Gate, içeriğinizi SEO/GEO/AEO açısından analiz eder. PASS (≥85) deploy için yeterlidir. WARNING (70-84) düzeltme önerir. FAIL (<70) düzeltme gerektirir.";

export default function SEOQualityGate({ preselectedProjectId = "" }) {
  const [health, setHealth] = useState(null);
  const [projects, setProjects] = useState([]);
  const [reports, setReports] = useState([]);
  const [projectId, setProjectId] = useState(preselectedProjectId || "");
  const [targetKeyword, setTargetKeyword] = useState("");
  const [mainSiteUrl, setMainSiteUrl] = useProjectSiteField();
  const [strictMode, setStrictMode] = useState(true);
  const [analyzeUrl, setAnalyzeUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [report, setReport] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [useLlm, setUseLlm] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [h, pl, rl] = await Promise.all([
        API.get("/api/seo-quality-gate/health"),
        API.get("/api/astro-factory/projects"),
        API.get("/api/seo-quality-gate/reports"),
      ]);
      setHealth(h.data);
      setProjects(pl.data.projects || []);
      setReports(rl.data.reports || []);
      setError("");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setInitialLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const stored = sessionStorage.getItem("seo_qg_project_id");
    if (stored && !preselectedProjectId) setProjectId(stored);
  }, [refresh, preselectedProjectId]);

  useEffect(() => {
    if (preselectedProjectId) setProjectId(preselectedProjectId);
  }, [preselectedProjectId]);

  const handleAnalyzeProject = async () => {
    if (!projectId) { setError("Proje seçin"); return; }
    setLoading(true);
    setError("");
    setReport(null);
    setSuggestions([]);
    try {
      const proj = projects.find((p) => p.id === projectId);
      const res = await API.post("/api/seo-quality-gate/analyze-project", {
        project_id: projectId,
        target_keyword: targetKeyword || proj?.seed_keyword || "",
        main_site_url: mainSiteUrl,
        strict_mode: strictMode,
      });
      setReport(res.data);
      setToast(`Analiz tamamlandı — Overall ${res.data.overall_score}/100 (${res.data.status})`);
      await refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeUrl = async () => {
    if (!analyzeUrl.trim()) { setError("URL girin"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/seo-quality-gate/analyze-url", {
        url: analyzeUrl.trim(),
        target_keyword: targetKeyword,
        strict_mode: strictMode,
      });
      setReport(res.data);
      setToast(`URL analizi — skor: ${res.data.overall_score}`);
      await refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadReport = async (reportId) => {
    try {
      const res = await API.get(`/api/seo-quality-gate/report/${reportId}`);
      setReport(res.data.report);
      setToast("Rapor yüklendi");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const handleFixSuggestions = async () => {
    if (!report?.report_id) return;
    setLoading(true);
    try {
      const res = await API.post("/api/seo-quality-gate/fix-suggestions", { report_id: report.report_id, use_llm: useLlm });
      setSuggestions(res.data.suggestions || []);
      setToast(`${res.data.count} düzeltme önerisi`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    if (!report?.report_id) return;
    try {
      const res = await API.post("/api/seo-quality-gate/export-report", { report_id: report.report_id, format });
      setToast(`Export: ${res.data.path}`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const statusInfo = report ? STATUS_STYLE[report.status] || STATUS_STYLE.warning : null;
  const readiness = report?.readiness || {};

  if (initialLoading) {
    return (
      <HiveShell title="🛡️ SEO GEO AEO Quality Gate" subtitle="Klasik SEO, GEO local, AEO/AI Overview, entity coverage ve topical authority analizi">
        <HiveSkeleton lines={8} />
      </HiveShell>
    );
  }

  return (
    <HiveShell
      title="🛡️ SEO GEO AEO Quality Gate"
      subtitle="Klasik SEO, GEO local, AEO/AI Overview, entity coverage ve topical authority analizi"
    >
      <HiveTooltip content={QG_TOOLTIP}>
        <HiveAlert variant="info" style={{ marginBottom: "0.75rem" }}>
          Deploy: PASS ≥85 · WARNING ≥70 · FAIL &lt;70 · Risk &gt;60 = FAIL
        </HiveAlert>
      </HiveTooltip>

      {error && <HiveAlert variant="error">{error}</HiveAlert>}
      {toast && <HiveToast message={toast} onClose={() => setToast("")} />}

      {health && (
        <p style={{ fontSize: "0.8rem", marginBottom: "1rem", opacity: 0.6 }}>
          {health.module || "SEO GEO AEO Quality Gate"} · Raporlar: {health.report_count} ·
          Astro: {health.astro_projects} · GEO min: {health.thresholds?.geo_deploy_min} ·
          AEO min: {health.thresholds?.aeo_publisher_min}
        </p>
      )}

      {projects.length === 0 ? (
        <HiveEmptyState title="Astro proje bulunamadı" message="Önce bir Astro projesi oluşturun." />
      ) : (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1rem", maxWidth: 600 }}>
            <div>
              <label style={{ fontSize: "0.85rem", opacity: 0.6 }}>
                <HiveTooltip content="Analiz edilecek Astro projesi">Astro Projesi</HiveTooltip>
              </label>
              <select value={projectId} onChange={(e) => setProjectId(e.target.value)}
                style={{ width: "100%", padding: "0.5rem" }}>
                <option value="">— seç —</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.site_name} ({p.slug})</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.85rem", opacity: 0.6 }}>
                <HiveTooltip content="Analizin merkez keyword'ü">Hedef keyword</HiveTooltip>
              </label>
              <input value={targetKeyword} onChange={(e) => setTargetKeyword(e.target.value)}
                style={{ width: "100%", padding: "0.5rem" }} placeholder="kuşadası gece hayatı" />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <label>
                <input type="checkbox" checked={strictMode} onChange={(e) => setStrictMode(e.target.checked)} />
                {" "}Strict mode
              </label>
              <HiveTooltip content="Strict mode: daha sıkı eşikler uygulanır (PASS ≥90)">?</HiveTooltip>
            </div>
            <HiveBtn onClick={handleAnalyzeProject} disabled={loading || !projectId}>
              {loading ? "Analiz…" : "Analyze Project"}
            </HiveBtn>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1rem", maxWidth: 600 }}>
            <span style={{ fontSize: "0.85rem", opacity: 0.6 }}>
              <HiveTooltip content="Tek bir URL'yi analiz eder. localhost engellidir.">URL Analizi</HiveTooltip>
            </span>
            <input value={analyzeUrl} onChange={(e) => setAnalyzeUrl(e.target.value)}
              placeholder="https://example.com" style={{ width: "100%", padding: "0.5rem" }} />
            <HiveBtn variant="secondary" onClick={handleAnalyzeUrl} disabled={loading}>Analyze URL</HiveBtn>
          </div>
        </>
      )}

      {report && (
        <div style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: "1rem", marginTop: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "2rem", fontWeight: 700 }}>{report.overall_score}</span>
            <span style={{ color: statusInfo?.color, fontWeight: 600 }}>Deploy: {statusInfo?.label}</span>
            {report.deploy_allowed === false && <span style={{ color: "#f87171" }}>Deploy kapalı</span>}
            {report.geo_deploy_allowed === false && <span style={{ color: "#f87171" }}>GEO deploy kapalı</span>}
            {report.publisher_hub_allowed === false && <span style={{ color: "#f87171" }}>Publisher Hub kapalı</span>}
          </div>

          <HiveStatGrid items={[
            { label: "SEO", value: report.seo_score, variant: report.seo_score >= 85 ? "ok" : report.seo_score >= 70 ? "warn" : "error" },
            { label: "GEO", value: report.geo_score, variant: report.geo_score >= 85 ? "ok" : report.geo_score >= 70 ? "warn" : "error" },
            { label: "AEO", value: report.aeo_score, variant: report.aeo_score >= 85 ? "ok" : report.aeo_score >= 70 ? "warn" : "error" },
            { label: "Entity", value: report.entity_score, variant: report.entity_score >= 85 ? "ok" : report.entity_score >= 70 ? "warn" : "error" },
            { label: "Authority", value: report.authority_score, variant: report.authority_score >= 85 ? "ok" : report.authority_score >= 70 ? "warn" : "error" },
            { label: "Citation", value: report.citation_score, variant: report.citation_score >= 85 ? "ok" : report.citation_score >= 70 ? "warn" : "error" },
            { label: "Answerability", value: report.answerability_score, variant: report.answerability_score >= 85 ? "ok" : report.answerability_score >= 70 ? "warn" : "error" },
            { label: "AI Overview %", value: report.overview_probability_score, variant: report.overview_probability_score >= 70 ? "ok" : "warn" },
            { label: "LLM Visibility", value: report.llm_visibility_score, variant: report.llm_visibility_score >= 70 ? "ok" : "warn" },
            { label: "Risk", value: report.risk_score, variant: report.risk_score <= 30 ? "ok" : report.risk_score <= 60 ? "warn" : "error" },
          ]} />

          <div style={{ margin: "1rem 0", padding: "0.75rem", background: "rgba(255,255,255,0.03)", borderRadius: 8, fontSize: 13 }}>
            <h4>Hazırlık Raporu</h4>
            <p>{readiness.google_search_ready ? "✓" : "✗"} Google klasik arama için hazır</p>
            <p>{readiness.geo_local_ready ? "✓" : "✗"} GEO/local arama için hazır</p>
            <p>{readiness.ai_overview_ready ? "✓" : "✗"} AI Overview / answer engine için hazır</p>
            <p>{readiness.support_network_ready ? "✓" : "✗"} Destek ağına dağıtılabilir</p>
          </div>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
            <HiveBtn variant="secondary" onClick={handleFixSuggestions} disabled={loading}>
              Fix Suggestions {useLlm ? "(+LLM)" : ""}
            </HiveBtn>
            <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} /> LLM
            </label>
            <HiveBtn variant="ghost" onClick={() => handleExport("json")}>Export JSON</HiveBtn>
            <HiveBtn variant="ghost" onClick={() => handleExport("md")}>Export Markdown</HiveBtn>
          </div>

          {report.critical_issues?.length > 0 && (
            <>
              <h4 style={{ color: "#f87171" }}>Critical ({report.critical_issues.length})</h4>
              <ul style={{ fontSize: 13 }}>
                {report.critical_issues.map((i) => (
                  <li key={`${i.code}-${i.page}`}>[{i.code}] {i.message}</li>
                ))}
              </ul>
            </>
          )}

          {report.warnings?.length > 0 && (
            <>
              <h4 style={{ color: "#fbbf24" }}>Warnings ({report.warnings.length})</h4>
              <ul style={{ fontSize: 13 }}>
                {report.warnings.slice(0, 20).map((i) => (
                  <li key={`${i.code}-${i.page}-w`}>[{i.code}] {i.message}</li>
                ))}
              </ul>
            </>
          )}

          <h4>Sayfalar</h4>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", fontSize: 12 }}>
              <thead>
                <tr>
                  <th>Slug</th><th>Tip</th><th>Overall</th><th>SEO</th><th>GEO</th><th>AEO</th><th>Entity</th><th>Kelime</th>
                </tr>
              </thead>
              <tbody>
                {(report.pages || []).map((p) => (
                  <tr key={p.slug || "home"}>
                    <td>{p.slug || "home"}</td>
                    <td>{p.type}</td>
                    <td>{p.score}</td>
                    <td>{p.seo_score ?? "—"}</td>
                    <td>{p.geo_score ?? "—"}</td>
                    <td>{p.aeo_score ?? "—"}</td>
                    <td>{p.entity_coverage_score ?? "—"}</td>
                    <td>{p.word_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {suggestions.length > 0 && (
            <>
              <h4 style={{ marginTop: "1rem" }}>Fix Suggestions</h4>
              <ul style={{ fontSize: 13 }}>
                {suggestions.map((s, idx) => (
                  <li key={idx}>
                    <strong>[{s.issue_code}]</strong> {s.suggestion}
                    {s.source && <span style={{ opacity: 0.6 }}> ({s.source})</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {reports.length > 0 && (
        <div style={{ marginTop: "1rem", padding: "0.75rem", borderRadius: 8, background: "rgba(255,255,255,0.03)" }}>
          <h4>Geçmiş Raporlar</h4>
          <ul style={{ fontSize: 13 }}>
            {reports.slice(0, 10).map((r) => (
              <li key={r.report_id}>
                <button type="button" className="btn-link" onClick={() => loadReport(r.report_id)}>
                  {r.report_id}
                </button>
                {" — "}{r.overall_score} ({r.status}) — {r.project_slug || r.url || "?"}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!report && reports.length === 0 && !loading && (
        <HiveEmptyState title="Henüz analiz yapılmadı" message="Analyze Project ile SEO/GEO/AEO kalite analizi başlatın." />
      )}
    </HiveShell>
  );
}
