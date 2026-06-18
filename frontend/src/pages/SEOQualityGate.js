import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

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

export default function SEOQualityGate({ preselectedProjectId = "" }) {
  const [health, setHealth] = useState(null);
  const [projects, setProjects] = useState([]);
  const [reports, setReports] = useState([]);
  const [projectId, setProjectId] = useState(preselectedProjectId || "");
  const [targetKeyword, setTargetKeyword] = useState("");
  const [mainSiteUrl, setMainSiteUrl] = useState("https://www.balkutusu.com");
  const [strictMode, setStrictMode] = useState(true);
  const [analyzeUrl, setAnalyzeUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
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
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
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
    setMessage("");
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
      setMessage(
        `Analiz tamamlandı — Overall ${res.data.overall_score}/100 (${res.data.status})`
      );
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
      setMessage(`URL analizi — skor: ${res.data.overall_score}`);
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
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const handleFixSuggestions = async () => {
    if (!report?.report_id) return;
    setLoading(true);
    try {
      const res = await API.post("/api/seo-quality-gate/fix-suggestions", {
        report_id: report.report_id,
        use_llm: useLlm,
      });
      setSuggestions(res.data.suggestions || []);
      setMessage(`${res.data.count} düzeltme önerisi`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    if (!report?.report_id) return;
    try {
      const res = await API.post("/api/seo-quality-gate/export-report", {
        report_id: report.report_id,
        format,
      });
      setMessage(`Export: ${res.data.path}`);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const statusInfo = report ? STATUS_STYLE[report.status] || STATUS_STYLE.warning : null;
  const readiness = report?.readiness || {};

  return (
    <div className="seo-quality-gate">
      <h2>🛡️ SEO GEO AEO Quality Gate</h2>
      <p className="modul-desc">
        Klasik SEO, GEO local, AEO/AI Overview, entity coverage ve topical authority analizi.
        Deploy: PASS ≥85 · WARNING ≥70 · FAIL &lt;70 · Risk &gt;60 = FAIL
      </p>

      {health && (
        <p className="sf-dim" style={{ marginBottom: "1rem" }}>
          {health.module || "SEO GEO AEO Quality Gate"} · Raporlar: {health.report_count} ·
          Astro: {health.astro_projects} · GEO min: {health.thresholds?.geo_deploy_min} ·
          AEO min: {health.thresholds?.aeo_publisher_min}
        </p>
      )}

      <div className="ch-panel" style={{ marginBottom: "1rem" }}>
        <h4>Proje Analizi</h4>
        <div className="storyforge-meta-row">
          <div>
            <label className="storyforge-label">Astro Projesi</label>
            <select className="storyforge-input" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">— seç —</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.site_name} ({p.slug})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="storyforge-label">Hedef keyword</label>
            <input
              className="storyforge-input"
              value={targetKeyword}
              onChange={(e) => setTargetKeyword(e.target.value)}
              placeholder="kuşadası gece hayatı"
            />
          </div>
          <div>
            <label className="storyforge-label">
              <input type="checkbox" checked={strictMode} onChange={(e) => setStrictMode(e.target.checked)} />
              {" "}Strict mode
            </label>
          </div>
        </div>
        <button type="button" className="btn btn-primary" onClick={handleAnalyzeProject} disabled={loading || !projectId}>
          {loading ? "Analiz…" : "Analyze Project"}
        </button>
      </div>

      <div className="ch-panel" style={{ marginBottom: "1rem" }}>
        <h4>URL Analizi (localhost engelli)</h4>
        <input
          className="storyforge-input"
          value={analyzeUrl}
          onChange={(e) => setAnalyzeUrl(e.target.value)}
          placeholder="https://example.com"
          style={{ marginBottom: "0.5rem", width: "100%" }}
        />
        <button type="button" className="btn btn-secondary" onClick={handleAnalyzeUrl} disabled={loading}>
          Analyze URL
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}
      {message && <div className="success-msg" style={{ color: "#6f6", marginBottom: "0.5rem" }}>{message}</div>}

      {report && (
        <div className="ch-preview-box">
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "2rem", fontWeight: 700 }}>{report.overall_score}</span>
            <span style={{ color: statusInfo?.color, fontWeight: 600 }}>
              Deploy: {statusInfo?.label}
            </span>
            {report.deploy_allowed === false && <span className="ch-warn">Deploy kapalı</span>}
            {report.geo_deploy_allowed === false && <span className="ch-warn">GEO deploy kapalı</span>}
            {report.publisher_hub_allowed === false && <span className="ch-warn">Publisher Hub kapalı</span>}
          </div>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
            <ScoreCard label="SEO" value={report.seo_score} />
            <ScoreCard label="GEO" value={report.geo_score} />
            <ScoreCard label="AEO" value={report.aeo_score} />
            <ScoreCard label="Entity" value={report.entity_score} />
            <ScoreCard label="Authority" value={report.authority_score} />
            <ScoreCard label="Citation" value={report.citation_score} />
            <ScoreCard label="Answerability" value={report.answerability_score} />
            <ScoreCard label="AI Overview %" value={report.overview_probability_score} />
            <ScoreCard label="LLM Visibility" value={report.llm_visibility_score} />
            <ScoreCard label="Risk" value={report.risk_score} invert />
          </div>

          <div className="ch-preview-box" style={{ marginBottom: "1rem", fontSize: 13 }}>
            <h4>Hazırlık Raporu</h4>
            <p>{readiness.google_search_ready ? "✓" : "✗"} Bu sayfa Google klasik arama için hazır mı?</p>
            <p>{readiness.geo_local_ready ? "✓" : "✗"} Bu sayfa GEO/local arama için hazır mı?</p>
            <p>{readiness.ai_overview_ready ? "✓" : "✗"} Bu sayfa AI Overview / answer engine için hazır mı?</p>
            <p>{readiness.support_network_ready ? "✓" : "✗"} Bu sayfa destek ağına dağıtılabilir mi?</p>
          </div>

          <div className="ch-create-actions" style={{ marginBottom: "1rem" }}>
            <button type="button" onClick={handleFixSuggestions} disabled={loading}>
              Fix Suggestions {useLlm ? "(+LLM)" : ""}
            </button>
            <label style={{ marginLeft: "0.5rem" }}>
              <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} /> LLM
            </label>
            <button type="button" onClick={() => handleExport("json")}>Export JSON</button>
            <button type="button" onClick={() => handleExport("md")}>Export Markdown</button>
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
          <table style={{ width: "100%", fontSize: 12 }}>
            <thead>
              <tr>
                <th>Slug</th>
                <th>Tip</th>
                <th>Overall</th>
                <th>SEO</th>
                <th>GEO</th>
                <th>AEO</th>
                <th>Entity</th>
                <th>Kelime</th>
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

          {suggestions.length > 0 && (
            <>
              <h4 style={{ marginTop: "1rem" }}>Fix Suggestions</h4>
              <ul style={{ fontSize: 13 }}>
                {suggestions.map((s, idx) => (
                  <li key={idx}>
                    <strong>[{s.issue_code}]</strong> {s.suggestion}
                    {s.source && <span className="sf-dim"> ({s.source})</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {reports.length > 0 && (
        <div className="ch-panel" style={{ marginTop: "1rem" }}>
          <h4>Geçmiş Raporlar</h4>
          <ul style={{ fontSize: 13 }}>
            {reports.slice(0, 10).map((r) => (
              <li key={r.report_id}>
                <button type="button" className="btn-link" onClick={() => loadReport(r.report_id)}>
                  {r.report_id}
                </button>
                {" "}— {r.overall_score} ({r.status}) — {r.project_slug || r.url || "?"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
