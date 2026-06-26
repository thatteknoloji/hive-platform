import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";

import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveTable,
  HiveCard,
  HiveCheck,
  HiveCode,
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/crawl-gap";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "domain_crawl", label: "Domain Crawl" },
  { id: "competitor", label: "Competitor Analysis" },
  { id: "entities", label: "Entities" },
  { id: "faqs", label: "FAQs" },
  { id: "geo", label: "GEO" },
  { id: "clusters", label: "Clusters" },
  { id: "ai", label: "AI Overview" },
  { id: "opportunities", label: "Opportunities" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const REPORT_TYPES = [
  { id: "overview", label: "Overview" },
  { id: "entity", label: "Entity Gap Report" },
  { id: "faq", label: "FAQ Gap Report" },
  { id: "geo", label: "GEO Gap Report" },
  { id: "cluster", label: "Cluster Gap Report" },
  { id: "ai", label: "AI Overview Gap Report" },
  { id: "authority", label: "Authority Gap Report" },
  { id: "competitor", label: "Competitor Gap Report" },
  { id: "quick_win", label: "Quick Win Gap Report" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

export default function CrawlGapEngine() {
  const [tab, setTab] = useState("dashboard");
  const [projectId, setProjectId] = useState(sessionStorage.getItem("crawl_gap_project_id") || "");
  const [ownDomain, setOwnDomain] = useState("");
  const [competitors, setCompetitors] = useState("");
  const [health, setHealth] = useState(null);
  const [settings, setSettings] = useState(null);
  const [dash, setDash] = useState(null);
  const [entities, setEntities] = useState([]);
  const [faqs, setFaqs] = useState([]);
  const [geo, setGeo] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [aiGaps, setAiGaps] = useState([]);
  const [authorityGaps, setAuthorityGaps] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [lastAnalysis, setLastAnalysis] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [exportToOpp, setExportToOpp] = useState(false);

  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";

  const refresh = useCallback(async () => {
    try {
      const [h, s, d, e, f, g, c, a, o, j] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/dashboard${q}`).catch(() => ({ data: null })),
        API.get(`${API_PREFIX}/entities${q}`).catch(() => ({ data: { entities: [] } })),
        API.get(`${API_PREFIX}/faqs${q}`).catch(() => ({ data: { faqs: [] } })),
        API.get(`${API_PREFIX}/geo${q}`).catch(() => ({ data: { geo: [] } })),
        API.get(`${API_PREFIX}/clusters${q}`).catch(() => ({ data: { clusters: [] } })),
        API.get(`${API_PREFIX}/ai${q}`).catch(() => ({ data: { ai_gaps: [] } })),
        API.get(`${API_PREFIX}/opportunities${q}`).catch(() => ({ data: { opportunities: [] } })),
        API.get(`${API_PREFIX}/jobs?limit=20`).catch(() => ({ data: { jobs: [] } })),
      ]);
      setHealth(h.data);
      setSettings(s.data.settings || s.data);
      setDash(d.data);
      setEntities(e.data.entities || []);
      setFaqs(f.data.faqs || []);
      setGeo(g.data.geo || []);
      setClusters(c.data.clusters || []);
      setAiGaps(a.data.ai_gaps || []);
      setOpportunities(o.data.opportunities || []);
      setJobs(j.data.jobs || []);
    } catch (err) {
      setError(apiError(err));
    }
  }, [q]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (projectId) sessionStorage.setItem("crawl_gap_project_id", projectId);
  }, [projectId]);

  const analyzeDomain = async () => {
    if (!ownDomain.trim() && !competitors.trim()) {
      setError("Own domain veya rakip domain gerekli");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const compList = competitors.split(",").map((x) => x.trim()).filter(Boolean);
      const res = await API.post(`${API_PREFIX}/analyze-domain`, {
        own_domain: ownDomain.trim(),
        competitor_domains: compList,
        project_id: projectId || undefined,
        export_to_opportunity: exportToOpp,
      });
      setLastAnalysis(res.data.analysis);
      setMessage(`Crawl tamamlandı — ${res.data.analysis?.pages_crawled_total || 0} sayfa, job: ${res.data.job_id || "—"}`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const analyzeProject = async () => {
    if (!projectId.trim()) {
      setError("Proje ID gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const compList = competitors.split(",").map((x) => x.trim()).filter(Boolean);
      const res = await API.post(`${API_PREFIX}/analyze-project`, {
        project_id: projectId.trim(),
        competitor_domains: compList,
        export_to_opportunity: exportToOpp,
      });
      setLastAnalysis(res.data.analysis);
      setMessage("Proje crawl & gap analizi tamamlandı");
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const analyzeCompetitor = async () => {
    const comp = competitors.split(",")[0]?.trim();
    if (!comp) {
      setError("Rakip domain gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/analyze-competitor`, {
        competitor_domain: comp,
        own_domain: ownDomain.trim() || undefined,
        project_id: projectId || undefined,
      });
      setLastAnalysis(res.data.analysis);
      setMessage(`Rakip analiz: ${comp}`);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const compareDomain = async () => {
    const comp = competitors.split(",")[0]?.trim();
    if (!ownDomain.trim() || !comp) {
      setError("Own domain ve rakip domain gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/compare-domain`, {
        own_domain: ownDomain.trim(),
        competitor_domain: comp,
        project_id: projectId || undefined,
      });
      setComparison(res.data.comparison);
      setLastAnalysis(res.data.analysis);
      setMessage("Domain karşılaştırması tamamlandı");
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (reportType) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ report_type: reportType });
      if (projectId) params.set("project_id", projectId);
      if (ownDomain.trim()) params.set("domain", ownDomain.trim());
      const res = await API.post(`${API_PREFIX}/export-report?${params}`);
      setExportPath(res.data.path || "");
      setMessage(`${reportType} raporu dışa aktarıldı`);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const exportOpportunities = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ export: "true" });
      if (projectId) params.set("project_id", projectId);
      const res = await API.get(`${API_PREFIX}/opportunities?${params}`);
      if (res.data.export?.success) {
        setMessage(`Opportunity Engine'e ${res.data.export.imported} crawl_gap_opportunity aktarıldı`);
      } else {
        setError(res.data.export?.message || res.data.export?.error || "Aktarım başarısız");
      }
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async (patch) => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/settings`, patch);
      setSettings(res.data.settings || res.data);
      setMessage("Ayarlar kaydedildi");
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const stats = dash?.gap_stats || {};
  const integrationErrors = health?.integration_errors || [];

  return (
    <HiveShell title="Crawl & Gap Engine" subtitle="Site crawl — entity, FAQ, GEO, cluster, authority & AI gap analizi">
      {message && <HiveAlert tone="ok" onClose={() => setMessage("")}>{message}</HiveAlert>}
      {error && <HiveAlert tone="danger" onClose={() => setError("")}>{error}</HiveAlert>}

      <HivePanel>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <HiveField label="Proje ID">
            <HiveInput value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="prj-..." />
          </HiveField>
          <HiveField label="Own Domain">
            <HiveInput value={ownDomain} onChange={(e) => setOwnDomain(e.target.value)} placeholder="https://example.com" />
          </HiveField>
          <HiveField label="Rakipler (virgülle)">
            <HiveInput value={competitors} onChange={(e) => setCompetitors(e.target.value)} placeholder="rakip1.com, rakip2.com" />
          </HiveField>
          <HiveCheck label="Opportunity'ye aktar" checked={exportToOpp} onChange={setExportToOpp} />
          <HiveBtn onClick={analyzeDomain} disabled={loading}>Domain Analiz</HiveBtn>
          <HiveBtn onClick={analyzeProject} disabled={loading || !projectId} variant="secondary">Proje Analiz</HiveBtn>
          <HiveBtn onClick={refresh} disabled={loading} variant="ghost">Yenile</HiveBtn>
        </div>
      </HivePanel>

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <HivePanel title="Dashboard">
          <HiveStatGrid stats={[
            ["Crawled Domains", dash?.domains_crawled ?? "—"],
            ["Pages Crawled", dash?.pages_crawled ?? "—"],
            ["Entity Gaps", dash?.entity_gaps ?? stats.entity_gap_count ?? "—"],
            ["FAQ Gaps", dash?.faq_gaps ?? stats.faq_gap_count ?? "—"],
            ["GEO Gaps", dash?.geo_gaps ?? stats.geo_gap_count ?? "—"],
            ["Critical Gaps", dash?.critical_gaps ?? stats.critical_gap_count ?? "—"],
            ["Quick Wins", dash?.quick_wins ?? stats.quick_win_count ?? "—"],
          ]} />
          {integrationErrors.length > 0 && (
            <HiveAlert tone="warn">
              Entegrasyon: {integrationErrors.map((e) => e.module).join(", ")}
            </HiveAlert>
          )}
          {(dash?.action_plan || []).length > 0 && (
            <>
              <h4>Action Plan</h4>
              <HiveTable
                columns={["Aksiyon", "Adet", "Öncelik"]}
                rows={(dash.action_plan || []).map((a) => [a.action, a.count, a.priority])}
              />
            </>
          )}
          {dash?.defense_risks?.critical_gaps?.length > 0 && (
            <HiveAlert tone="warn">
              SERP Defense risk (+{dash.defense_risks.attack_surface_boost || 0} attack surface):{" "}
              {(dash.defense_risks.critical_gaps || []).map((g) => g.type).join(", ")}
            </HiveAlert>
          )}
          {jobs.length > 0 && (
            <HiveCard title="Son Job'lar">
              <HiveTable
                columns={["Job ID", "Tip", "Durum", "Sayfa", "Başlangıç"]}
                rows={jobs.slice(0, 5).map((j) => [j.job_id, j.type, j.status, j.pages_crawled ?? "—", j.started_at])}
              />
            </HiveCard>
          )}
        </HivePanel>
      )}

      {tab === "domain_crawl" && (
        <HivePanel title="Domain Crawl">
          <HiveBtn onClick={analyzeDomain} disabled={loading}>Crawl Başlat</HiveBtn>
          {lastAnalysis?.crawl_results?.length ? (
            <HiveTable
              columns={["Domain", "Rol", "Sayfa"]}
              rows={lastAnalysis.crawl_results.map((c) => [c.domain, c.role, c.pages_crawled])}
            />
          ) : (
            <p>Henüz crawl yok — domain veya proje analiz edin.</p>
          )}
          {lastAnalysis?.page_scores?.length > 0 && (
            <HiveCard title="Sayfa Gap Skorları">
              <HiveTable
                columns={["URL", "Coverage", "Entity", "FAQ", "GEO", "Cluster", "AI", "Authority", "Overall Gap"]}
                rows={lastAnalysis.page_scores.slice(0, 15).map((p) => [
                  (p.url || "").slice(0, 40),
                  p.coverage_score,
                  p.entity_gap_score,
                  p.faq_gap_score,
                  p.geo_gap_score,
                  p.cluster_gap_score,
                  p.ai_gap_score,
                  p.authority_gap_score,
                  p.overall_gap_score,
                ])}
              />
            </HiveCard>
          )}
          {lastAnalysis?.content_refresh_recommendations?.length > 0 && (
            <HiveCard title="Content Refresh Önerileri (plan only)">
              <HiveTable
                columns={["URL", "Gap Skor", "Aksiyonlar"]}
                rows={lastAnalysis.content_refresh_recommendations.slice(0, 10).map((r) => [
                  (r.page_url || "").slice(0, 50),
                  r.overall_gap_score,
                  (r.recommended_actions || []).join(", "),
                ])}
              />
            </HiveCard>
          )}
        </HivePanel>
      )}

      {tab === "competitor" && (
        <HivePanel title="Competitor Analysis">
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <HiveBtn onClick={analyzeCompetitor} disabled={loading}>Rakip Analiz</HiveBtn>
            <HiveBtn onClick={compareDomain} disabled={loading} variant="secondary">Domain Karşılaştır</HiveBtn>
          </div>
          {comparison && (
            <HiveStatGrid stats={[
              ["Own Sayfa", comparison.pages_crawled_own ?? "—"],
              ["Rakip Sayfa", comparison.pages_crawled_competitor ?? "—"],
              ["Entity Gap", comparison.gap_stats?.entity_gap_count ?? "—"],
              ["FAQ Gap", comparison.gap_stats?.faq_gap_count ?? "—"],
              ["Critical", (comparison.critical_gaps || []).length],
              ["Quick Win", (comparison.quick_wins || []).length],
            ]} />
          )}
          {lastAnalysis?.qie_questions?.length > 0 && (
            <HiveCard title="QIE FAQ Önerileri">
              <HiveTable
                columns={["Soru", "Intent", "Engine"]}
                rows={lastAnalysis.qie_questions.slice(0, 15).map((q) => [q.question?.slice(0, 60), q.intent, q.recommended_engine])}
              />
            </HiveCard>
          )}
        </HivePanel>
      )}

      {tab === "entities" && (
        <HivePanel title="Entity Gaps">
          <HiveTable
            columns={["Entity", "Rakip", "Biz", "Gap Skor", "Öncelik"]}
            rows={entities.map((e) => [
              e.entity,
              e.competitor_mentions ?? "—",
              e.our_mentions ?? "—",
              e.gap_score ?? e.overall_gap_score ?? "—",
              e.priority,
            ])}
            empty="Entity gap yok — önce analiz çalıştırın"
          />
        </HivePanel>
      )}

      {tab === "faqs" && (
        <HivePanel title="FAQ Gaps">
          <HiveTable
            columns={["Soru", "Gap Skor", "Öncelik"]}
            rows={faqs.map((f) => [(f.question || f.title || "").slice(0, 80), f.overall_gap_score ?? "—", f.priority])}
            empty="FAQ gap yok"
          />
        </HivePanel>
      )}

      {tab === "geo" && (
        <HivePanel title="GEO Gaps">
          <HiveTable
            columns={["Lokasyon", "Seviye", "Gap Skor", "Öncelik"]}
            rows={geo.map((g) => [g.location, g.level, g.overall_gap_score ?? "—", g.priority])}
            empty="GEO gap yok"
          />
        </HivePanel>
      )}

      {tab === "clusters" && (
        <HivePanel title="Cluster Gaps">
          <HiveTable
            columns={["Konu", "Tip", "Gap Skor", "Öncelik"]}
            rows={clusters.map((c) => [c.topic, c.type, c.overall_gap_score ?? "—", c.priority])}
            empty="Cluster gap yok"
          />
        </HivePanel>
      )}

      {tab === "ai" && (
        <HivePanel title="AI Overview Gaps">
          {aiGaps.length === 0 ? (
            <HiveAlert tone="warn">AI gap verisi yok — DataForSEO yapılandırın veya analiz çalıştırın</HiveAlert>
          ) : (
            <HiveTable
              columns={["Keyword", "AI Overview", "Rakip Block", "Öncelik"]}
              rows={aiGaps.map((a) => [
                a.keyword,
                a.ai_overview_present ? "Var" : "Yok",
                a.competitor_answer_blocks,
                a.priority,
              ])}
            />
          )}
        </HivePanel>
      )}

      {tab === "opportunities" && (
        <HivePanel title="Gap → Opportunity (crawl_gap_opportunity)">
          <HiveBtn onClick={exportOpportunities} disabled={loading || !projectId}>
            Opportunity Engine'e Aktar
          </HiveBtn>
          <HiveTable
            columns={["Fırsat", "Tip", "Skor", "Gain", "Aksiyon"]}
            rows={opportunities.slice(0, 30).map((o) => [
              (o.title || "").slice(0, 60),
              o.type,
              o.opportunity_score,
              o.estimated_gain ?? "—",
              (o.action_plan || []).join(", "),
            ])}
            empty="Gap fırsatı yok"
          />
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel title="Raporlar">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            {REPORT_TYPES.map((rt) => (
              <HiveBtn key={rt.id} variant="secondary" onClick={() => exportReport(rt.id)} disabled={loading}>
                {rt.label}
              </HiveBtn>
            ))}
          </div>
          {exportPath && <HiveCode value={exportPath} />}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel title="Ayarlar">
          <HiveCheck
            label="Crawl & Gap aktif"
            checked={!!settings.enabled}
            onChange={(v) => saveSettings({ enabled: v })}
          />
          <HiveField label="Max sayfa / domain">
            <HiveInput
              type="number"
              value={settings.max_pages_per_domain ?? 100}
              onChange={(e) => saveSettings({ max_pages_per_domain: Number(e.target.value) })}
            />
          </HiveField>
          <HiveField label="Crawl timeout (sn)">
            <HiveInput
              type="number"
              value={settings.crawl_timeout_seconds ?? 20}
              onChange={(e) => saveSettings({ crawl_timeout_seconds: Number(e.target.value) })}
            />
          </HiveField>
          <HiveCheck
            label="robots.txt dikkate al"
            checked={settings.respect_robots_txt !== false}
            onChange={(v) => saveSettings({ respect_robots_txt: v })}
          />
          <HiveCheck
            label="Rakip crawl izni"
            checked={settings.allow_competitor_crawl !== false}
            onChange={(v) => saveSettings({ allow_competitor_crawl: v })}
          />
          <HiveCheck
            label="Otomatik Opportunity aktarımı"
            checked={!!settings.auto_send_to_opportunity || !!settings.export_to_opportunity_on_analyze}
            onChange={(v) => saveSettings({ auto_send_to_opportunity: v, export_to_opportunity_on_analyze: v })}
          />
          <HiveCheck
            label="SERP Defense gap payload"
            checked={!!settings.auto_send_to_serp_defense}
            onChange={(v) => saveSettings({ auto_send_to_serp_defense: v })}
          />
          <HiveField label="Kritik gap eşiği">
            <HiveInput
              type="number"
              value={settings.critical_gap_threshold ?? 65}
              onChange={(e) => saveSettings({ critical_gap_threshold: Number(e.target.value) })}
            />
          </HiveField>
        </HivePanel>
      )}
    </HiveShell>
  );
}
