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
  HiveCard,
  HiveCode,
} from "../components/HiveModuleUI";

import HiveApiErrorCard from "../components/HiveApiErrorCard";
import { BrainEventTimeline } from "../components/HiveOSVisualizations";
import { formatHiveApiError } from "../utils/hiveApiErrors";

const API_PREFIX = "/api/hive-brain";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "timeline", label: "Timeline" },
  { id: "projects", label: "Project Memory" },
  { id: "domains", label: "Domain Memory" },
  { id: "keywords", label: "Keyword Memory" },
  { id: "decisions", label: "Decisions" },
  { id: "story", label: "Project Story" },
];

function apiError(e, endpoint) {
  return formatHiveApiError(e, endpoint);
}

export default function HiveBrain({ onNavigate }) {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [events, setEvents] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [projectMemory, setProjectMemory] = useState(null);
  const [domainMemory, setDomainMemory] = useState(null);
  const [keywordMemory, setKeywordMemory] = useState(null);
  const [story, setStory] = useState(null);
  const [projectId, setProjectId] = useState("");
  const [domain, setDomain] = useState("");
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [h, d, ev, dec, tl] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/events?limit=40`),
        API.get(`${API_PREFIX}/decisions?limit=30`),
        API.get(`${API_PREFIX}/timeline?days=14`),
      ]);
      setHealth(h.data);
      setDash(d.data);
      setEvents(ev.data.events || []);
      setDecisions(dec.data.decisions || []);
      setTimeline(tl.data.timeline || []);
      setError("");
    } catch (e) {
      setError(apiError(e, `${API_PREFIX}/dashboard`));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    try {
      const q = sessionStorage.getItem("hive_brain_search");
      if (q) {
        sessionStorage.removeItem("hive_brain_search");
        setTab("timeline");
      }
    } catch { /* ignore */ }
  }, []);

  const loadProject = async () => {
    if (!projectId.trim()) return;
    setLoading(true);
    try {
      const res = await API.get(`${API_PREFIX}/project/${encodeURIComponent(projectId.trim())}`);
      setProjectMemory(res.data);
      setMessage(`Proje hafızası yüklendi: ${projectId}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadStory = async () => {
    if (!projectId.trim()) return;
    setLoading(true);
    try {
      const res = await API.get(`${API_PREFIX}/project/${encodeURIComponent(projectId.trim())}/story`);
      setStory(res.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadDomain = async () => {
    if (!domain.trim()) return;
    setLoading(true);
    try {
      const res = await API.get(`${API_PREFIX}/domain/${encodeURIComponent(domain.trim())}`);
      setDomainMemory(res.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadKeyword = async () => {
    if (!keyword.trim()) return;
    setLoading(true);
    try {
      const res = await API.get(`${API_PREFIX}/keyword/${encodeURIComponent(keyword.trim())}`);
      setKeywordMemory(res.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const backfillLogs = async () => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/backfill/logs?limit=300`);
      setMessage(`${res.data.imported || 0} olay activity log'dan içe aktarıldı`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const backfillStates = async () => {
    setLoading(true);
    try {
      const res = await API.post(`${API_PREFIX}/backfill/states`);
      setMessage(`${res.data.imported || 0} olay engine state'lerden içe aktarıldı`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <HiveShell
      title="🧠 HIVE Brain / Memory Engine"
      subtitle="Ne yaptı? Ne zaman? Neden? Sonuç? Sonraki öneri? — tüm modül olaylarının merkezi hafızası"
    >
      <HiveToolbar>
        <HiveBtn variant="ghost" onClick={refresh}>Yenile</HiveBtn>
        <HiveBtn variant="outline" onClick={backfillLogs} disabled={loading}>Log Backfill</HiveBtn>
        <HiveBtn variant="outline" onClick={backfillStates} disabled={loading}>State Backfill</HiveBtn>
      </HiveToolbar>

      {message && <HiveAlert type="ok">{message}</HiveAlert>}
      {error && <HiveApiErrorCard errorInfo={error} />}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && dash && (
        <>
          {dash.status === "empty" && (
            <HiveAlert type="info">
              {dash.message || "Henüz kayıt yok"} — {dash.next_action?.label || "Backfill çalıştır"}
            </HiveAlert>
          )}
          <div className="hive-ops-pills" style={{ marginBottom: "0.75rem" }}>
            <span className="hive-pill hive-pill-accent hive-pill-sm">{health?.events_count ?? dash.total_events ?? 0} events</span>
            <span className="hive-pill hive-pill-success hive-pill-sm">{dash.today_count ?? 0} today</span>
            <span className="hive-pill hive-pill-neutral hive-pill-sm">{health?.projects_tracked ?? 0} projects</span>
            <span className="hive-pill hive-pill-warning hive-pill-sm">{dash.pending_decisions ?? 0} pending</span>
          </div>
          <BrainEventTimeline events={events} timeline={timeline} title="Brain Timeline" onNavigate={onNavigate} />
        </>
      )}

      {tab === "timeline" && (
        <BrainEventTimeline events={events} timeline={timeline} title="Brain Timeline" onNavigate={onNavigate} />
      )}

      {tab === "projects" && (
        <HivePanel>
          <div className="hm-form-row">
            <HiveField label="Project ID">
              <HiveInput value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="astro-proj-xxx" />
            </HiveField>
            <HiveBtn onClick={loadProject} disabled={loading || !projectId}>Yükle</HiveBtn>
          </div>
          {projectMemory?.memory && (
            <>
              <HiveStatGrid items={[
                ["Özet", (projectMemory.memory.project_summary || "—").slice(0, 40)],
                ["Son aksiyon", projectMemory.memory.last_actions?.length || 0],
                ["Karar", projectMemory.memory.important_decisions?.length || 0],
              ]} />
              <h4 className="hm-panel-title">Sonraki öneriler</h4>
              <ul style={{ fontSize: "0.88rem", paddingLeft: "1.2rem" }}>
                {(projectMemory.memory.next_recommended_actions || []).map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
              <HiveTable
                columns={[
                  { key: "timestamp", label: "Zaman" },
                  { key: "event_type", label: "Tip" },
                  { key: "summary", label: "Özet" },
                ]}
                rows={(projectMemory.recent_event_details || []).map((e) => ({
                  id: e.event_id,
                  timestamp: e.timestamp,
                  event_type: e.event_type,
                  summary: e.summary,
                }))}
                emptyText="Olay yok"
              />
            </>
          )}
        </HivePanel>
      )}

      {tab === "domains" && (
        <HivePanel>
          <div className="hm-form-row">
            <HiveField label="Domain">
              <HiveInput value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="balkutusu.com" />
            </HiveField>
            <HiveBtn onClick={loadDomain} disabled={loading || !domain}>Yükle</HiveBtn>
          </div>
          {domainMemory?.memory && (
            <>
              <p className="hm-meta-line">İlk görülme: <strong>{domainMemory.memory.first_seen}</strong></p>
              <HiveStatGrid items={[
                ["Deploy", domainMemory.memory.deploy_history?.length || 0],
                ["Publish", domainMemory.memory.publish_history?.length || 0],
                ["Rol", domainMemory.memory.role_history?.length || 0],
                ["Keyword", domainMemory.memory.keyword_history?.length || 0],
              ]} />
            </>
          )}
        </HivePanel>
      )}

      {tab === "keywords" && (
        <HivePanel>
          <div className="hm-form-row">
            <HiveField label="Keyword">
              <HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="kuşadası gece hayatı" />
            </HiveField>
            <HiveBtn onClick={loadKeyword} disabled={loading || !keyword}>Yükle</HiveBtn>
          </div>
          {keywordMemory?.memory && (
            <>
              <p className="hm-meta-line">İlk keşif: <strong>{keywordMemory.memory.first_discovery}</strong></p>
              <HiveStatGrid items={[
                ["Pozisyon", keywordMemory.memory.position_history?.length || 0],
                ["Fortress", keywordMemory.memory.fortress_history?.length || 0],
                ["Refresh", keywordMemory.memory.refresh_history?.length || 0],
                ["Savunma", keywordMemory.memory.defense_history?.length || 0],
              ]} />
            </>
          )}
        </HivePanel>
      )}

      {tab === "decisions" && (
        <HivePanel title="Decision Memory">
          <HiveTable
            columns={[
              { key: "timestamp", label: "Zaman" },
              { key: "module", label: "Modül" },
              { key: "recommendation", label: "Öneri" },
              { key: "applied", label: "Uygulandı" },
              { key: "outcome", label: "Sonuç" },
            ]}
            rows={decisions.map((d) => ({
              id: d.decision_id,
              timestamp: d.timestamp,
              module: d.module,
              recommendation: (d.recommendation || "").slice(0, 60),
              applied: d.applied === null ? "—" : d.applied ? "✓" : "✗",
              outcome: (d.outcome || "—").slice(0, 40),
            }))}
            emptyText="Karar kaydı yok"
          />
        </HivePanel>
      )}

      {tab === "story" && (
        <HivePanel>
          <div className="hm-form-row">
            <HiveField label="Project ID">
              <HiveInput value={projectId} onChange={(e) => setProjectId(e.target.value)} />
            </HiveField>
            <HiveBtn onClick={loadStory} disabled={loading || !projectId}>Hikayeyi Üret</HiveBtn>
          </div>
          {story?.story && (
            <>
              <HiveCode>{story.story}</HiveCode>
              {story.next_recommended_actions?.length > 0 && (
                <>
                  <h4 className="hm-panel-title">Sonraki adımlar</h4>
                  <ul style={{ fontSize: "0.88rem", paddingLeft: "1.2rem" }}>
                    {story.next_recommended_actions.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </>
              )}
            </>
          )}
        </HivePanel>
      )}

    </HiveShell>
  );
}
