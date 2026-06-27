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
  HiveCheck,
  HiveField,
  HiveSelect,
  HiveMissionBoard,
  HiveContextBar,
  HiveSection,
  HiveSkeleton,
  HiveToast,
  HiveEmptyState,
  HiveConceptTooltip,
} from "../components/HiveModuleUI";
import { HIVE_CONCEPTS, ACADEMY_GUIDE_MODULES } from "../config/hiveConcepts";
import { HivePanelHero, PublisherKanban } from "../components/HiveOSVisualizations";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "sources", label: "Sources" },
  { id: "channels", label: "Channels" },
  { id: "drafts", label: "Drafts" },
  { id: "queue", label: "Queue" },
  { id: "published", label: "Published" },
  { id: "jobs", label: "Jobs" },
  { id: "reports", label: "Reports" },
];

const SOURCE_LABELS = {
  astro_factory: "Astro Factory",
  place_seo_pipeline: "Place SEO Pipeline",
  entity_detail_generator: "Entity Detail Generator",
  question_intelligence_engine: "Question Intelligence Engine",
  content_refresh_engine: "Content Refresh Engine",
  listing_hub: "Listing Hub",
  network_replicator: "Network Replicator",
};

function apiError(e) {
  return e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

export default function PublisherHub({ onNavigate }) {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [settings, setSettings] = useState(null);
  const [channels, setChannels] = useState([]);
  const [sources, setSources] = useState([]);
  const [queue, setQueue] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [published, setPublished] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [selectedChannels, setSelectedChannels] = useState(["wordpress"]);

  const refresh = useCallback(async () => {
    try {
      const [h, s, ch, q, d, p, j] = await Promise.all([
        API.get("/api/publisher-hub/health"),
        API.get("/api/publisher-hub/settings"),
        API.get("/api/publisher-hub/channels"),
        API.get("/api/publisher-hub/queue"),
        API.get("/api/publisher-hub/drafts"),
        API.get("/api/publisher-hub/published"),
        API.get("/api/publisher-hub/jobs"),
      ]);
      setHealth(h.data);
      setSettings(s.data.settings);
      setChannels(ch.data.channels || []);
      setQueue(q.data.queue || []);
      setDrafts(d.data.drafts || []);
      setPublished(p.data.published || []);
      setJobs(j.data.jobs || []);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const saveSettings = async (patch) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/publisher-hub/settings", patch);
      setSettings(res.data.settings);
      setMessage("Ayarlar kaydedildi");
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const runScan = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.get("/api/publisher-hub/sources/scan");
      setSources(res.data.items || []);
      setMessage(`${res.data.count} kaynak içerik bulundu`);
      setTab("sources");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const enqueueSource = async (item) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/publisher-hub/enqueue", {
        ...item,
        channels: selectedChannels,
      });
      setMessage(`Kuyruğa alındı: ${res.data.publish_id} (${res.data.status})`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const approveDraft = async (publishId) => {
    setLoading(true);
    try {
      await API.post("/api/publisher-hub/approve", { publish_id: publishId, channels: selectedChannels });
      setMessage("Taslak onaylandı ve kuyruğa alındı");
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const publishOne = async (publishId) => {
    setLoading(true);
    try {
      const res = await API.post("/api/publisher-hub/publish", { publish_id: publishId });
      setMessage(`Yayın: ${res.data.status}`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const processQueue = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/publisher-hub/process");
      setMessage(`İşlendi: ${res.data.summary?.published || 0} yayın, ${res.data.summary?.failed || 0} hata`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const requeueRefresh = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/publisher-hub/requeue-refresh", {});
      setMessage(`Content Refresh: ${res.data.queued} öğe kuyruğa alındı`);
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
      const res = await API.post("/api/publisher-hub/export-report");
      setExportPath(res.data.path || "");
      setMessage("Rapor dışa aktarıldı");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const toggleChannel = (id) => {
    setSelectedChannels((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const dash = health?.dashboard || {};

  return (
    <div className="hive-module hive-os-command-center">
      <HivePanelHero
        kicker="Publisher OS"
        title="Publisher Hub"
        subtitle="WordPress · Ghost · Medium · LinkedIn — kaynak → taslak → kuyruk → yayın"
      />
    <HiveShell title="" subtitle="">
      <HiveToast message={message} onClose={() => setMessage("")} />
      <HiveAlert type="err">{error}</HiveAlert>

      <HiveContextBar>
        <HiveBtn variant="primary" disabled={loading} onClick={runScan}>Kaynakları Tara</HiveBtn>
        <HiveBtn variant="success" disabled={loading} onClick={processQueue}>Kuyruğu İşle</HiveBtn>
        <HiveBtn variant="outline" disabled={loading} onClick={requeueRefresh}>CRE → Kuyruk</HiveBtn>
        <HiveBtn variant="outline" disabled={loading} onClick={refresh}>Yenile</HiveBtn>
      </HiveContextBar>

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />
      {loading && !dash && <HiveSkeleton lines={6} />}

      {tab === "dashboard" && (
        <>
          <PublisherKanban
            drafts={drafts}
            queue={queue}
            jobs={jobs}
            published={published}
            failed={jobs.filter((j) => (j.status || "").toLowerCase() === "failed")}
          />
          <HivePanel title="Publish Pipeline" description="Kuyruk, taslak ve kanal durumu">
            <p className="hm-label-tip hm-panel-tip">
              Publish Queue
              <HiveConceptTooltip conceptKey="publish_queue" concepts={HIVE_CONCEPTS} />
            </p>
            <HiveMissionBoard
              primary={[
                { label: "Queued", value: dash.queued ?? 0, tone: "accent" },
                { label: "Published", value: dash.published ?? 0, tone: "ok" },
                { label: "Review Required", value: dash.review_required ?? 0, tone: dash.review_required ? "warn" : "default" },
              ]}
              secondary={[
                { label: "Drafts", value: dash.drafts ?? 0 },
                { label: "Connected Channels", value: health?.channels_connected ?? "—" },
                { label: "Min Quality Score", value: health?.min_quality_score ?? 85 },
              ]}
            />
          </HivePanel>
          <HivePanel title="Hub Settings">
            {settings && (
              <div className="hm-settings-grid">
                <HiveCheck
                  label="Hub aktif"
                  checked={!!settings.enabled}
                  onChange={(e) => saveSettings({ enabled: e.target.checked })}
                />
                <HiveCheck
                  label="Otomatik yayın"
                  checked={!!settings.auto_publish}
                  onChange={(e) => saveSettings({ auto_publish: e.target.checked })}
                />
                <HiveCheck
                  label="Quality Gate zorunlu (≥85)"
                  checked={!!settings.require_quality_gate}
                  onChange={(e) => saveSettings({ require_quality_gate: e.target.checked })}
                />
                <HiveField label="Yayın modu">
                  <HiveSelect
                    value={settings.publish_mode || "manual"}
                    onChange={(e) => saveSettings({ publish_mode: e.target.value })}
                  >
                    <option value="manual">Manuel</option>
                    <option value="draft">Taslak</option>
                    <option value="auto">Otomatik</option>
                  </HiveSelect>
                </HiveField>
              </div>
            )}
          </HivePanel>
        </>
      )}

      {tab === "sources" && (
        <>
          <p className="hm-meta-line">Seçili kanallar: <strong>{selectedChannels.join(", ") || "—"}</strong></p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
            {channels.map((c) => (
              <HiveCheck
                key={c.id}
                label={`${c.label} (K${c.layer})`}
                checked={selectedChannels.includes(c.id)}
                onChange={() => toggleChannel(c.id)}
              />
            ))}
          </div>
          <HiveTable
            emptyText="Kaynak taraması yapın."
            columns={[
              { key: "source", label: "Kaynak", render: (r) => SOURCE_LABELS[r.source] || r.source },
              { key: "title", label: "Başlık" },
              { key: "content_type", label: "Tip" },
              { key: "keyword", label: "Keyword" },
              {
                key: "act",
                label: "",
                render: (r) => (
                  <HiveBtn variant="ghost" size="sm" onClick={() => enqueueSource(r)}>Kuyruğa Al</HiveBtn>
                ),
              },
            ]}
            rows={sources}
          />
        </>
      )}

      {tab === "channels" && (
        <div className="hm-stat-grid">
          {channels.map((c) => (
            <div key={c.id} className="hm-stat-card">
              <div className="hm-stat-label">Katman {c.layer} · {c.mode}</div>
              <div className="hm-stat-value" style={{ fontSize: "1rem" }}>{c.label}</div>
              <p className="hm-card-meta" style={{ marginTop: "0.5rem" }}>
                {c.connected ? "✓ Bağlı" : c.configured ? "Yapılandırılmış" : "Yapılandırılmamış"}
                {settings?.channels?.[c.id] === false ? " · Kapalı" : ""}
              </p>
              <HiveCheck
                label="Etkin"
                checked={!!settings?.channels?.[c.id]}
                onChange={(e) => saveSettings({ channels: { [c.id]: e.target.checked } })}
              />
            </div>
          ))}
        </div>
      )}

      {tab === "drafts" && (
        drafts.length ? drafts.map((d) => (
          <HiveCard
            key={d.publish_id}
            title={d.title}
            meta={`${d.status} · skor ${d.quality_score} · ${d.channels?.join(", ")}`}
            actions={
              <>
                <HiveBtn variant="outline" size="sm" onClick={() => approveDraft(d.publish_id)}>Onayla</HiveBtn>
                <HiveBtn variant="primary" size="sm" onClick={() => publishOne(d.publish_id)}>Yayınla</HiveBtn>
              </>
            }
          />
        )) : <p className="hm-empty">Taslak yok</p>
      )}

      {tab === "queue" && (
        queue.length ? (
          <HiveTable
            columns={[
              { key: "publish_id", label: "ID", render: (r) => <code>{r.publish_id}</code> },
              { key: "title", label: "Başlık" },
              { key: "source", label: "Kaynak" },
              { key: "quality_score", label: "Skor" },
              { key: "channels", label: "Kanallar", render: (r) => (r.channels || []).join(", ") },
              {
                key: "act",
                label: "",
                render: (r) => (
                  <HiveBtn variant="primary" size="sm" onClick={() => publishOne(r.publish_id)}>Yayınla</HiveBtn>
                ),
              },
            ]}
            rows={queue}
          />
        ) : (
          <HiveEmptyState
            icon="📢"
            title="Kuyruk boş"
            description="Kaynak taraması yapın veya Content Refresh'ten kuyruğa aktarın."
            actionLabel="Kaynakları Tara"
            onAction={() => setTab("sources")}
            academyLabel={ACADEMY_GUIDE_MODULES.publisher_hub.label}
            onAcademy={() => onNavigate?.("hive_academy")}
          />
        )
      )}

      {tab === "published" && (
        published.length ? published.map((p) => (
          <HiveCard
            key={p.publish_id}
            title={p.title}
            meta={`${p.source} · ${p.updated_at || ""}`}
          >
            {Object.entries(p.channel_results || {}).map(([ch, res]) => (
              <div key={ch}>{ch}: {res.success ? "✓" : "✗"} {res.url || res.error || ""}</div>
            ))}
          </HiveCard>
        )) : <p className="hm-empty">Henüz yayın yok</p>
      )}

      {tab === "jobs" && (
        jobs.length ? jobs.map((j) => (
          <HiveCard
            key={j.job_id}
            title={j.job_id}
            meta={`${j.type} · ${j.status} · ${j.started_at}`}
          >
            {j.summary && (
              <div className="hm-job-row">
                İşlenen: <strong>{j.summary.processed}</strong>
                {" · "}Yayın: <strong>{j.summary.published}</strong>
                {" · "}Hata: <strong>{j.summary.failed}</strong>
              </div>
            )}
          </HiveCard>
        )) : <p className="hm-empty">Job yok</p>
      )}

      {tab === "reports" && (
        <HivePanel>
          <HiveBtn variant="outline" disabled={loading} onClick={runExport}>Export Report</HiveBtn>
          {exportPath && <p className="hm-meta-line" style={{ marginTop: "0.75rem" }}>Dosya: <code>{exportPath}</code></p>}
        </HivePanel>
      )}
    </HiveShell>
    </div>
  );
}
