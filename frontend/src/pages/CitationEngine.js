import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveAlert,
  HiveBtn,
  HiveCheck,
  HiveConceptTooltip,
  HiveField,
  HiveInput,
  HiveLabelWithTip,
  HivePanel,
  HiveSection,
  HiveShell,
  HiveSkeleton,
  HiveStatGrid,
  HiveStatusBadge,
  HiveTable,
  HiveTabs,
  HiveToast,
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/citation";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "pages", label: "Pages" },
  { id: "entities", label: "Entities" },
  { id: "visibility", label: "Visibility" },
  { id: "competitors", label: "Competitors" },
  { id: "opportunities", label: "Opportunities" },
  { id: "revenue", label: "Revenue Impact" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

function scoreVariant(s) {
  const n = Number(s) || 0;
  if (n >= 75) return "ok";
  if (n >= 50) return "warn";
  return "error";
}

export default function CitationEngine() {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [settings, setSettings] = useState(null);
  const [pages, setPages] = useState([]);
  const [entities, setEntities] = useState([]);
  const [visibility, setVisibility] = useState([]);
  const [competitors, setCompetitors] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");

  const [analyzeUrl, setAnalyzeUrl] = useState("");
  const [competitorUrl, setCompetitorUrl] = useState("");
  const [projectId, setProjectId] = useState("");
  const [lastAnalysis, setLastAnalysis] = useState(null);
  const [revenueImpact, setRevenueImpact] = useState(null);

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, d, s] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/settings`),
      ]);
      setHealth(h.data);
      setDash(d.data);
      setSettings(s.data?.settings || s.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTabData = useCallback(async () => {
    try {
      if (tab === "pages") {
        const r = await API.get(`${API_PREFIX}/pages`, { params: { project_id: projectId, limit: 100 } });
        setPages(r.data?.pages || []);
      } else if (tab === "entities") {
        const r = await API.get(`${API_PREFIX}/entities`, { params: { project_id: projectId, limit: 50 } });
        setEntities(r.data?.entities || []);
      } else if (tab === "visibility") {
        const r = await API.get(`${API_PREFIX}/visibility`, { params: { project_id: projectId, limit: 50 } });
        setVisibility(r.data?.visibility || []);
      } else if (tab === "competitors") {
        const r = await API.get(`${API_PREFIX}/competitors`, { params: { limit: 50 } });
        setCompetitors(r.data?.competitors || []);
      } else if (tab === "opportunities") {
        const r = await API.get(`${API_PREFIX}/opportunities`, { params: { limit: 100 } });
        setOpportunities(r.data?.opportunities || []);
      }
    } catch (e) {
      setError(apiError(e));
    }
  }, [tab, projectId]);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    if (["pages", "entities", "visibility", "competitors", "opportunities"].includes(tab)) {
      loadTabData();
    }
  }, [tab, loadTabData]);

  const handleAnalyzePage = async () => {
    if (!analyzeUrl.trim()) {
      setError("URL gerekli");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post(`${API_PREFIX}/analyze-page`, {
        url: analyzeUrl.trim(),
        project_id: projectId.trim(),
        competitor_url: competitorUrl.trim(),
      });
      setLastAnalysis(res.data);
      setMessage(`Analiz tamam: citation skoru ${res.data?.page?.citation_score ?? "—"}`);
      loadCore();
      if (tab === "pages") loadTabData();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeProject = async () => {
    if (!projectId.trim()) {
      setError("Project ID gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/analyze-project`, { project_id: projectId.trim() });
      setMessage(`Proje analizi: ${res.data?.summary?.pages_analyzed ?? 0} sayfa`);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (reportType = "overview") => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, { report_type: reportType });
      setExportPath(res.data?.path || "");
      setMessage(`Rapor: ${reportType}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/settings`, settings);
      setSettings(res.data?.settings || settings);
      setMessage("Ayarlar kaydedildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadRevenueImpact = async (url, score) => {
    try {
      const r = await API.get(`${API_PREFIX}/pages`);
      const page = (r.data?.pages || []).find((p) => p.url === url);
      setRevenueImpact({
        url,
        citation_score: score ?? page?.citation_score ?? 0,
        note: "Citation ↑ Revenue ↑ — Revenue Lead Engine verisiyle korelasyon",
        lead_count: page?.lead_count,
      });
    } catch {
      setRevenueImpact({ url, citation_score: score, note: "Revenue verisi panelden okunur" });
    }
  };

  useEffect(() => {
    if (tab === "revenue" && lastAnalysis?.page?.url) {
      loadRevenueImpact(lastAnalysis.page.url, lastAnalysis.page.citation_score);
    }
  }, [tab, lastAnalysis]);

  return (
    <HiveShell
      title="Citation Engine"
      subtitle="AI citation uygunluğu, görünürlük ve entity güven analizi — içerik üretmez"
      loading={loading}
    >
      {error && <HiveAlert tone="error">{error}</HiveAlert>}
      <HiveToast message={message} onClose={() => setMessage("")} />

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />
      {loading && !dash && <HiveSkeleton lines={6} />}

      {tab === "dashboard" && (
        <>
          <HiveStatGrid
            items={[
              { label: "Citation Health", value: dash?.citation_health ?? "—", variant: scoreVariant(dash?.citation_health) },
              { label: "Sayfa", value: dash?.pages_count ?? 0 },
              { label: "Citation Ready", value: dash?.citation_ready_count ?? 0 },
              { label: "AI Visibility Ø", value: dash?.ai_visibility_avg ?? "—" },
              { label: "Fırsat", value: dash?.quick_wins ?? 0 },
              { label: "Düşük Skor", value: dash?.low_citation_pages ?? 0 },
            ]}
          />
          <HivePanel title="Sayfa Analizi">
            <HiveField label="URL">
              <HiveInput value={analyzeUrl} onChange={(e) => setAnalyzeUrl(e.target.value)} placeholder="https://example.com/sayfa" />
            </HiveField>
            <HiveField label="Rakip URL (opsiyonel)">
              <HiveInput value={competitorUrl} onChange={(e) => setCompetitorUrl(e.target.value)} placeholder="https://rakip.com/sayfa" />
            </HiveField>
            <HiveField label="Project ID">
              <HiveInput value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="rank-watcher project id" />
            </HiveField>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <HiveBtn onClick={handleAnalyzePage}>Analyze Page</HiveBtn>
              <HiveBtn variant="secondary" onClick={handleAnalyzeProject}>Analyze Project</HiveBtn>
            </div>
          </HivePanel>
          {lastAnalysis?.page && (
            <HivePanel title="Son Analiz">
              <p><strong>{lastAnalysis.page.title}</strong> — skor {lastAnalysis.page.citation_score}</p>
              <p className="sf-dim">Citation ready: {lastAnalysis.page.citation_ready ? "Evet" : "Hayır"}</p>
              {lastAnalysis.page.missing_signals?.length > 0 && (
                <HiveAlert tone="warn">Eksik: {lastAnalysis.page.missing_signals.join(", ")}</HiveAlert>
              )}
            </HivePanel>
          )}
          <HivePanel title="AI Targets">
            <p className="sf-dim">Google AI Overview: heuristic · Diğerleri: provider_missing (sahte veri yok)</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
              {(health?.ai_targets || []).map((t) => (
                <HiveStatusBadge key={t} variant={t === "Google AI Overview" ? "ok" : "neutral"} label={t} />
              ))}
            </div>
          </HivePanel>
        </>
      )}

      {tab === "pages" && (
        <HiveTable
          columns={[
            { key: "title", label: "Başlık" },
            { key: "url", label: "URL" },
            { key: "citation_score", label: "Skor", render: (r) => <HiveStatusBadge variant={scoreVariant(r.citation_score)} label={String(r.citation_score)} /> },
            { key: "citation_ready", label: "Ready", render: (r) => (r.citation_ready ? "✓" : "—") },
            { key: "faq_count", label: "FAQ" },
          ]}
          rows={pages}
          emptyText="Henüz analiz yok — Dashboard'dan sayfa analiz edin"
        />
      )}

      {tab === "entities" && (
        <HiveTable
          columns={[
            { key: "entity", label: "Entity" },
            { key: "entity_strength", label: "Strength" },
            { key: "trust_score", label: "Trust" },
            { key: "support_pages", label: "Support" },
            { key: "project_id", label: "Project" },
          ]}
          rows={entities}
          emptyText="Entity trust verisi yok — proje analizi çalıştırın"
        />
      )}

      {tab === "visibility" && (
        <HiveTable
          columns={[
            { key: "url", label: "URL" },
            { key: "ai_visibility_score", label: "AI Visibility" },
            { key: "overview_probability", label: "Overview %" },
            { key: "citation_probability", label: "Citation %" },
            { key: "trust_probability", label: "Trust %" },
          ]}
          rows={visibility}
          emptyText="Visibility kaydı yok"
        />
      )}

      {tab === "competitors" && (
        <HiveTable
          columns={[
            { key: "our_url", label: "Biz" },
            { key: "competitor_url", label: "Rakip" },
            { key: "citation_gap_score", label: "Gap" },
            { key: "us", label: "Biz Skor", render: (r) => r.us?.citation_score },
            { key: "competitor", label: "Rakip Skor", render: (r) => r.competitor?.citation_score },
          ]}
          rows={competitors}
          emptyText="Rakip gap analizi yok"
        />
      )}

      {tab === "opportunities" && (
        <HiveTable
          columns={[
            { key: "type", label: "Tip" },
            { key: "title", label: "Başlık" },
            { key: "citation_opportunity_score", label: "Opp Skor" },
            { key: "gap", label: "Gap" },
            { key: "quick_win", label: "Quick Win", render: (r) => (r.quick_win ? "✓" : "—") },
          ]}
          rows={opportunities}
          emptyText="Citation fırsatı yok"
        />
      )}

      {tab === "revenue" && (
        <HivePanel title="Citation → Revenue Impact">
          <p className="sf-dim">Citation alan içeriklerin lead etkisi Revenue Lead Engine ile ölçülür.</p>
          {revenueImpact ? (
            <HiveStatGrid
              items={[
                { label: "Citation Score", value: revenueImpact.citation_score },
                { label: "URL", value: (revenueImpact.url || "").slice(0, 40) },
              ]}
            />
          ) : (
            <HiveAlert tone="info">Önce Dashboard'dan bir sayfa analiz edin</HiveAlert>
          )}
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel title="Export">
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {["overview", "pages", "entities", "opportunities", "competitors", "visibility"].map((rt) => (
              <HiveBtn key={rt} variant="secondary" onClick={() => handleExport(rt)}>{rt}</HiveBtn>
            ))}
          </div>
          {exportPath && <p className="sf-dim" style={{ marginTop: "0.75rem" }}>Kayıt: {exportPath}</p>}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel title="Settings">
          <HiveCheck
            label="Enabled"
            checked={!!settings.enabled}
            onChange={(v) => setSettings({ ...settings, enabled: v })}
          />
          <HiveField label="Citation Threshold">
            <HiveInput
              type="number"
              value={settings.citation_threshold}
              onChange={(e) => setSettings({ ...settings, citation_threshold: Number(e.target.value) })}
            />
          </HiveField>
          <HiveField label="Visibility Threshold">
            <HiveInput
              type="number"
              value={settings.visibility_threshold}
              onChange={(e) => setSettings({ ...settings, visibility_threshold: Number(e.target.value) })}
            />
          </HiveField>
          <HiveField label="Trust Threshold">
            <HiveInput
              type="number"
              value={settings.trust_threshold}
              onChange={(e) => setSettings({ ...settings, trust_threshold: Number(e.target.value) })}
            />
          </HiveField>
          <HiveBtn onClick={handleSaveSettings}>Kaydet</HiveBtn>
        </HivePanel>
      )}
    </HiveShell>
  );
}
