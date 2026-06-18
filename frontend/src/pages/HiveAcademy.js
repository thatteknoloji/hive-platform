import React, { useState, useEffect, useCallback, useMemo } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveBtn,
  HiveBadge,
  HiveSection,
  HiveEmptyState,
} from "../components/HiveModuleUI";
import HiveApiErrorCard from "../components/HiveApiErrorCard";
import { formatHiveApiError } from "../utils/hiveApiErrors";

const API_PREFIX = "/api/hive-academy";

const CATEGORY_LABELS = {
  command: "COMMAND",
  seo_core: "SEO CORE",
  content: "CONTENT",
  network: "NETWORK",
  workers: "WORKERS",
  learn: "LEARN",
  tools: "TOOLS",
};

function apiError(e, endpoint = `${API_PREFIX}/modules`) {
  return formatHiveApiError(e, endpoint);
}

export default function HiveAcademy({ onNavigate }) {
  const [tab, setTab] = useState("modules");
  const [health, setHealth] = useState(null);
  const [modules, setModules] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [guides, setGuides] = useState([]);
  const [glossary, setGlossary] = useState({});
  const [selectedModule, setSelectedModule] = useState(null);
  const [selectedGuide, setSelectedGuide] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const go = (id) => onNavigate?.(id);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, m, w, g] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/modules`),
        API.get(`${API_PREFIX}/workflows`),
        API.get(`${API_PREFIX}/guides`),
      ]);
      setHealth(h.data);
      setModules(m.data.modules || []);
      setWorkflows(w.data.workflows || []);
      setGuides(g.data.guides || []);
      setGlossary(g.data.glossary || {});
    } catch (err) {
      setError(apiError(err, `${API_PREFIX}/modules`));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const openModule = async (moduleId) => {
    setLoading(true);
    try {
      const res = await API.get(`${API_PREFIX}/module/${moduleId}`);
      setSelectedModule(res.data.module);
      setSelectedGuide(null);
      setTab("detail");
      await refresh();
    } catch (err) {
      setError(apiError(err, `${API_PREFIX}/module/${moduleId}`));
    } finally {
      setLoading(false);
    }
  };

  const openGuide = async (guide) => {
    setLoading(true);
    try {
      const res = await API.get(`${API_PREFIX}/guide/${guide.guide_id}`);
      setSelectedGuide(res.data.guide);
      setSelectedModule(null);
      setTab("guide_detail");
    } catch (err) {
      setError(apiError(err, `${API_PREFIX}/guide/${guide.guide_id}`));
    } finally {
      setLoading(false);
    }
  };

  const exportAcademy = async () => {
    try {
      const res = await API.post(`${API_PREFIX}/export`, { report_type: "overview" });
      setMessage(`Export: ${res.data.filename}`);
    } catch (err) {
      setError(apiError(err, `${API_PREFIX}/export`));
    }
  };

  const filteredModules = useMemo(() => {
    if (categoryFilter === "all") return modules;
    return modules.filter((m) => m.category === categoryFilter);
  }, [modules, categoryFilter]);

  const categories = useMemo(() => {
    const set = new Set(modules.map((m) => m.category).filter(Boolean));
    return ["all", ...Array.from(set)];
  }, [modules]);

  const TABS = [
    { id: "modules", label: "Modül Ansiklopedisi" },
    { id: "workflows", label: "Workflow Haritaları" },
    { id: "guides", label: "Rehberler" },
    { id: "glossary", label: "Kavramlar" },
    ...(selectedModule ? [{ id: "detail", label: selectedModule.title?.slice(0, 28) || "Detay" }] : []),
    ...(selectedGuide ? [{ id: "guide_detail", label: selectedGuide.title?.slice(0, 28) || "Rehber" }] : []),
  ];

  return (
    <div className="hive-module hive-learn-page">
      <section className="hive-os-hero hive-learn-hero">
        <div className="hive-os-hero-glow" aria-hidden />
        <div className="hive-os-hero-top">
          <div>
            <span className="hive-os-hero-kicker">HIVE SEO OS · Learn</span>
            <h1 className="hive-os-hero-title">🎓 HIVE Academy</h1>
            <p className="hive-os-hero-sub">
              {health?.modules_total ?? modules.length} modül · {health?.workflows_total ?? workflows.length} workflow ·
              {" "}{health?.guides_total ?? guides.length} rehber — tam operasyon dokümantasyonu
            </p>
          </div>
          <div className="hive-learn-stats-row">
            <div className="hive-learn-progress-badge">
              <span>İlerleme</span>
              <strong>{health?.progress_percent ?? 0}%</strong>
            </div>
            <div className="hive-learn-progress-badge">
              <span>Görüntülenen</span>
              <strong>{health?.modules_viewed ?? 0}</strong>
            </div>
          </div>
        </div>
      </section>

      <HiveShell
        title=""
        subtitle=""
        actions={
          <>
            <HiveBtn variant="secondary" onClick={exportAcademy} disabled={loading}>Export</HiveBtn>
            <HiveBtn onClick={refresh} disabled={loading}>{loading ? "…" : "↻ Yenile"}</HiveBtn>
          </>
        }
      >
        {error && <HiveApiErrorCard errorInfo={error} />}
        {message && <HiveAlert type="success">{message}</HiveAlert>}

        <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

        {tab === "modules" && (
          <HiveSection title="Modül Ansiklopedisi" description={`${filteredModules.length} modül — ne işe yarar, ne zaman kullanılır, ilk adımlar`}>
            <div className="hive-academy-filters">
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={`hive-academy-filter-btn ${categoryFilter === cat ? "active" : ""}`}
                  onClick={() => setCategoryFilter(cat)}
                >
                  {cat === "all" ? "Tümü" : (CATEGORY_LABELS[cat] || cat)}
                </button>
              ))}
            </div>
            <div className="hive-academy-grid">
              {filteredModules.map((m) => (
                <button key={m.module_id} type="button" className="hive-academy-card" onClick={() => openModule(m.module_id)}>
                  <div className="hive-academy-card-head">
                    <span className="hive-academy-card-icon">{m.icon || "📦"}</span>
                    <HiveBadge tone="neutral">{CATEGORY_LABELS[m.category] || m.category}</HiveBadge>
                  </div>
                  <strong>{m.title}</strong>
                  <p>{m.purpose}</p>
                  {m.guide_id && <HiveBadge tone="info">📖 Rehber mevcut</HiveBadge>}
                </button>
              ))}
            </div>
          </HiveSection>
        )}

        {tab === "workflows" && (
          <HiveSection title="Workflow Haritaları" description="Operasyon senaryoları — adım adım modül sırası">
            {workflows.map((wf) => (
              <HivePanel key={wf.workflow_id} title={wf.title} className="hive-workflow-panel">
                <p className="hm-section-desc">{wf.description}</p>
                <ol className="hive-workflow-steps">
                  {(wf.steps || []).map((s) => (
                    <li key={s.order}>
                      <button type="button" className="hive-workflow-step-btn" onClick={() => go(s.deep_link || s.module_id)}>
                        <span className="hive-os-mission-order">{s.order}</span>
                        <span>{s.title}</span>
                        <HiveBadge tone="neutral">{s.module_id?.replace(/_/g, " ")}</HiveBadge>
                      </button>
                    </li>
                  ))}
                </ol>
              </HivePanel>
            ))}
          </HiveSection>
        )}

        {tab === "guides" && (
          <HiveSection title="Operasyon Rehberleri" description="Adım adım, checklist ve troubleshooting ile tam rehberler">
            <div className="hive-academy-grid">
              {guides.map((g) => (
                <button key={g.guide_id} type="button" className="hive-academy-card hive-guide-card" onClick={() => openGuide(g)}>
                  <strong>{g.title}</strong>
                  <p>{g.summary}</p>
                  <div className="hive-guide-card-meta">
                    {g.estimated_time && <HiveBadge tone="info">⏱ {g.estimated_time}</HiveBadge>}
                    {g.step_count > 0 && <HiveBadge tone="neutral">{g.step_count} adım</HiveBadge>}
                  </div>
                </button>
              ))}
            </div>
          </HiveSection>
        )}

        {tab === "glossary" && (
          <HiveSection title="Kavram Sözlüğü" description="HIVE SEO OS terminolojisi">
            <div className="hive-glossary-list">
              {Object.entries(glossary).map(([key, text]) => (
                <div key={key} className="hive-glossary-item">
                  <strong>{key.replace(/_/g, " ")}</strong>
                  <p>{text}</p>
                </div>
              ))}
              {!Object.keys(glossary).length && (
                <HiveEmptyState title="Kavram yüklenemedi" actionLabel="Yenile" onAction={refresh} />
              )}
            </div>
          </HiveSection>
        )}

        {tab === "detail" && selectedModule && (
          <HiveSection title={`${selectedModule.icon || "📦"} ${selectedModule.title}`}>
            <div className="hive-module-detail">
              <div className="hive-module-detail-meta">
                <HiveBadge tone="neutral">{CATEGORY_LABELS[selectedModule.category] || selectedModule.category}</HiveBadge>
                {selectedModule.api_prefix && <code className="hive-api-prefix">{selectedModule.api_prefix}</code>}
              </div>
              <DetailBlock label="Amaç" value={selectedModule.purpose} />
              <DetailBlock label="Ne işe yarar" value={selectedModule.what_it_does} />
              <DetailBlock label="Ne zaman kullanılır" value={selectedModule.when_to_use} highlight />
              <DetailBlock label="Ne zaman kullanılmaz" value={selectedModule.when_not_to_use} />
              <DetailList label="İlk adımlar" items={selectedModule.first_steps} ordered />
              <DetailList label="Giriş verileri" items={selectedModule.inputs} />
              <DetailList label="Çıkış verileri" items={selectedModule.outputs} />
              <DetailList label="Bağlı modüller" items={selectedModule.related_modules} link onLink={go} />
              {selectedModule.env_keys?.length > 0 && (
                <DetailList label="Gerekli .env anahtarları" items={selectedModule.env_keys} env />
              )}
              <DetailBlock label="Örnek kullanım" value={selectedModule.example_usage} code />
              <DetailList label="Yaygın hatalar" items={selectedModule.common_mistakes} warn />
              <DetailList label="İleri seviye ipuçları" items={selectedModule.advanced_tips} tip />
              <div className="hive-module-detail-actions">
                <HiveBtn onClick={() => go(selectedModule.module_id)}>Modüle Git →</HiveBtn>
                {selectedModule.guide_id && (
                  <HiveBtn variant="secondary" onClick={() => openGuide({ guide_id: selectedModule.guide_id })}>
                    📖 Rehberi Aç
                  </HiveBtn>
                )}
                <HiveBtn variant="ghost" onClick={() => setTab("modules")}>← Ansiklopedi</HiveBtn>
              </div>
            </div>
          </HiveSection>
        )}

        {tab === "guide_detail" && selectedGuide && (
          <HiveSection title={selectedGuide.title}>
            <div className="hive-guide-detail">
              <p className="hive-guide-summary">{selectedGuide.summary}</p>
              <div className="hive-guide-detail-meta">
                {selectedGuide.estimated_time && <HiveBadge tone="info">⏱ {selectedGuide.estimated_time}</HiveBadge>}
                {selectedGuide.module_id && (
                  <HiveBtn size="sm" variant="secondary" onClick={() => go(selectedGuide.module_id)}>Modüle Git</HiveBtn>
                )}
              </div>
              {selectedGuide.prerequisites?.length > 0 && (
                <DetailList label="Ön koşullar" items={selectedGuide.prerequisites} />
              )}
              {selectedGuide.steps?.length > 0 && (
                <div className="hive-guide-steps">
                  <h4>Adım adım</h4>
                  <ol>
                    {selectedGuide.steps.map((s) => (
                      <li key={s.order} className="hive-guide-step-item">
                        <span className="hive-os-mission-order">{s.order}</span>
                        <div>
                          <strong>{s.title}</strong>
                          <p>{s.body}</p>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              {selectedGuide.checklist?.length > 0 && (
                <DetailList label="Checklist" items={selectedGuide.checklist} check />
              )}
              {selectedGuide.troubleshooting?.length > 0 && (
                <div className="hive-guide-troubleshooting">
                  <h4>Sorun giderme</h4>
                  {selectedGuide.troubleshooting.map((t, i) => (
                    <div key={i} className="hive-troubleshoot-item">
                      <strong>{typeof t === "string" ? t : t.issue}</strong>
                      {typeof t === "object" && t.fix && <p>{t.fix}</p>}
                    </div>
                  ))}
                </div>
              )}
              <HiveBtn variant="ghost" onClick={() => setTab("guides")}>← Rehberler</HiveBtn>
            </div>
          </HiveSection>
        )}
      </HiveShell>
    </div>
  );
}

function DetailBlock({ label, value, highlight, code }) {
  if (!value) return null;
  return (
    <div className={`hive-detail-block ${highlight ? "hive-detail-highlight" : ""}`}>
      <h4>{label}</h4>
      {code ? <pre className="hive-detail-code">{value}</pre> : <p>{value}</p>}
    </div>
  );
}

function DetailList({ label, items, link, onLink, ordered, env, warn, tip, check }) {
  if (!items?.length) return null;
  const Tag = ordered ? "ol" : "ul";
  return (
    <div className={`hive-detail-block ${warn ? "hive-detail-warn" : ""} ${tip ? "hive-detail-tip" : ""}`}>
      <h4>{label}</h4>
      <Tag className={check ? "hive-checklist" : ""}>
        {items.map((item) => (
          <li key={item}>
            {link ? (
              <button type="button" className="hive-link-btn" onClick={() => onLink?.(item)}>
                {item.replace(/_/g, " ")}
              </button>
            ) : env ? (
              <code>{item}</code>
            ) : (
              item
            )}
          </li>
        ))}
      </Tag>
    </div>
  );
}
