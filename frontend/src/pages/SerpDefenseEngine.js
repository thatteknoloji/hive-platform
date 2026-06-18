import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveBtn,
  HiveTable,
  HiveCard,
  HiveField,
  HiveInput,
  HiveCheck,
  HiveCode,
  HiveBadge,
  HiveMissionBoard,
  HiveContextBar,
  HiveSection,
  HiveConceptTooltip,
} from "../components/HiveModuleUI";
import { HIVE_CONCEPTS } from "../config/hiveConcepts";
import { HivePanelHero, KeywordWarRoom } from "../components/HiveOSVisualizations";

const API_PREFIX = "/api/serp-defense";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "fortress", label: "Fortress" },
  { id: "attack_surface", label: "Attack Surface" },
  { id: "ctr", label: "CTR" },
  { id: "ai_overview", label: "AI Overview" },
  { id: "entities", label: "Entities" },
  { id: "faqs", label: "FAQs" },
  { id: "pressure", label: "Pressure" },
  { id: "defense_plan", label: "Defense Plan" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const REPORT_TYPES = [
  { id: "fortress", label: "Fortress Report" },
  { id: "attack_surface", label: "Attack Surface Report" },
  { id: "keyword_risk", label: "Keyword Risk Report" },
  { id: "ctr", label: "CTR Defense Report" },
  { id: "ai_overview", label: "AI Overview Defense Report" },
  { id: "entity", label: "Entity Defense Report" },
  { id: "faq", label: "FAQ Defense Report" },
  { id: "pressure", label: "Competitor Pressure Report" },
  { id: "defense_plan", label: "Defense Plan Report" },
  { id: "opportunities", label: "Defense Opportunities Report" },
  { id: "overview", label: "Overview" },
];

function apiError(e) {
  return e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

function pressureBadge(level) {
  const map = { LOW: "ok", MEDIUM: "warn", HIGH: "danger", CRITICAL: "danger" };
  return <HiveBadge tone={map[level] || "muted"}>{level || "—"}</HiveBadge>;
}

export default function SerpDefenseEngine({ preselectedProjectId = "" }) {
  const [tab, setTab] = useState("dashboard");
  const [projectId, setProjectId] = useState(
    preselectedProjectId || sessionStorage.getItem("serp_defense_project_id") || ""
  );
  const [keyword, setKeyword] = useState("");
  const [health, setHealth] = useState(null);
  const [settings, setSettings] = useState(null);
  const [dash, setDash] = useState(null);
  const [fortresses, setFortresses] = useState([]);
  const [attackSurfaces, setAttackSurfaces] = useState([]);
  const [pressure, setPressure] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [plan, setPlan] = useState(null);
  const [execution, setExecution] = useState(null);
  const [liveRefresh, setLiveRefresh] = useState(null);
  const [lastReport, setLastReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");

  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";

  const refresh = useCallback(async () => {
    try {
      const [h, s, d, f, a, p, o] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/dashboard${q}`).catch(() => ({ data: null })),
        API.get(`${API_PREFIX}/fortress${q}`).catch(() => ({ data: { fortresses: [] } })),
        API.get(`${API_PREFIX}/attack-surface${q}`).catch(() => ({ data: { attack_surfaces: [] } })),
        API.get(`${API_PREFIX}/pressure${q}`).catch(() => ({ data: null })),
        API.get(`${API_PREFIX}/opportunities${q}`).catch(() => ({ data: { opportunities: [] } })),
      ]);
      setHealth(h.data);
      setSettings(s.data.settings || s.data);
      setDash(d.data);
      setFortresses(f.data.fortresses || []);
      setAttackSurfaces(a.data.attack_surfaces || []);
      setPressure(p.data);
      setOpportunities(o.data.opportunities || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, [q]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (projectId) sessionStorage.setItem("serp_defense_project_id", projectId);
  }, [projectId]);

  const analyzeKeyword = async () => {
    if (!keyword.trim()) {
      setError("Keyword gerekli");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post(`${API_PREFIX}/analyze-keyword`, {
        keyword: keyword.trim(),
        project_id: projectId || undefined,
      });
      setLastReport(res.data.report);
      setMessage(`"${keyword}" analiz edildi — fortress: ${res.data.report?.fortress_score}`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const analyzeProject = async () => {
    if (!projectId) {
      setError("Proje ID gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/analyze-project`, { project_id: projectId });
      setMessage(`Proje analizi tamamlandı — ${res.data.count} keyword`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const generatePlan = async () => {
    setLoading(true);
    setError("");
    try {
      const body = keyword.trim()
        ? { keyword: keyword.trim(), project_id: projectId || undefined }
        : { project_id: projectId || undefined };
      const res = await API.post(`${API_PREFIX}/generate-plan`, body);
      setPlan(res.data.plan);
      setExecution(null);
      setMessage(res.data.plan?.one_click_defense?.auto_apply
        ? "Savunma planı oluşturuldu — «Planı Uygula» ile çalıştırabilirsiniz"
        : "Savunma planı oluşturuldu (otomatik uygulama kapalı)");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const executePlan = async () => {
    if (!plan?.plan_id && !projectId) {
      setError("Önce plan oluşturun veya proje ID girin");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const body = {
        plan_id: plan?.plan_id || undefined,
        keyword: keyword.trim() || plan?.keyword || undefined,
        project_id: projectId || plan?.project_id || undefined,
      };
      const res = await API.post(`${API_PREFIX}/execute-plan`, body);
      setExecution(res.data.execution);
      setPlan(res.data.plan || plan);
      const ex = res.data.execution;
      setMessage(`Plan uygulandı — ${ex?.status} (${ex?.success_count}/${(ex?.steps || []).length} adım)`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const refreshLiveData = async (opts = {}) => {
    if (!projectId) {
      setError("Canlı veri için proje ID gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/refresh-live-data`, {
        project_id: projectId,
        keyword: keyword.trim() || undefined,
        refresh_gsc: opts.refresh_gsc !== false,
        refresh_rank: opts.refresh_rank !== false,
        refresh_ai: !!opts.refresh_ai,
      });
      setLiveRefresh(res.data);
      const lr = res.data.live_refresh || {};
      const parts = [];
      if (lr.gsc?.success) parts.push("GSC");
      if (lr.rank?.success) parts.push("Rank");
      if (lr.ai_overview?.success) parts.push("AI Overview");
      setMessage(parts.length ? `Canlı veri yenilendi: ${parts.join(", ")}` : "Canlı yenileme tamamlandı (bazı sağlayıcılar yapılandırılmamış olabilir)");
      if (keyword.trim()) {
        const anal = await API.post(`${API_PREFIX}/analyze-keyword`, {
          keyword: keyword.trim(),
          project_id: projectId,
        });
        setLastReport(anal.data.report);
      }
      await refresh();
    } catch (e) {
      setError(apiError(e));
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
      if (keyword.trim()) params.set("keyword", keyword.trim());
      const res = await API.post(`${API_PREFIX}/export-report?${params}`);
      setExportPath(res.data.path || "");
      setMessage(`${reportType} raporu dışa aktarıldı`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async (patch) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/settings`, patch);
      setSettings(res.data.settings || res.data);
      setMessage("Ayarlar kaydedildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const integrationErrors = health?.integration_errors || [];
  const gscOk = health?.providers?.search_console ?? health?.integrations?.search_console?.ok;
  const dfsOk = health?.providers?.dataforseo ?? health?.integrations?.dataforseo_ai_overview?.ok;
  const selectedFortress = fortresses.find(
    (f) => f.keyword?.toLowerCase() === keyword.trim().toLowerCase()
  ) || fortresses[0];

  return (
    <div className="hive-module hive-os-command-center">
      <HivePanelHero
        kicker="SERP Defense OS"
        title="SERP Defense Engine"
        subtitle="Keyword fortress — baskı tespiti, risk haritası ve savunma planı"
      />
    <HiveShell title="" subtitle="">
      {message && <HiveAlert tone="ok" onClose={() => setMessage("")}>{message}</HiveAlert>}
      {error && <HiveAlert tone="danger" onClose={() => setError("")}>{error}</HiveAlert>}

      <HiveContextBar>
        <HiveField label="Proje ID">
          <HiveInput value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="proj-balkutusu" />
        </HiveField>
        <HiveField label="Keyword">
          <HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="kuşadası gece hayatı" />
        </HiveField>
        <HiveBtn onClick={analyzeKeyword} disabled={loading}>Analiz Et</HiveBtn>
        <HiveBtn onClick={analyzeProject} disabled={loading || !projectId} variant="outline">Projeyi Analiz Et</HiveBtn>
        <HiveBtn onClick={refresh} disabled={loading} variant="ghost">Yenile</HiveBtn>
      </HiveContextBar>

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <>
          <div className="hive-viz-grid">
            <KeywordWarRoom
              keywords={fortresses.length ? fortresses : (dash?.top_risks || [])}
            />
          </div>
        <HivePanel title="Fortress Overview" description="Savunma baskısı ve keyword risk özeti">
          <p className="hm-label-tip hm-panel-tip">
            Fortress Score
            <HiveConceptTooltip conceptKey="fortress_score" concepts={HIVE_CONCEPTS} />
          </p>
          {(dash?.critical_pressure_count || 0) > 0 && (
            <HiveAlert type="error" pulse>
              {dash.critical_pressure_count} keyword CRITICAL baskı altında — savunma planı önerilir.
            </HiveAlert>
          )}
          <HiveMissionBoard
            primary={[
              { label: "Avg Fortress", value: dash?.avg_fortress_score ?? "—", tone: "accent" },
              { label: "Critical Pressure", value: dash?.critical_pressure_count ?? 0, tone: (dash?.critical_pressure_count || 0) > 0 ? "danger" : "ok" },
              { label: "Keywords", value: dash?.keyword_count ?? 0 },
            ]}
            secondary={[
              { label: "Plans", value: health?.plans_count ?? 0 },
              { label: "GSC", value: gscOk ? "Connected" : "Off" },
              { label: "DataForSEO", value: dfsOk ? "Connected" : "Off" },
              { label: "Executions", value: health?.execution_count ?? 0 },
            ]}
          />
          {integrationErrors.length > 0 && (
            <HiveAlert type="warn">
              Entegrasyon uyarıları: {integrationErrors.map((e) => e.module).join(", ")}
            </HiveAlert>
          )}
          <HiveSection title="Highest Risk Keywords">
            <HiveTable
              columns={["Keyword", "Fortress", "Baskı", "Durum", "Strateji"]}
              rows={(dash?.top_risks || []).map((r) => [
                r.keyword,
                r.fortress_score,
                r.pressure_score,
                pressureBadge(r.pressure_level),
                r.strategy_recommendation?.decision || "—",
              ])}
              emptyText="Henüz analiz yok — keyword analiz edin"
            />
          </HiveSection>
          {opportunities.length > 0 && (
            <HiveSection title="Defense vs Growth">
              <HiveTable
                columns={["Keyword", "Karar", "Gerekçe", "Fortress"]}
                rows={opportunities.slice(0, 10).map((o) => [
                  o.keyword,
                  o.strategy_decision || "defend",
                  (o.strategy_reason || "").slice(0, 60),
                  o.fortress_score,
                ])}
              />
            </HiveSection>
          )}
        </HivePanel>
        </>
      )}

      {tab === "fortress" && (
        <HivePanel title="Keyword Fortress">
          <HiveTable
            columns={["Keyword", "Pozisyon", "Fortress", "Attack Surface", "Baskı", "AI", "Entity", "FAQ", "Freshness"]}
            rows={fortresses.map((r) => [
              r.keyword,
              r.position ?? "—",
              r.fortress_score,
              r.attack_surface_score,
              pressureBadge(r.pressure_level),
              r.ai_visibility ?? r.components?.ai_visibility_score ?? "—",
              r.entity_strength ?? r.components?.entity_score ?? "—",
              r.faq_strength ?? r.components?.faq_score ?? "—",
              r.freshness ?? r.components?.freshness_score ?? "—",
            ])}
            empty="Fortress verisi yok"
          />
        </HivePanel>
      )}

      {tab === "attack_surface" && (
        <HivePanel title="SERP Attack Surface">
          {attackSurfaces.length === 0 ? (
            <p>Attack surface verisi yok.</p>
          ) : (
            attackSurfaces.map((as, i) => (
              <HiveCard key={i} title={as.keyword || fortresses[i]?.keyword || `Surface ${i + 1}`}>
                <HiveStatGrid stats={[
                  ["Skor", as.attack_surface_score ?? "—"],
                  ["Gap Sayısı", as.gap_count ?? "—"],
                  ["Eksikler", (as.gaps || []).length],
                ]} />
                {as.gaps?.length > 0 && (
                  <p><strong>Eksik yüzeyler:</strong> {as.gaps.join(", ")}</p>
                )}
                <HiveCode value={JSON.stringify(as.missing || as, null, 2)} />
              </HiveCard>
            ))
          )}
        </HivePanel>
      )}

      {tab === "ctr" && (
        <HivePanel title="CTR Defense (Canlı GSC)">
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <HiveBtn onClick={() => refreshLiveData({ refresh_ai: false })} disabled={loading || !projectId}>
              GSC Canlı Yenile
            </HiveBtn>
            {!gscOk && (
              <HiveAlert tone="warn">Search Console OAuth yapılandırılmadı — CTR canlı analiz devre dışı</HiveAlert>
            )}
          </div>
          {liveRefresh?.live_refresh?.gsc && (
            <HiveCard title="Son GSC Sync">
              <HiveCode value={JSON.stringify(liveRefresh.live_refresh.gsc, null, 2)} />
            </HiveCard>
          )}
          {selectedFortress?.ctr_analysis ? (
            <>
              {selectedFortress.ctr_analysis.success === false ? (
                <HiveAlert tone="warn">
                  {selectedFortress.ctr_analysis.error}: {selectedFortress.ctr_analysis.message || "GSC yapılandırılmadı"}
                </HiveAlert>
              ) : (
                <>
                  <HiveStatGrid stats={[
                    ["CTR", selectedFortress.ctr_analysis.ctr != null ? `${(selectedFortress.ctr_analysis.ctr * 100).toFixed(2)}%` : "—"],
                    ["Impressions", selectedFortress.ctr_analysis.impressions ?? "—"],
                    ["Clicks", selectedFortress.ctr_analysis.clicks ?? "—"],
                    ["Pozisyon", selectedFortress.ctr_analysis.position ?? "—"],
                  ]} />
                  <HiveStatGrid stats={[
                    ["Başlık Problemi", selectedFortress.ctr_analysis.title_problem ? "Evet" : "Hayır"],
                    ["Snippet Problemi", selectedFortress.ctr_analysis.snippet_problem ? "Evet" : "Hayır"],
                    ["AI Overview Etkisi", selectedFortress.ctr_analysis.ai_overview_impact ? "Olası" : "Hayır"],
                    ["Impression Kaybı", selectedFortress.ctr_analysis.impression_loss ? "Evet" : "Hayır"],
                  ]} />
                  {(selectedFortress.ctr_analysis.issues || []).length > 0 && (
                    <HiveAlert tone="warn">
                      Sorunlar: {selectedFortress.ctr_analysis.issues.join(", ")}
                    </HiveAlert>
                  )}
                </>
              )}
            </>
          ) : (
            <p>CTR verisi için keyword analizi gerekli (GSC OAuth).</p>
          )}
        </HivePanel>
      )}

      {tab === "ai_overview" && (
        <HivePanel title="AI Overview Defense (DataForSEO)">
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <HiveBtn
              onClick={() => refreshLiveData({ refresh_gsc: false, refresh_rank: true, refresh_ai: true })}
              disabled={loading || !projectId || !keyword.trim()}
            >
              AI Overview Canlı Yenile
            </HiveBtn>
            {!dfsOk && (
              <HiveAlert tone="warn">DataForSEO yapılandırılmadı — AI Overview canlı analiz devre dışı</HiveAlert>
            )}
          </div>
          {selectedFortress ? (
            <>
              <HiveStatGrid stats={[
                ["AI Overview", selectedFortress.ai_overview?.ai_overview_present ? "Var" : "Yok"],
                ["Görünürlük", selectedFortress.ai_overview?.ai_visibility_score ?? "—"],
                ["Rakip", selectedFortress.ai_overview?.ai_competitor_count ?? "—"],
                ["Answer Block", selectedFortress.ai_overview?.answer_block_score ?? "—"],
                ["Citation", selectedFortress.ai_overview?.citation_strength ?? "—"],
              ]} />
              {selectedFortress.ai_overview?.success === false && (
                <HiveAlert tone="warn">
                  {selectedFortress.ai_overview.error}: {selectedFortress.ai_overview.message || "Provider eksik"}
                </HiveAlert>
              )}
            </>
          ) : (
            <p>Keyword analiz edin veya fortress listesini doldurun.</p>
          )}
        </HivePanel>
      )}

      {tab === "entities" && (
        <HivePanel title="Entity Defense">
          {selectedFortress?.entity_defense ? (
            <>
              <HiveStatGrid stats={[
                ["Entity Gücü", selectedFortress.entity_defense.entity_strength ?? "—"],
                ["GEO Skor", selectedFortress.entity_defense.geo_score ?? "—"],
                ["Eksik", (selectedFortress.entity_defense.missing_entities || []).length],
              ]} />
              <HiveTable
                columns={["Entity", "Durum"]}
                rows={(selectedFortress.entity_defense.missing_entities || []).slice(0, 20).map((e) => [
                  e.entity || e.label || JSON.stringify(e),
                  "eksik",
                ])}
                empty="Eksik entity yok"
              />
              {(selectedFortress.entity_defense.competitor_entities || []).length > 0 && (
                <>
                  <h4>Rakip SERP Entity</h4>
                  <HiveTable
                    columns={["Entity", "Pozisyon", "URL"]}
                    rows={selectedFortress.entity_defense.competitor_entities.slice(0, 10).map((e) => [
                      e.entity,
                      e.position ?? "—",
                      (e.url || "").slice(0, 50),
                    ])}
                  />
                </>
              )}
            </>
          ) : (
            <p>Entity verisi için keyword analizi gerekli.</p>
          )}
        </HivePanel>
      )}

      {tab === "faqs" && (
        <HivePanel title="FAQ Defense">
          {selectedFortress?.faq_defense ? (
            <>
              <HiveStatGrid stats={[
                ["FAQ Skor", selectedFortress.faq_defense.faq_strength ?? selectedFortress.components?.faq_score ?? "—"],
                ["Eksik PAA", (selectedFortress.faq_defense.missing_paa || []).length],
                ["Eksik FAQ", (selectedFortress.faq_defense.missing_faq || []).length],
                ["Eksik Objection", (selectedFortress.faq_defense.missing_objection || []).length],
              ]} />
              <HiveCode value={JSON.stringify(selectedFortress.faq_defense.gaps || selectedFortress.faq_defense, null, 2)} />
            </>
          ) : (
            <p>FAQ verisi için keyword analizi gerekli.</p>
          )}
        </HivePanel>
      )}

      {tab === "pressure" && (
        <HivePanel title="Competitor Pressure">
          {pressure?.by_level ? (
            Object.entries(pressure.by_level).map(([level, items]) => (
              items.length > 0 && (
                <HiveCard key={level} title={`${level} (${items.length})`}>
                  <HiveTable
                    columns={["Keyword", "Baskı Skoru", "Fortress"]}
                    rows={items.map((i) => [i.keyword, i.pressure_score, i.fortress_score])}
                  />
                </HiveCard>
              )
            ))
          ) : (
            <p>Baskı verisi yok.</p>
          )}
        </HivePanel>
      )}

      {tab === "defense_plan" && (
        <HivePanel title="Defense Plan & Uygulama">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            <HiveBtn onClick={generatePlan} disabled={loading}>
              Plan Oluştur
            </HiveBtn>
            <HiveBtn
              onClick={executePlan}
              disabled={loading || !plan?.one_click_defense?.auto_apply || (!plan && !projectId)}
              variant="secondary"
            >
              Planı Uygula
            </HiveBtn>
          </div>
          {plan && (
            <>
              <HiveAlert tone="info">{plan.one_click_defense?.note}</HiveAlert>
              <HiveStatGrid stats={[
                ["Sayfa Güncelleme", plan.one_click_defense?.pages_to_update ?? 0],
                ["Refresh", plan.one_click_defense?.refreshes_needed ?? 0],
                ["Yayın", plan.one_click_defense?.publishes_planned ?? 0],
                ["Entity", plan.one_click_defense?.entities_to_add ?? 0],
                ["GEO", plan.one_click_defense?.geo_sections_to_add ?? 0],
                ["FAQ", plan.one_click_defense?.faqs_to_add ?? 0],
                ["Support Sayfa", plan.one_click_defense?.support_pages_needed ?? 0],
                ["Comparison", plan.one_click_defense?.comparisons_to_add ?? 0],
                ["Cluster", plan.one_click_defense?.cluster_expansions ?? 0],
                ["Tahmini Kalite", plan.estimated_quality_score ?? "—"],
              ]} />
              {selectedFortress?.support_network && (
                <>
                  <h4>Support Network</h4>
                  <p><strong>Destekleyen:</strong> {(selectedFortress.support_network.supporting_domains || []).join(", ") || "—"}</p>
                  <p><strong>Güçlendirilmeli:</strong> {(selectedFortress.support_network.strengthen_domains || []).join(", ") || "—"}</p>
                  <p><strong>Desteklemiyor:</strong> {(selectedFortress.support_network.not_contributing || []).slice(0, 5).join(", ") || "—"}</p>
                </>
              )}
              <p><strong>Modüller:</strong> {(plan.one_click_defense?.modules_to_run || []).join(", ") || "—"}</p>
              <HiveTable
                columns={["Aksiyon", "Keyword", "Öncelik", "Uygulama"]}
                rows={(plan.actions || []).map((a) => [
                  a.action,
                  a.keyword,
                  a.priority || "—",
                  a.apply || "plan_only",
                ])}
                empty="Aksiyon yok"
              />
            </>
          )}
          {execution && (
            <>
              <h4>Son Uygulama — {execution.status}</h4>
              <HiveStatGrid stats={[
                ["Başarılı", execution.success_count ?? 0],
                ["Başarısız", execution.fail_count ?? 0],
                ["Zaman", execution.executed_at ?? "—"],
              ]} />
              <HiveTable
                columns={["Aksiyon", "Modül", "Durum", "Detay"]}
                rows={(execution.steps || []).map((s) => [
                  s.action,
                  s.module || "—",
                  s.success ? "OK" : (s.skipped ? "Atlandı" : "Hata"),
                  s.error || s.note || (s.publish?.count != null ? `${s.publish.count} yayın` : "—"),
                ])}
                empty="Uygulama adımı yok"
              />
            </>
          )}
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
          {lastReport && (
            <HiveCard title="Son Analiz">
              <HiveCode value={JSON.stringify(lastReport, null, 2)} />
            </HiveCard>
          )}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel title="Ayarlar">
          <HiveCheck
            label="SERP Defense aktif"
            checked={!!settings.enabled}
            onChange={(v) => saveSettings({ enabled: v })}
          />
          <HiveCheck
            label="Otomatik plan uygulama (execute-plan)"
            checked={!!settings.auto_apply_enabled}
            onChange={(v) => saveSettings({ auto_apply_enabled: v })}
          />
          <HiveCheck
            label="Uygulamada otomatik yayın (Publisher)"
            checked={!!settings.auto_publish_on_execute}
            onChange={(v) => saveSettings({ auto_publish_on_execute: v })}
          />
          <HiveCheck
            label="Analiz sırasında canlı GSC/Rank yenile"
            checked={settings.live_refresh_on_analyze !== false}
            onChange={(v) => saveSettings({ live_refresh_on_analyze: v })}
          />
          <HiveField label="Fortress uyarı eşiği">
            <HiveInput
              type="number"
              value={settings.fortress_warning_threshold ?? 55}
              onChange={(e) => saveSettings({ fortress_warning_threshold: Number(e.target.value) })}
            />
          </HiveField>
          <HiveField label="Fortress kritik eşiği">
            <HiveInput
              type="number"
              value={settings.fortress_critical_threshold ?? 40}
              onChange={(e) => saveSettings({ fortress_critical_threshold: Number(e.target.value) })}
            />
          </HiveField>
        </HivePanel>
      )}
    </HiveShell>
    </div>
  );
}
