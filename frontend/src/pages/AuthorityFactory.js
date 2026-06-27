import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";

import {
  HiveAlert,
  HiveBtn,
  HiveCheck,
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

const API_PREFIX = "/api/authority-factory";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "create_campaign", label: "Create From Campaign" },
  { id: "create_dataset", label: "Create From Dataset" },
  { id: "domain_candidates", label: "Domain Candidates" },
  { id: "provider_mix", label: "Provider Mix" },
  { id: "create", label: "Create Batch" },
  { id: "batches", label: "Batches" },
  { id: "items", label: "Items" },
  { id: "processing", label: "Processing" },
  { id: "published", label: "Published" },
  { id: "failed", label: "Failed" },
  { id: "login_required", label: "Login Required" },
  { id: "providers", label: "Provider Status" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

function statusVariant(s) {
  if (s === "published" || s === "completed") return "ok";
  if (s === "failed" || s === "provider_missing") return "error";
  if (s === "login_required" || s === "review_required") return "warn";
  if (s === "processing") return "active";
  return "neutral";
}

export default function AuthorityFactory() {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [settings, setSettings] = useState(null);
  const [batches, setBatches] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");

  const [keyword, setKeyword] = useState("");
  const [moneySite, setMoneySite] = useProjectSiteField();
  const [batchName, setBatchName] = useState("");
  const [source, setSource] = useState("manual");
  const [autoProcess, setAutoProcess] = useState(false);
  const [lastBatch, setLastBatch] = useState(null);
  const [campaignId, setCampaignId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [datasets, setDatasets] = useState([]);
  const [domainCandidates, setDomainCandidates] = useState([]);
  const [providerMix, setProviderMix] = useState(null);
  const [preview, setPreview] = useState(null);

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, d, s, b] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/batches`, { params: { limit: 50 } }),
      ]);
      setHealth(h.data);
      setDash(d.data);
      setSettings(s.data?.settings || s.data);
      setBatches(b.data?.batches || []);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadItems = useCallback(async (status = "") => {
    try {
      const res = await API.get(`${API_PREFIX}/items`, { params: { status, limit: 100 } });
      setItems(res.data?.items || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    if (["processing", "published", "failed", "login_required", "items"].includes(tab)) {
      const statusMap = {
        processing: "processing",
        published: "published",
        failed: "failed",
        login_required: "login_required",
        items: "",
      };
      loadItems(statusMap[tab] || "");
    }
    if (tab === "create_dataset") {
      API.get(`${API_PREFIX}/datasets`).then((r) => setDatasets(r.data?.datasets || [])).catch(() => {});
    }
    if (tab === "domain_candidates") {
      API.get(`${API_PREFIX}/domain-candidates`).then((r) => setDomainCandidates(r.data?.candidates || [])).catch(() => {});
    }
    if (tab === "provider_mix") {
      API.get(`${API_PREFIX}/provider-mix`).then((r) => setProviderMix(r.data?.provider_mix || null)).catch(() => {});
    }
  }, [tab, loadItems]);

  const handleCreateFromCampaign = async () => {
    if (!campaignId.trim()) { setError("Campaign ID gerekli"); return; }
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/create-from-campaign`, { campaign_id: campaignId.trim() });
      setMessage(`V2 batch: ${res.data?.batch?.batch_id}`);
      await loadCore();
      setTab("batches");
    } catch (e) { setError(apiError(e)); } finally { setLoading(false); }
  };

  const handleCreateFromDataset = async () => {
    if (!datasetId.trim()) { setError("Dataset ID gerekli"); return; }
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/create-from-dataset`, { dataset_id: datasetId.trim(), keyword: keyword.trim(), money_site: moneySite.trim() });
      setMessage(`Dataset batch: ${res.data?.batch?.batch_id}`);
      await loadCore();
      setTab("batches");
    } catch (e) { setError(apiError(e)); } finally { setLoading(false); }
  };

  const handleCreateFromDomains = async () => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/create-from-domain-candidates`, { keyword: keyword.trim(), money_site: moneySite.trim() });
      setMessage(`Domain batch: ${res.data?.batch?.batch_id}`);
      await loadCore();
      setTab("batches");
    } catch (e) { setError(apiError(e)); } finally { setLoading(false); }
  };

  const handleCreateBatch = async () => {
    if (!keyword.trim()) {
      setError("Keyword gerekli");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post(`${API_PREFIX}/create-batch`, {
        keyword: keyword.trim(),
        money_site: moneySite.trim(),
        name: batchName.trim(),
        source,
        auto_process: autoProcess,
      });
      setLastBatch(res.data?.batch);
      setMessage(`Batch oluşturuldu: ${res.data?.batch?.batch_id}${res.data?.auto_processed ? " (işlendi)" : ""}`);
      if (res.data?.warnings?.length) {
        setMessage((m) => `${m} — Uyarılar: ${res.data.warnings.join(", ")}`);
      }
      await loadCore();
      setTab("batches");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = async (batchId) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/process-batch/${batchId}`);
      setMessage(`Batch işlendi: ${batchId} — published ${res.data?.summary?.published ?? 0}`);
      await loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async (batchId) => {
    try {
      await API.post(`${API_PREFIX}/pause-batch/${batchId}`);
      setMessage(`Batch duraklatıldı: ${batchId}`);
      await loadCore();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const handleResume = async (batchId) => {
    try {
      await API.post(`${API_PREFIX}/resume-batch/${batchId}`);
      setMessage(`Batch devam ediyor: ${batchId}`);
      await loadCore();
    } catch (e) {
      setError(apiError(e));
    }
  };

  const handleSaveSettings = async () => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/settings`, settings);
      setSettings(res.data?.settings);
      setMessage("Ayarlar kaydedildi");
      await loadCore();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (reportType = "overview") => {
    try {
      const res = await API.post(`${API_PREFIX}/export-report`, { report_type: reportType });
      setExportPath(res.data?.path || "");
      setMessage(`Rapor: ${reportType}`);
    } catch (e) {
      setError(apiError(e));
    }
  };

  const handlePreviewContent = async (itemId) => {
    if (!itemId) return;
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/preview-content`, { item_id: itemId, format: "html" });
      setPreview(res.data || null);
      setMessage(`Preview hazır: ${itemId}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const batchColumns = [
    { key: "batch_id", label: "Batch ID" },
    { key: "name", label: "Ad" },
    { key: "target_keyword", label: "Keyword" },
    { key: "source", label: "Kaynak" },
    { key: "status", label: "Durum", render: (v) => <HiveStatusBadge status={statusVariant(v)} label={v} /> },
    { key: "items", label: "Items", render: (_, row) => row.items?.length ?? 0 },
    {
      key: "actions",
      label: "",
      render: (_, row) => (
        <span className="hive-inline-actions">
          {row.status !== "completed" && row.status !== "paused" && (
            <HiveBtn size="sm" onClick={() => handleProcess(row.batch_id)} disabled={loading}>İşle</HiveBtn>
          )}
          {row.status === "processing" && (
            <HiveBtn size="sm" variant="ghost" onClick={() => handlePause(row.batch_id)}>Duraklat</HiveBtn>
          )}
          {row.status === "paused" && (
            <HiveBtn size="sm" onClick={() => handleResume(row.batch_id)}>Devam</HiveBtn>
          )}
        </span>
      ),
    },
  ];

  const itemColumns = [
    { key: "item_id", label: "Item" },
    { key: "batch_name", label: "Batch" },
    { key: "provider", label: "Provider" },
    { key: "title", label: "Başlık" },
    { key: "status", label: "Durum", render: (v) => <HiveStatusBadge status={statusVariant(v)} label={v} /> },
    {
      key: "assigned_worker",
      label: "Task ID",
      render: (v, row) => {
        const tid = row?.metadata?.google_sites_task_id || (v && String(v).includes(":") ? v.split(":").pop() : null);
        return tid || "—";
      },
    },
    { key: "quality_score", label: "Q Score", render: (v) => (v ?? "—") },
    { key: "metadata", label: "Queue ID", render: (v) => v?.queue_id || "—" },
    { key: "metadata", label: "Words", render: (v) => v?.word_count ?? "—" },
    { key: "metadata", label: "FAQ", render: (v) => v?.faq_count ?? "—" },
    { key: "metadata", label: "Entity", render: (v) => v?.entity_count ?? "—" },
    { key: "result_url", label: "URL", render: (v) => v ? <a href={v} target="_blank" rel="noreferrer">{v.slice(0, 40)}…</a> : "—" },
    {
      key: "error",
      label: "Hata",
      render: (v, row) => (
        row?.status === "login_required"
          ? <span title={v}>Google giriş gerekli — Resume Task</span>
          : (v || "—")
      ),
    },
    {
      key: "actions",
      label: "",
      render: (_, row) => (
        <HiveBtn size="sm" variant="ghost" onClick={() => handlePreviewContent(row.item_id)}>
          Preview Content
        </HiveBtn>
      ),
    },
  ];

  return (
    <HiveShell
      title="Authority Factory"
      subtitle="Authority Mesh planlarını kontrollü üretim batch'lerine çevirir"
      icon="🏭"
      loading={loading}
    >
      {error && <HiveAlert type="error">{error}</HiveAlert>}
      <HiveToast message={message} onClose={() => setMessage("")} />

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />
      {loading && !dash && <HiveSkeleton lines={6} />}

      {tab === "dashboard" && (
        <HivePanel>
          <HiveStatGrid
            stats={[
              { label: "Modül", value: health?.enabled ? "Aktif" : "Kapalı" },
              { label: "V2 Batches", value: dash?.v2_batches ?? 0 },
              { label: "Queued Items", value: dash?.queued_items ?? 0 },
              { label: "Processing", value: dash?.processing_items ?? 0 },
              { label: "Published", value: dash?.published_items ?? 0 },
              { label: "Login Required", value: dash?.login_required_items ?? 0 },
              { label: "Provider Missing", value: dash?.provider_missing_items ?? 0 },
              { label: "Failed", value: dash?.failed_items ?? 0 },
            ]}
          />
          <HiveSection title="V2 Operasyon Kartları">
            <HiveStatGrid
              stats={[
                { label: "Dataset Driven", value: dash?.dataset_driven_batches ?? 0, highlight: true },
                { label: "Domain Driven", value: dash?.domain_driven_batches ?? 0, highlight: true },
                { label: "Campaign Driven", value: dash?.campaign_driven_batches ?? 0, highlight: true },
              ]}
            />
          </HiveSection>
          <HiveSection title="Son Batch'ler">
            <HiveTable columns={batchColumns.slice(0, 6)} rows={dash?.recent_batches || []} emptyText="Henüz batch yok" />
          </HiveSection>
        </HivePanel>
      )}

      {tab === "create_campaign" && (
        <HivePanel>
          <HiveSection title="Campaign → Authority Factory V2">
            <HiveField label="Campaign ID"><HiveInput value={campaignId} onChange={(e) => setCampaignId(e.target.value)} placeholder="camp-..." /></HiveField>
            <HiveBtn onClick={handleCreateFromCampaign} disabled={loading}>Batch Oluştur</HiveBtn>
          </HiveSection>
        </HivePanel>
      )}

      {tab === "create_dataset" && (
        <HivePanel>
          <HiveSection title="Data Miner Dataset → Authority V2">
            <HiveField label="Dataset / Job ID"><HiveInput value={datasetId} onChange={(e) => setDatasetId(e.target.value)} placeholder="dm-job-..." /></HiveField>
            <HiveField label="Keyword (opsiyonel)"><HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} /></HiveField>
            <HiveBtn onClick={handleCreateFromDataset} disabled={loading}>Dataset'ten Oluştur</HiveBtn>
            <HiveTable columns={[{ key: "id", label: "ID" }, { key: "source", label: "Kaynak" }, { key: "entity_count", label: "Entities" }, { key: "faq_count", label: "FAQs" }]} rows={datasets} emptyText="Dataset yok" />
          </HiveSection>
        </HivePanel>
      )}

      {tab === "domain_candidates" && (
        <HivePanel>
          <HiveSection title="Domain Intelligence Adayları">
            <HiveField label="Keyword"><HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} /></HiveField>
            <HiveBtn onClick={handleCreateFromDomains} disabled={loading}>Seçili Adaylardan Batch</HiveBtn>
            <HiveTable columns={[{ key: "domain", label: "Domain" }, { key: "overall_domain_score", label: "Score" }, { key: "spam_risk_score", label: "Spam" }]} rows={domainCandidates} emptyText="Uygun aday yok" />
          </HiveSection>
        </HivePanel>
      )}

      {tab === "provider_mix" && (
        <HivePanel>
          <HiveSection title="Varsayılan Provider Mix">
            {providerMix && (
              <HiveTable columns={[{ key: "provider", label: "Provider" }, { key: "count", label: "Count" }]} rows={Object.entries(providerMix).map(([provider, count]) => ({ provider, count }))} />
            )}
          </HiveSection>
        </HivePanel>
      )}

      {tab === "items" && (
        <HivePanel>
          <HiveTable columns={itemColumns} rows={items} emptyText="Item yok" />
          {preview && (
            <HiveSection title={`Item Preview: ${preview.item_id}`}>
              <HiveStatGrid
                stats={[
                  { label: "Word count", value: preview.word_count ?? 0 },
                  { label: "FAQ count", value: preview.faq_count ?? 0 },
                  { label: "Entity count", value: preview.entity_count ?? 0 },
                  { label: "Quality score", value: preview.quality_score ?? 0, highlight: true },
                  { label: "Queue ID", value: items.find((x) => x.item_id === preview.item_id)?.metadata?.queue_id || "—" },
                ]}
              />
              <pre className="hive-code-block">{JSON.stringify(preview.quality_reasons || [], null, 2)}</pre>
            </HiveSection>
          )}
        </HivePanel>
      )}

      {tab === "create" && (
        <HivePanel>
          <HiveSection title="Yeni Authority Batch">
            <HiveField label="Keyword">
              <HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="kuşadası gece hayatı" />
            </HiveField>
            <HiveField label="Money Site">
              <HiveInput value={moneySite} onChange={(e) => setMoneySite(e.target.value)} />
            </HiveField>
            <HiveField label="Batch Adı (opsiyonel)">
              <HiveInput value={batchName} onChange={(e) => setBatchName(e.target.value)} />
            </HiveField>
            <HiveField label="Kaynak">
              <select value={source} onChange={(e) => setSource(e.target.value)} className="hive-select">
                <option value="manual">manual</option>
                <option value="authority_mesh">authority_mesh</option>
                <option value="opportunity">opportunity</option>
                <option value="serp_defense">serp_defense</option>
                <option value="action_orchestrator">action_orchestrator</option>
              </select>
            </HiveField>
            <HiveCheck checked={autoProcess} onChange={setAutoProcess} label="Oluşturduktan sonra işle (auto_process)" />
            <HiveBtn onClick={handleCreateBatch} disabled={loading || !health?.enabled}>
              Batch Oluştur
            </HiveBtn>
            {!health?.enabled && (
              <HiveAlert type="warn">Factory kapalı — Settings sekmesinden enabled=true yapın.</HiveAlert>
            )}
            {lastBatch && (
              <HiveSection title="Son Oluşturulan">
                <pre className="hive-code-block">{JSON.stringify(lastBatch.summary, null, 2)}</pre>
              </HiveSection>
            )}
          </HiveSection>
        </HivePanel>
      )}

      {tab === "batches" && (
        <HivePanel>
          <HiveTable columns={batchColumns} rows={batches} emptyText="Batch bulunamadı" />
        </HivePanel>
      )}

      {["processing", "published", "failed", "login_required"].includes(tab) && (
        <HivePanel>
          <HiveTable columns={itemColumns} rows={items} emptyText="Item yok" />
        </HivePanel>
      )}

      {tab === "providers" && (
        <HivePanel>
          <HiveSection title="Provider Durumu">
            <HiveTable
              columns={[
                { key: "id", label: "Provider", render: (_, row) => row.id },
                { key: "label", label: "Label" },
                { key: "provider_type", label: "Tip" },
                { key: "ready", label: "Hazır", render: (v) => (v ? "✓" : "✗") },
                { key: "error", label: "Hata" },
              ]}
              rows={Object.entries(dash?.provider_status || {}).map(([id, v]) => ({ id, ...v }))}
              emptyText="Provider verisi yok"
            />
          </HiveSection>
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel>
          <HiveSection title="Rapor Export">
            {["overview", "batches", "items", "providers"].map((rt) => (
              <HiveBtn key={rt} variant="ghost" onClick={() => handleExport(rt)} style={{ marginRight: 8 }}>
                {rt}
              </HiveBtn>
            ))}
            {exportPath && <p className="hive-muted">Kaydedildi: {exportPath}</p>}
          </HiveSection>
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel>
          <HiveSection title="Güvenlik & Üretim Ayarları">
            {[
              ["enabled", "Factory aktif"],
              ["auto_process", "Otomatik işle"],
              ["allow_github_pages", "GitHub Pages"],
              ["allow_google_sites", "Google Sites"],
              ["allow_publisher", "Publisher (Blogger/Tumblr/Dev.to/WP)"],
              ["allow_astro", "Astro support site"],
              ["duplicate_block", "Duplicate engelle"],
            ].map(([key, label]) => (
              <HiveCheck
                key={key}
                checked={!!settings[key]}
                onChange={(v) => setSettings({ ...settings, [key]: v })}
                label={label}
              />
            ))}
            <HiveField label="max_items_per_batch">
              <HiveInput
                type="number"
                value={settings.max_items_per_batch ?? 25}
                onChange={(e) => setSettings({ ...settings, max_items_per_batch: Number(e.target.value) })}
              />
            </HiveField>
            <HiveField label="max_exact_anchor_ratio">
              <HiveInput
                type="number"
                step="0.01"
                value={settings.max_exact_anchor_ratio ?? 0.15}
                onChange={(e) => setSettings({ ...settings, max_exact_anchor_ratio: Number(e.target.value) })}
              />
            </HiveField>
            <HiveBtn onClick={handleSaveSettings} disabled={loading}>Kaydet</HiveBtn>
          </HiveSection>
        </HivePanel>
      )}
    </HiveShell>
  );
}
