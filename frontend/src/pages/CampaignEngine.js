import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
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
  HiveCheck,
  HiveStatusBadge,
} from "../components/HiveModuleUI";
import { HivePanelHero, CampaignWeekTimeline } from "../components/HiveOSVisualizations";

const API_PREFIX = "/api/campaigns";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "dataset_campaign", label: "Dataset Campaign" },
  { id: "campaigns", label: "Campaigns" },
  { id: "blueprint", label: "Blueprint" },
  { id: "tasks", label: "Tasks" },
  { id: "authority", label: "Authority" },
  { id: "citation", label: "Citation" },
  { id: "revenue", label: "Revenue" },
  { id: "progress", label: "Progress" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const GOALS = [
  { value: "ranking", label: "Ranking" },
  { value: "authority", label: "Authority" },
  { value: "citation", label: "Citation" },
  { value: "lead_generation", label: "Lead Generation" },
];

const TYPES = [
  { value: "", label: "Auto (from goal)" },
  { value: "ranking", label: "Ranking Campaign" },
  { value: "authority", label: "Authority Campaign" },
  { value: "citation", label: "Citation Campaign" },
  { value: "lead", label: "Lead Campaign" },
  { value: "local_geo", label: "Local GEO Campaign" },
  { value: "full_domination", label: "Full Domination" },
];

function apiError(e) {
  return e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

function scoreVariant(s) {
  const n = Number(s) || 0;
  if (n >= 75) return "ok";
  if (n >= 50) return "warn";
  return "error";
}

function statusVariant(s) {
  if (s === "active" || s === "completed") return "ok";
  if (s === "planned" || s === "paused") return "warn";
  return "error";
}

export default function CampaignEngine() {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [settings, setSettings] = useState(null);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");

  const [name, setName] = useState("");
  const [keyword, setKeyword] = useState("kuşadası gece hayatı");
  const [domain, setDomain] = useState("");
  const [market, setMarket] = useState("");
  const [goal, setGoal] = useState("ranking");
  const [campaignType, setCampaignType] = useState("");
  const [priority, setPriority] = useState("high");

  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [dsKeyword, setDsKeyword] = useState("kuşadası gece hayatı");
  const [dsDomain, setDsDomain] = useState("https://www.balkutusu.com");
  const [dsMarket, setDsMarket] = useState("kusadasi");
  const [dsCampaignType, setDsCampaignType] = useState("full_domination");

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, d, c, s] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/list`),
        API.get(`${API_PREFIX}/settings`),
      ]);
      setHealth(h.data);
      setDash(d.data);
      setCampaigns(c.data?.campaigns || []);
      setSettings(s.data?.settings || s.data);
      if (!selected && (c.data?.campaigns || []).length) {
        setSelected(c.data.campaigns[0]);
      }
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, [selected]);

  const loadTasks = useCallback(async (campaignId = "") => {
    try {
      const params = { limit: 300 };
      if (campaignId) params.campaign_id = campaignId;
      const r = await API.get(`${API_PREFIX}/tasks`, { params });
      setTasks(r.data?.tasks || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  const loadDatasets = useCallback(async () => {
    try {
      const r = await API.get(`${API_PREFIX}/datasets`);
      const list = r.data?.datasets || [];
      setDatasets(list);
      if (!selectedDatasetId && list.length) {
        setSelectedDatasetId(list[0].dataset_id || list[0].id || "");
      }
    } catch (e) {
      setError(apiError(e));
    }
  }, [selectedDatasetId]);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    if (["dashboard", "tasks", "blueprint", "authority", "citation", "revenue", "progress", "dataset_campaign"].includes(tab)) {
      loadTasks(selected?.campaign_id || "");
    }
    if (tab === "dataset_campaign") {
      loadDatasets();
    }
  }, [tab, selected, loadTasks, loadDatasets]);

  const handleCreate = async () => {
    if (!keyword.trim()) {
      setError("Keyword gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/create`, {
        name: name.trim(),
        target_keyword: keyword.trim(),
        target_domain: domain.trim(),
        target_market: market.trim(),
        goal,
        campaign_type: campaignType,
        priority,
      });
      setMessage(`Kampanya oluşturuldu: ${res.data?.campaign?.campaign_id}`);
      setSelected(res.data?.campaign);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePlan = async (campaignId) => {
    const cid = campaignId || selected?.campaign_id;
    if (!cid) return;
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/generate-plan`, { campaign_id: cid });
      setSelected(res.data?.campaign);
      setTasks(res.data?.tasks || []);
      setMessage(`Plan üretildi: ${res.data?.task_count ?? 0} görev`);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSendOrchestrator = async (campaignId) => {
    const cid = campaignId || selected?.campaign_id;
    if (!cid) return;
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/send-to-orchestrator`, { campaign_id: cid });
      setMessage(`Orchestrator'a gönderildi: ${res.data?.imported ?? 0} görev`);
      loadTasks(cid);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFromDataset = async () => {
    if (!selectedDatasetId) {
      setError("Dataset seçin");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/create-from-dataset`, {
        dataset_id: selectedDatasetId,
        target_domain: dsDomain.trim(),
        campaign_type: dsCampaignType,
        goal: "ranking",
        market: dsMarket.trim(),
        primary_keyword: dsKeyword.trim(),
        priority: "high",
      });
      setSelected(res.data?.campaign);
      setMessage(`Dataset kampanyası: ${res.data?.campaign?.campaign_id}`);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDatasetPlan = async () => {
    const cid = selected?.campaign_id;
    if (!cid) {
      setError("Önce kampanya seçin veya oluşturun");
      return;
    }
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/generate-plan-from-dataset`, { campaign_id: cid });
      setSelected(res.data?.campaign);
      setTasks(res.data?.tasks || []);
      setMessage(`Dataset plan: ${res.data?.task_count ?? 0} görev`);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleAttachDataset = async () => {
    const cid = selected?.campaign_id;
    if (!cid || !selectedDatasetId) {
      setError("Kampanya ve dataset gerekli");
      return;
    }
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/${cid}/attach-dataset`, { dataset_id: selectedDatasetId });
      setSelected(res.data?.campaign);
      setMessage(`Dataset bağlandı: ${selectedDatasetId}`);
      loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSendToAuthorityFactory = async () => {
    const cid = selected?.campaign_id;
    if (!cid) return;
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/send-to-authority-factory`, { campaign_id: cid });
      const batchId = res.data?.batch?.batch_id || res.data?.batch_id || "";
      setMessage(batchId ? `Authority Factory batch: ${batchId}` : "Authority Factory'a gönderildi");
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

  const blueprint = selected?.blueprint?.counts || dash?.default_blueprint || {};
  const weekly = selected?.weekly_blueprint || {};
  const scores = selected?.scores || {};

  const authorityTasks = tasks.filter((t) => t.module === "authority_factory" || t.item_type === "authority_source");
  const citationTasks = tasks.filter((t) => t.module === "citation_engine" || t.item_type?.includes("citation"));
  const revenueTasks = tasks.filter((t) => t.module === "revenue_lead_engine" || t.item_type === "revenue");

  return (
    <div className="hive-module hive-os-command-center">
      <HivePanelHero
        kicker="Campaign OS"
        title="Campaign Engine"
        subtitle="Keyword → blueprint → authority → citation → revenue — uçtan uca kampanya orkestrasyonu"
      />
      <HiveShell title="" subtitle="" loading={loading}>
      {error && <HiveAlert variant="error">{error}</HiveAlert>}
      {message && <HiveAlert variant="ok">{message}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <>
          <div className="hive-viz-grid hive-ops-primary">
            <CampaignWeekTimeline campaigns={campaigns} tasks={tasks} selected={selected} />
          </div>
          <div className="hive-ops-pills" style={{ marginBottom: "1rem" }}>
            <span className="hive-pill hive-pill-success hive-pill-sm">{dash?.active_campaigns ?? 0} active</span>
            <span className="hive-pill hive-pill-accent hive-pill-sm">{dash?.campaigns_total ?? 0} total</span>
            <span className="hive-pill hive-pill-neutral hive-pill-sm">{dash?.tasks_total ?? 0} tasks</span>
            <span className="hive-pill hive-pill-warning hive-pill-sm">{dash?.campaign_progress_avg ?? 0}% avg</span>
          </div>
          <HivePanel title="Yeni Kampanya" style={{ marginTop: 0 }}>
            <HiveField label="Keyword">
              <HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="kuşadası gece hayatı" />
            </HiveField>
            <HiveField label="Kampanya adı">
              <HiveInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Opsiyonel" />
            </HiveField>
            <HiveField label="Domain / Money site">
              <HiveInput value={domain} onChange={(e) => setDomain(e.target.value)} />
            </HiveField>
            <HiveField label="Goal">
              <select value={goal} onChange={(e) => setGoal(e.target.value)} className="hive-input">
                {GOALS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </HiveField>
            <HiveField label="Campaign Type">
              <select value={campaignType} onChange={(e) => setCampaignType(e.target.value)} className="hive-input">
                {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </HiveField>
            <HiveBtn onClick={handleCreate}>Create Campaign</HiveBtn>
          </HivePanel>
          {dash?.executive_alignment?.best_match && (
            <p style={{ marginTop: 12, opacity: 0.8 }}>
              Executive match: {dash.executive_alignment.best_match.name} (score {dash.executive_alignment.best_match.alignment_score})
            </p>
          )}
        </>
      )}

      {tab === "dataset_campaign" && (
        <HivePanel title="Dataset Campaign — Data Miner → Campaign Engine">
          <HiveAlert variant="info">
            Data Miner dataset&apos;inden gerçek entities/FAQs/categories ile kampanya oluşturun.
            Balkutusu Index Recovery kampanyasına dataset attach edilebilir.
          </HiveAlert>
          <HiveField label="Dataset">
            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="hive-input"
            >
              <option value="">— seç —</option>
              {datasets.map((d) => (
                <option key={d.dataset_id || d.id} value={d.dataset_id || d.id}>
                  {(d.dataset_id || d.id)} — {d.source} ({d.entity_count ?? 0} ent / {d.faq_count ?? 0} faq)
                </option>
              ))}
            </select>
          </HiveField>
          <HiveField label="Primary keyword">
            <HiveInput value={dsKeyword} onChange={(e) => setDsKeyword(e.target.value)} />
          </HiveField>
          <HiveField label="Target domain">
            <HiveInput value={dsDomain} onChange={(e) => setDsDomain(e.target.value)} />
          </HiveField>
          <HiveField label="Market">
            <HiveInput value={dsMarket} onChange={(e) => setDsMarket(e.target.value)} placeholder="kusadasi" />
          </HiveField>
          <HiveField label="Campaign type">
            <select value={dsCampaignType} onChange={(e) => setDsCampaignType(e.target.value)} className="hive-input">
              {TYPES.filter((t) => t.value).map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </HiveField>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <HiveBtn onClick={handleCreateFromDataset} disabled={loading}>Create Campaign From Dataset</HiveBtn>
            <HiveBtn variant="secondary" onClick={handleGenerateDatasetPlan} disabled={loading || !selected}>Generate Dataset Plan</HiveBtn>
            <HiveBtn variant="secondary" onClick={handleAttachDataset} disabled={loading || !selected}>Attach Dataset To Selected</HiveBtn>
            <HiveBtn variant="secondary" onClick={handleSendToAuthorityFactory} disabled={loading || !selected}>Send To Authority Factory</HiveBtn>
          </div>
          {selected?.dataset_id && (
            <HiveAlert variant="ok">
              Seçili kampanya dataset: <code>{selected.dataset_id}</code>
              {selected.index_recovery && " — Index Recovery görevleri dahil"}
            </HiveAlert>
          )}
          <HiveTable
            columns={[
              { key: "dataset_id", label: "Dataset ID" },
              { key: "source", label: "Source" },
              { key: "entity_count", label: "Entities" },
              { key: "faq_count", label: "FAQs" },
              { key: "category_count", label: "Categories" },
              { key: "created_at", label: "Created" },
            ]}
            rows={datasets}
            emptyText="Data Miner dataset yok — önce crawl çalıştırın"
          />
        </HivePanel>
      )}

      {tab === "campaigns" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "name", label: "Name" },
              { key: "target_keyword", label: "Keyword" },
              { key: "goal", label: "Goal" },
              { key: "campaign_type", label: "Type" },
              { key: "dataset_id", label: "Dataset", render: (v) => v || "—" },
              { key: "status", label: "Status", render: (v) => <HiveStatusBadge variant={statusVariant(v)}>{v}</HiveStatusBadge> },
              { key: "progress", label: "Progress", render: (v) => `${v ?? 0}%` },
              { key: "score", label: "Score" },
              {
                key: "campaign_id",
                label: "Actions",
                render: (v, row) => (
                  <span style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <HiveBtn variant="secondary" onClick={() => setSelected(row)}>Select</HiveBtn>
                    <HiveBtn variant="secondary" onClick={() => handleGeneratePlan(v)}>Plan</HiveBtn>
                    <HiveBtn variant="secondary" onClick={() => handleSendOrchestrator(v)}>→ Orchestrator</HiveBtn>
                  </span>
                ),
              },
            ]}
            rows={campaigns}
          />
        </HivePanel>
      )}

      {tab === "blueprint" && (
        <HivePanel>
          {selected ? (
            <>
              <p><strong>{selected.name}</strong> — {selected.target_keyword}</p>
              <HiveTable
                columns={[{ key: "type", label: "Content Type" }, { key: "count", label: "Count" }]}
                rows={Object.entries(blueprint).map(([type, count]) => ({ type, count }))}
              />
              <h4 style={{ marginTop: 16 }}>Weekly Blueprint</h4>
              {Object.entries(weekly).map(([week, data]) => (
                <div key={week} style={{ marginBottom: 12 }}>
                  <strong>{week}</strong> — {data.phase}
                  <pre style={{ fontSize: 12, opacity: 0.85 }}>{JSON.stringify(data.items || {}, null, 2)}</pre>
                </div>
              ))}
              <HiveBtn onClick={() => handleGeneratePlan()} style={{ marginTop: 8 }}>Regenerate Plan</HiveBtn>
            </>
          ) : (
            <p>Kampanya seçin veya oluşturun.</p>
          )}
        </HivePanel>
      )}

      {tab === "tasks" && (
        <HivePanel>
          <div style={{ marginBottom: 12 }}>
            <HiveBtn variant="secondary" onClick={() => handleSendOrchestrator()} disabled={!selected}>
              Send To Orchestrator
            </HiveBtn>
          </div>
          <HiveTable
            columns={[
              { key: "week", label: "Week" },
              { key: "item_type", label: "Type" },
              { key: "module", label: "Module" },
              { key: "action_type", label: "Action" },
              { key: "priority", label: "Priority" },
              { key: "status", label: "Status", render: (v) => <HiveStatusBadge variant={statusVariant(v)}>{v}</HiveStatusBadge> },
              { key: "estimated_impact", label: "Impact" },
              { key: "title", label: "Title" },
            ]}
            rows={tasks}
          />
        </HivePanel>
      )}

      {tab === "authority" && (
        <HivePanel>
          <HiveTable columns={[
            { key: "title", label: "Task" }, { key: "status", label: "Status" }, { key: "estimated_impact", label: "Impact" },
          ]} rows={authorityTasks.length ? authorityTasks : tasks.filter((t) => t.module?.includes("authority"))} />
          {selected && (
            <HiveBtn style={{ marginTop: 12 }} onClick={async () => {
              try {
                const res = await API.post("/api/campaigns/generate-plan", { campaign_id: selected.campaign_id });
                setMessage("Authority batch — plan içinde authority_factory görevleri üretildi");
              } catch (e) { setError(apiError(e)); }
            }}>Refresh Authority Tasks</HiveBtn>
          )}
        </HivePanel>
      )}

      {tab === "citation" && (
        <HivePanel>
          <HiveTable columns={[
            { key: "title", label: "Task" }, { key: "module", label: "Module" }, { key: "status", label: "Status" },
          ]} rows={citationTasks} />
        </HivePanel>
      )}

      {tab === "revenue" && (
        <HivePanel>
          <HiveTable columns={[
            { key: "title", label: "Task" }, { key: "estimated_impact", label: "Impact" }, { key: "status", label: "Status" },
          ]} rows={revenueTasks} />
        </HivePanel>
      )}

      {tab === "progress" && selected && (
        <HivePanel>
          <div className="hive-viz-grid">
            <CampaignWeekTimeline campaigns={campaigns} tasks={tasks} selected={selected} />
          </div>
          <HiveStatGrid
            items={[
              { label: "Overall", value: scores.overall ?? selected.score ?? 0, variant: scoreVariant(scores.overall) },
              { label: "Ranking", value: scores.ranking ?? "—", variant: scoreVariant(scores.ranking) },
              { label: "Authority", value: scores.authority ?? "—", variant: scoreVariant(scores.authority) },
              { label: "Citation", value: scores.citation ?? "—", variant: scoreVariant(scores.citation) },
              { label: "Revenue", value: scores.revenue ?? "—", variant: scoreVariant(scores.revenue) },
              { label: "Execution", value: scores.execution ?? "—", variant: scoreVariant(scores.execution) },
              { label: "Risk", value: scores.risk ?? "—", variant: scoreVariant(100 - (scores.risk || 0)) },
              { label: "Progress", value: `${selected.progress ?? 0}%`, variant: scoreVariant(selected.progress) },
            ]}
          />
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <HiveBtn onClick={() => handleExport("overview")}>Overview</HiveBtn>
            <HiveBtn variant="secondary" onClick={() => handleExport("campaigns")}>Campaigns</HiveBtn>
            <HiveBtn variant="secondary" onClick={() => handleExport("tasks")}>Tasks</HiveBtn>
          </div>
          {exportPath && <p style={{ marginTop: 12 }}>Kayıt: {exportPath}</p>}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel>
          <HiveField label="Modül aktif">
            <HiveCheck checked={!!settings.enabled} onChange={(v) => setSettings({ ...settings, enabled: v })} label="Campaign Engine etkin" />
          </HiveField>
          <HiveField label="Commercial intent boost">
            <HiveCheck checked={!!settings.commercial_intent_boost} onChange={(v) => setSettings({ ...settings, commercial_intent_boost: v })} label="Revenue yüksek intent önceliği" />
          </HiveField>
          <HiveField label="Citation gap threshold">
            <HiveInput type="number" value={settings.citation_gap_threshold ?? 15} onChange={(e) => setSettings({ ...settings, citation_gap_threshold: Number(e.target.value) })} />
          </HiveField>
          <HiveBtn onClick={handleSaveSettings} style={{ marginTop: 16 }}>Kaydet</HiveBtn>
        </HivePanel>
      )}

      {health && (
        <p style={{ marginTop: 16, fontSize: 12, opacity: 0.6 }}>
          Module: {health.module} · Active: {health.active_campaigns} · Publishes: {health.publishes ? "yes" : "no"}
        </p>
      )}
    </HiveShell>
    </div>
  );
}
