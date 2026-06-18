import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveToolbar,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveTable,
  HiveBadge,
  HiveEmptyState,
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/data-miner";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "url", label: "URL Miner" },
  { id: "keyword", label: "Keyword Miner" },
  { id: "domain", label: "Domain Miner" },
  { id: "entities", label: "Entities" },
  { id: "faqs", label: "FAQs" },
  { id: "datasets", label: "Datasets" },
  { id: "jobs", label: "Jobs" },
  { id: "reports", label: "Reports" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "API hatası";
}

export default function DataMinerEngine() {
  const [tab, setTab] = useState("dashboard");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [url, setUrl] = useState("");
  const [keyword, setKeyword] = useState("");
  const [domain, setDomain] = useState("");
  const [limit, setLimit] = useState(5);
  const [engine, setEngine] = useState("auto");
  const [selectedJob, setSelectedJob] = useState("");
  const [exportFormat, setExportFormat] = useState("json");

  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [settings, setSettings] = useState(null);
  const [integrations, setIntegrations] = useState(null);
  const [exportOut, setExportOut] = useState(null);

  const setLoad = (k, v) => setLoading((l) => ({ ...l, [k]: v }));

  const fetchHealth = useCallback(async () => {
    try {
      const res = await API.get(`${API_PREFIX}/health`);
      setHealth(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
  }, []);

  const fetchDashboard = useCallback(async () => {
    setLoad("dashboard", true);
    try {
      const [dash, integ] = await Promise.all([
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/integrations`),
      ]);
      setDashboard(dash.data);
      setIntegrations(integ.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("dashboard", false);
  }, []);

  const fetchJobs = useCallback(async () => {
    setLoad("jobs", true);
    try {
      const res = await API.get(`${API_PREFIX}/jobs`);
      setJobs(res.data.jobs || []);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("jobs", false);
  }, []);

  const fetchDatasets = useCallback(async () => {
    setLoad("datasets", true);
    try {
      const res = await API.get(`${API_PREFIX}/datasets`);
      setDatasets(res.data.datasets || []);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("datasets", false);
  }, []);

  const fetchSettings = useCallback(async () => {
    try {
      const res = await API.get(`${API_PREFIX}/settings`);
      setSettings(res.data.settings);
    } catch (e) {
      setHata(apiError(e));
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    fetchDashboard();
    fetchSettings();
  }, [fetchHealth, fetchDashboard, fetchSettings]);

  useEffect(() => {
    if (tab === "jobs") fetchJobs();
    if (tab === "datasets") fetchDatasets();
  }, [tab, fetchJobs, fetchDatasets]);

  const handleCrawlUrl = async () => {
    if (!url.trim()) { setHata("URL gerekli"); return; }
    setHata("");
    setLoad("url", true);
    try {
      const res = await API.post(`${API_PREFIX}/crawl-url`, { url, engine });
      setLastResult(res.data);
      if (res.data.job_id) setSelectedJob(res.data.job_id);
      if (!res.data.success) setHata(res.data.error || "Crawl başarısız");
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("url", false);
  };

  const handleCrawlKeyword = async () => {
    if (!keyword.trim()) { setHata("Keyword gerekli"); return; }
    setHata("");
    setLoad("keyword", true);
    try {
      const res = await API.post(`${API_PREFIX}/crawl-keyword`, { keyword, limit, engine });
      setLastResult(res.data);
      if (res.data.job_id) setSelectedJob(res.data.job_id);
      if (!res.data.success) setHata(res.data.error || "provider_missing");
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("keyword", false);
  };

  const handleCrawlDomain = async () => {
    if (!domain.trim()) { setHata("Domain gerekli"); return; }
    setHata("");
    setLoad("domain", true);
    try {
      const res = await API.post(`${API_PREFIX}/crawl-domain`, { domain, limit, engine });
      setLastResult(res.data);
      if (res.data.job_id) setSelectedJob(res.data.job_id);
      if (!res.data.success) setHata(res.data.error || "Crawl başarısız");
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("domain", false);
  };

  const handleExport = async () => {
    if (!selectedJob) { setHata("job_id seçin"); return; }
    setLoad("export", true);
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, { job_id: selectedJob, format: exportFormat });
      setExportOut(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("export", false);
  };

  const loadJobResult = async (jobId) => {
    setLoad("result", true);
    try {
      const res = await API.get(`${API_PREFIX}/results/${encodeURIComponent(jobId)}`);
      setLastResult(res.data.result || res.data);
      setSelectedJob(jobId);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("result", false);
  };

  const providerBadge = (name, info) => {
    const ok = info?.available;
    return <HiveBadge tone={ok ? "ok" : "info"} key={name}>{name}: {ok ? "ok" : (info?.error || info?.reason || "missing")}</HiveBadge>;
  };

  const result = lastResult?.result || lastResult;

  return (
    <HiveShell
      title="Data Miner Engine"
      subtitle="Keşif ve veri çıkarımı — içerik üretmez, yayın yapmaz"
      meta={health ? `v${health.version || "1"} · jobs: ${health.jobs_count ?? 0}` : null}
      actions={<HiveBtn variant="outline" onClick={fetchDashboard} disabled={loading.dashboard}>Yenile</HiveBtn>}
    >
      {hata && <HiveAlert type="err">{hata}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <>
          <HiveStatGrid
            stats={[
              { label: "Toplam Job", value: dashboard?.total_jobs ?? "—" },
              { label: "Active Extractor", value: dashboard?.active_extractor ?? dashboard?.current_provider ?? "—", highlight: true },
              { label: "Fallback Provider", value: dashboard?.fallback_provider ?? "—" },
              { label: "Dataset", value: dashboard?.datasets_count ?? "—" },
            ]}
          />
          <HivePanel title="Provider Status">
            <HiveStatGrid
              stats={[
                { label: "ScrapeGraphAI Installed", value: dashboard?.scrapegraphai_installed ? "Yes" : "No", tone: dashboard?.scrapegraphai_installed ? "ok" : "warn" },
                { label: "LLM Provider", value: dashboard?.scrapegraph_llm_provider ?? health?.providers?.scrapegraphai?.llm_provider ?? "—" },
                { label: "Active Extractor", value: dashboard?.active_extractor ?? "—", tone: "ok" },
                { label: "Fallback Provider", value: dashboard?.fallback_provider ?? (dashboard?.playwright_available ? "playwright" : "beautifulsoup") },
                { label: "Playwright", value: dashboard?.playwright_available ? "Available" : "Missing", tone: dashboard?.playwright_available ? "ok" : "info" },
                { label: "BeautifulSoup", value: dashboard?.beautifulsoup_available ? "Available" : "Missing", tone: dashboard?.beautifulsoup_available ? "ok" : "info" },
              ]}
            />
          </HivePanel>
          {health?.providers && (
            <HivePanel title="Providers">
              <div className="hm-stat-row" style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {Object.entries(health.providers).map(([k, v]) => providerBadge(k, v))}
              </div>
            </HivePanel>
          )}
          {integrations && (
            <p className="hm-meta">HIVE entegrasyonları read-only — {integrations.ready ? "hazır" : "kısmi"}</p>
          )}
        </>
      )}

      {tab === "url" && (
        <HivePanel title="URL Miner" description="Tek URL — telefon, email, FAQ, schema, entity">
          <HiveToolbar>
            <HiveField label="URL"><HiveInput value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://ornek.com" /></HiveField>
            <HiveField label="Engine">
              <select className="hm-select" value={engine} onChange={(e) => setEngine(e.target.value)}>
                <option value="auto">auto</option>
                <option value="beautifulsoup">beautifulsoup</option>
                <option value="playwright">playwright</option>
                <option value="firecrawl">firecrawl</option>
              </select>
            </HiveField>
            <HiveBtn onClick={handleCrawlUrl} disabled={loading.url}>{loading.url ? "…" : "Crawl"}</HiveBtn>
          </HiveToolbar>
        </HivePanel>
      )}

      {tab === "keyword" && (
        <HivePanel title="Keyword Miner" description="Arama sonuçlarını tara — SearXNG/Tavily gerekli">
          <HiveToolbar>
            <HiveField label="Keyword"><HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="kuşadası gece kulübü" /></HiveField>
            <HiveField label="Limit"><HiveInput type="number" value={limit} onChange={(e) => setLimit(parseInt(e.target.value, 10) || 5)} min={1} max={8} /></HiveField>
            <HiveBtn onClick={handleCrawlKeyword} disabled={loading.keyword}>Crawl</HiveBtn>
          </HiveToolbar>
        </HivePanel>
      )}

      {tab === "domain" && (
        <HivePanel title="Domain Miner" description="Rakip domain — entity graph, FAQ/schema/content gap">
          <HiveToolbar>
            <HiveField label="Domain"><HiveInput value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="rakip.com" /></HiveField>
            <HiveBtn onClick={handleCrawlDomain} disabled={loading.domain}>Analiz</HiveBtn>
          </HiveToolbar>
          {result?.gaps && (
            <HiveStatGrid
              stats={[
                { label: "FAQ Gap", value: (result.gaps.faq_gap || []).length, tone: "warn" },
                { label: "Schema Gap", value: (result.gaps.schema_gap || []).length },
                { label: "Content Gap", value: (result.gaps.content_gap || []).length },
              ]}
            />
          )}
        </HivePanel>
      )}

      {(tab === "entities" || tab === "faqs") && (
        <HivePanel title={tab === "entities" ? "Entities" : "FAQs"}>
          {!result ? (
            <HiveEmptyState title="Veri yok" why="Önce URL, keyword veya domain crawl çalıştırın." />
          ) : tab === "entities" ? (
            <HiveTable
              columns={[{ key: "label", label: "Entity" }, { key: "type", label: "Tip" }, { key: "source", label: "Kaynak" }]}
              rows={(result.entities || []).map((e, i) => ({ id: i, ...e }))}
              emptyText="Entity bulunamadı"
            />
          ) : (
            <HiveTable
              columns={[{ key: "question", label: "Soru" }, { key: "answer", label: "Cevap" }]}
              rows={(result.faqs || []).map((f, i) => ({ id: i, question: (f.question || "").slice(0, 80), answer: (f.answer || "").slice(0, 120) }))}
              emptyText="FAQ bulunamadı"
            />
          )}
        </HivePanel>
      )}

      {tab === "datasets" && (
        <HivePanel title="Datasets">
          <HiveBtn variant="outline" onClick={fetchDatasets} disabled={loading.datasets}>Yenile</HiveBtn>
          <HiveTable
            columns={[{ key: "id", label: "ID" }, { key: "type", label: "Tip" }, { key: "source", label: "Kaynak" }, { key: "entities", label: "Entities" }]}
            rows={datasets.map((d) => ({ id: d.id, type: d.type, source: d.source, entities: d.entity_count, key: d.id }))}
            emptyText="Dataset yok"
          />
        </HivePanel>
      )}

      {tab === "jobs" && (
        <HivePanel title="Jobs">
          <HiveBtn variant="outline" onClick={fetchJobs} disabled={loading.jobs}>Yenile</HiveBtn>
          <HiveTable
            columns={[{ key: "job_id", label: "Job" }, { key: "type", label: "Tip" }, { key: "status", label: "Durum" }, { key: "actions", label: "" }]}
            rows={jobs.map((j) => ({
              id: j.job_id,
              job_id: j.job_id,
              type: j.job_type,
              status: j.status,
              actions: <HiveBtn size="sm" variant="outline" onClick={() => loadJobResult(j.job_id)}>Sonuç</HiveBtn>,
            }))}
            emptyText="Job yok"
          />
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel title="Reports">
          <HiveToolbar>
            <HiveField label="Job ID"><HiveInput value={selectedJob} onChange={(e) => setSelectedJob(e.target.value)} /></HiveField>
            <select className="hm-select" value={exportFormat} onChange={(e) => setExportFormat(e.target.value)}>
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
            </select>
            <HiveBtn onClick={handleExport} disabled={loading.export}>Export</HiveBtn>
          </HiveToolbar>
          {settings && (
            <p className="hm-meta">Engine: {settings.engine_preference} · max pages: {settings.max_pages_per_job}</p>
          )}
          {exportOut?.content && (
            <pre className="hm-code-block" style={{ maxHeight: 300, overflow: "auto", fontSize: "0.75rem" }}>{exportOut.content.slice(0, 4000)}</pre>
          )}
        </HivePanel>
      )}

      {result && tab !== "reports" && tab !== "jobs" && tab !== "datasets" && (
        <HivePanel title="Son Çıktı" description={result.job_id ? `Job: ${result.job_id}` : ""}>
          <HiveStatGrid
            stats={[
              { label: "Phones", value: (result.phones || []).length },
              { label: "Emails", value: (result.emails || []).length },
              { label: "Entities", value: (result.entities || []).length },
              { label: "FAQs", value: (result.faqs || []).length },
              { label: "Schema", value: (result.schema_types || []).join(", ") || "—" },
              { label: "Source", value: result.source || "—" },
            ]}
          />
        </HivePanel>
      )}
    </HiveShell>
  );
}
