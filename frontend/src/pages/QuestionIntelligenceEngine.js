import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveToolbar,
  HiveTabs,
  HivePanel,
  HiveField,
  HiveSelect,
  HiveInput,
  HiveBtn,
  HiveCard,
  HiveCode,
  HiveCheck,
} from "../components/HiveModuleUI";

const TABS = [
  { id: "faq", label: "FAQ", endpoint: "/api/question-intelligence/generate-faq" },
  { id: "far", label: "FAR", endpoint: "/api/question-intelligence/generate-far" },
  { id: "paa", label: "People Also Ask", endpoint: "/api/question-intelligence/generate-people-also-ask" },
  { id: "autocomplete", label: "Autocomplete", endpoint: "/api/question-intelligence/generate-autocomplete" },
  { id: "related", label: "Related Searches", endpoint: "/api/question-intelligence/generate-related-searches" },
  { id: "reddit", label: "Reddit Intent", endpoint: "/api/question-intelligence/generate-reddit-intent" },
  { id: "decision", label: "Decision", endpoint: "/api/question-intelligence/generate-decision" },
  { id: "entity", label: "Entity Questions", endpoint: "/api/question-intelligence/generate-entity-questions" },
  { id: "location", label: "Location Questions", endpoint: "/api/question-intelligence/generate-location-questions" },
  { id: "comparisons", label: "Comparisons", endpoint: "/api/question-intelligence/generate-comparisons" },
  { id: "bestof", label: "Best Of", endpoint: "/api/question-intelligence/generate-bestof" },
  { id: "problem", label: "Problem Solution", endpoint: "/api/question-intelligence/generate-problem-solution" },
  { id: "local", label: "Local Intent", endpoint: "/api/question-intelligence/generate-local-intent" },
  { id: "objections", label: "Objections", endpoint: "/api/question-intelligence/generate-objections" },
  { id: "overview", label: "AI Overview", endpoint: "/api/question-intelligence/generate-ai-overview" },
  { id: "reports", label: "Reports" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

export default function QuestionIntelligenceEngine({ preselectedProjectId = "" }) {
  const [tab, setTab] = useState("faq");
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(
    preselectedProjectId || sessionStorage.getItem("qie_project_id") || ""
  );
  const [keyword, setKeyword] = useState("kuşadası gece hayatı");
  const [location, setLocation] = useState("Kuşadası");
  const [category, setCategory] = useState("gece hayatı");
  const [count, setCount] = useState(4);
  const [writeAstro, setWriteAstro] = useState(false);
  const [pushGraph, setPushGraph] = useState(true);
  const [health, setHealth] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [exportFormat, setExportFormat] = useState("json");

  const loadProjects = useCallback(async () => {
    try {
      const res = await API.get("/api/astro-factory/projects");
      setProjects(res.data.projects || []);
    } catch {
      setProjects([]);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [h, j] = await Promise.all([
        API.get("/api/question-intelligence/health"),
        API.get("/api/question-intelligence/jobs?limit=20"),
      ]);
      setHealth(h.data);
      setJobs(j.data.jobs || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  useEffect(() => { loadProjects(); refresh(); }, [loadProjects, refresh]);
  useEffect(() => {
    if (projectId) sessionStorage.setItem("qie_project_id", projectId);
  }, [projectId]);

  const baseBody = () => ({
    keyword,
    location,
    category,
    city: "Aydın",
    district: location,
    subcategory: category,
    project_id: projectId,
    write_astro: writeAstro && !!projectId,
    push_entity_graph: pushGraph,
    count,
  });

  const runGenerate = async (endpoint) => {
    if (!keyword.trim()) { setError("Anahtar kelime gerekli"); return; }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await API.post(endpoint, baseBody());
      setResult(res.data);
      setMessage(`${res.data.count || 0} içerik üretildi (job: ${res.data.job_id || "—"})`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runGenerateAll = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/question-intelligence/generate-all", baseBody());
      setResult(res.data);
      setMessage(`Tüm tipler: ${res.data.count} içerik`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runExport = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/question-intelligence/export-report", {
        job_id: result?.job_id || "",
        format: exportFormat,
      });
      setExportPath(res.data.path || "");
      setMessage(`Rapor (${exportFormat}) dışa aktarıldı`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const currentTab = TABS.find((t) => t.id === tab);

  return (
    <HiveShell
      title="🧠 Question Intelligence Engine V2"
      subtitle="Search Intent Intelligence — PAA, Autocomplete, Reddit, Entity/Location soruları"
    >
      <HiveAlert type="ok">{message}</HiveAlert>
      <HiveAlert type="err">{error}</HiveAlert>

      <HiveToolbar>
        <HiveField label="Anahtar kelime" className="hm-field-grow">
          <HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        </HiveField>
        <HiveField label="Konum">
          <HiveInput value={location} onChange={(e) => setLocation(e.target.value)} />
        </HiveField>
        <HiveField label="Kategori">
          <HiveInput value={category} onChange={(e) => setCategory(e.target.value)} />
        </HiveField>
        <HiveField label="Adet" style={{ maxWidth: 90 }}>
          <HiveInput type="number" value={count} onChange={(e) => setCount(Number(e.target.value))} />
        </HiveField>
      </HiveToolbar>

      <HiveToolbar>
        <HiveField label="Astro Proje (opsiyonel)" className="hm-field-grow">
          <HiveSelect value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">— Seçin —</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.site_name || p.slug}</option>
            ))}
          </HiveSelect>
        </HiveField>
        <HiveCheck label="Astro'ya yaz" checked={writeAstro} onChange={(e) => setWriteAstro(e.target.checked)} />
        <HiveCheck label="Entity Graph" checked={pushGraph} onChange={(e) => setPushGraph(e.target.checked)} />
        <div className="hm-toolbar-actions">
          <HiveBtn variant="warning" disabled={loading} onClick={runGenerateAll}>Generate All</HiveBtn>
          <span className="hm-meta-line" style={{ margin: 0 }}>Jobs: <strong>{health?.job_count ?? 0}</strong></span>
        </div>
      </HiveToolbar>

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab !== "reports" && currentTab?.endpoint && (
        <div style={{ marginBottom: "1rem" }}>
          <HiveBtn
            variant="primary"
            disabled={loading}
            onClick={() => runGenerate(currentTab.endpoint)}
          >
            {loading ? "Üretiliyor…" : `${currentTab.label} Üret`}
          </HiveBtn>
        </div>
      )}

      {result?.items?.length > 0 && (
        <HivePanel>
          <h3 className="hm-panel-title">Üretilen içerikler ({result.count})</h3>
          {result.items.map((item, idx) => (
            <HiveCard
              key={item.slug || idx}
              title={
                <>
                  {item.title}
                  <span className="hm-tag">{item.type}</span>
                  <span className="hm-tag hm-tag-intent">{item.intent}</span>
                </>
              }
              meta={
                <>
                  Slug: {item.slug} · Difficulty: {item.difficulty}
                  {" · "}Q-gap: {item.question_gap_score} · PAA-gap: {item.paa_gap_score}
                  {" · "}Auto-gap: {item.autocomplete_gap_score}
                  {item.refresh_candidate && <span className="hm-card-warn"> · Refresh adayı</span>}
                </>
              }
            >
              {item.related_questions?.length > 0 && (
                <div>Related: {item.related_questions.slice(0, 3).join(" · ")}</div>
              )}
              {(item.content_outline || []).length > 0 && (
                <div>Outline: {(item.content_outline || []).slice(0, 4).join(" · ")}</div>
              )}
            </HiveCard>
          ))}
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel>
          <div className="hm-form-row" style={{ marginBottom: "1rem" }}>
            <HiveField label="Format" style={{ maxWidth: 160 }}>
              <HiveSelect value={exportFormat} onChange={(e) => setExportFormat(e.target.value)}>
                <option value="json">JSON</option>
                <option value="markdown">Markdown</option>
              </HiveSelect>
            </HiveField>
            <HiveBtn variant="outline" disabled={loading} onClick={runExport}>Export Report</HiveBtn>
          </div>
          {exportPath && (
            <p className="hm-meta-line">Dosya: <code>{exportPath}</code></p>
          )}
          <h3 className="hm-panel-title" style={{ marginTop: "1rem" }}>Son Jobs</h3>
          {jobs.length ? jobs.map((j) => (
            <HiveCard
              key={j.job_id}
              title={j.job_id}
              meta={`${j.type} · ${j.status} · ${j.count || 0} item`}
            />
          )) : (
            <p className="hm-empty">Henüz job yok.</p>
          )}
        </HivePanel>
      )}

      {result?.overview && tab === "overview" && (
        <HiveCode>{JSON.stringify(result.overview, null, 2)}</HiveCode>
      )}
    </HiveShell>
  );
}
