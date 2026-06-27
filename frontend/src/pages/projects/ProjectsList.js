import React, { useCallback, useEffect, useMemo, useState } from "react";
import API from "../../api";
import { useActiveProject } from "../../context/ActiveProjectContext";
import {
  HiveShell,
  HivePanel,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveStatusBadge,
  HiveEmptyState,
  HiveToast,
  HiveSkeleton,
} from "../../components/HiveModuleUI";
import HiveApiErrorCard from "../../components/HiveApiErrorCard";
import { formatHiveApiError } from "../../utils/hiveApiErrors";
import { PROJECT_SECTORS, PROJECT_STATUSES, sectorLabel } from "../../config/projectSectors";

const API_PREFIX = "/api/v3/projects";

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso.replace(" UTC", "Z")).toLocaleDateString("tr-TR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function ProjectsList({ onNavigate }) {
  const { activeProjectId, refresh: refreshActive } = useActiveProject();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorInfo, setErrorInfo] = useState(null);
  const [toast, setToast] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [settingActive, setSettingActive] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setErrorInfo(null);
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (statusFilter) params.status = statusFilter;
      if (sectorFilter) params.sector = sectorFilter;
      const res = await API.get(API_PREFIX, { params });
      setProjects(res.data?.projects || []);
    } catch (e) {
      setErrorInfo(formatHiveApiError(e, API_PREFIX));
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, sectorFilter]);

  useEffect(() => {
    const t = setTimeout(load, search ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, search]);

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const filteredCount = useMemo(() => projects.length, [projects]);
  const demoProject = useMemo(
    () => projects.find((p) => p.metadata?.phoenix_demo || p.metadata?.customer_journey_demo),
    [projects],
  );

  const setActive = async (id, name) => {
    setSettingActive(id);
    setErrorInfo(null);
    try {
      await API.post(`${API_PREFIX}/${id}/set-active`);
      window.dispatchEvent(new CustomEvent("hive-active-project-changed"));
      await refreshActive();
      setToast(`"${name}" aktif proje olarak seçildi.`);
    } catch (e) {
      setErrorInfo(formatHiveApiError(e, `${API_PREFIX}/${id}/set-active`));
    } finally {
      setSettingActive("");
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`"${name}" projesini silmek istediğinize emin misiniz?`)) return;
    setErrorInfo(null);
    try {
      await API.delete(`${API_PREFIX}/${id}`);
      setToast(`"${name}" silindi.`);
      await load();
      await refreshActive();
    } catch (e) {
      setErrorInfo(formatHiveApiError(e, `${API_PREFIX}/${id}`));
    }
  };

  return (
    <HiveShell
      title="Projects"
      subtitle="HIVE V3 Project Engine — proje oluştur, yönet ve aktif proje seç"
      actions={(
        <>
          <HiveBtn variant="secondary" size="sm" title="Academy proje rehberi" onClick={() => window.open("/academy", "_blank")}>
            Academy
          </HiveBtn>
          <HiveBtn variant="primary" title="Yeni proje sihirbazını başlat" onClick={() => onNavigate("/projects/new")}>
            + Yeni Proje Oluştur
          </HiveBtn>
        </>
      )}
    >
      {errorInfo && <HiveApiErrorCard errorInfo={errorInfo} />}
      {toast && <HiveToast message={toast} onClose={() => setToast("")} />}

      {demoProject && (
        <HivePanel title="Phoenix Demo" className="hive-project-demo-banner">
          <p style={{ margin: "0 0 8px" }}>
            Customer Journey demo projesi: <strong>{demoProject.name}</strong>
            {demoProject.domain ? ` · ${demoProject.domain}` : ""}
          </p>
          {activeProjectId === demoProject.id ? (
            <HiveStatusBadge status="active" />
          ) : (
            <HiveBtn
              size="sm"
              variant="primary"
              disabled={settingActive === demoProject.id}
              title="Demo projeyi aktif proje yap"
              onClick={() => setActive(demoProject.id, demoProject.name)}
            >
              {settingActive === demoProject.id ? "Seçiliyor…" : "Demo projeyi aktif yap"}
            </HiveBtn>
          )}
        </HivePanel>
      )}

      <HivePanel title="Filtreler">
        <div className="hive-form-grid" style={{ gridTemplateColumns: "2fr 1fr 1fr auto" }}>
          <HiveField label="Ara">
            <HiveInput
              placeholder="Proje adı, domain veya sektör..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              title="Arama"
            />
          </HiveField>
          <HiveField label="Durum">
            <select className="hive-input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} title="Durum filtresi">
              {PROJECT_STATUSES.map((s) => (
                <option key={s.id || "all"} value={s.id}>{s.label}</option>
              ))}
            </select>
          </HiveField>
          <HiveField label="Sektör">
            <select className="hive-input" value={sectorFilter} onChange={(e) => setSectorFilter(e.target.value)} title="Sektör filtresi">
              <option value="">Tümü</option>
              {PROJECT_SECTORS.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </HiveField>
          <div style={{ alignSelf: "end" }}>
            <HiveBtn onClick={load} disabled={loading} title="Listeyi yenile">Yenile</HiveBtn>
          </div>
        </div>
      </HivePanel>

      <div style={{ margin: "12px 0", opacity: 0.75, fontSize: 13 }}>
        {loading ? "Yükleniyor…" : `${filteredCount} proje`}
      </div>

      {loading && <HiveSkeleton lines={5} />}

      {!loading && projects.length === 0 && (
        <HiveEmptyState
          title="Henüz proje yok"
          description="İlk projenizi oluşturmak için sihirbazı başlatın veya Phoenix demo seed script'ini çalıştırın."
          actionLabel="Yeni Proje Oluştur"
          onAction={() => onNavigate("/projects/new")}
        />
      )}

      {!loading && projects.length > 0 && (
        <div className="hive-project-grid">
          {projects.map((p) => {
            const isActive = activeProjectId === p.id;
            return (
              <article
                key={p.id}
                className={`hive-project-card ${isActive ? "hive-project-card--active" : ""}`}
                onClick={() => onNavigate(`/projects/${p.id}`)}
              >
                <div className="hive-project-card-head">
                  <h3 title={p.name}>{p.name}</h3>
                  <HiveStatusBadge status={p.status} />
                </div>
                {isActive && <span className="hive-project-active-pill" title="Aktif proje">Aktif</span>}
                <div className="hive-project-card-meta">
                  <span>{sectorLabel(p.sector)}</span>
                  <span>{p.domain || "—"}</span>
                  {(p.pages_count ?? 0) > 0 && (
                    <span className="hive-project-pages-badge">{p.pages_count} sayfa</span>
                  )}
                </div>
                <div className="hive-project-card-foot">
                  <span>{formatDate(p.created_at)}</span>
                  <div className="hive-project-card-actions" onClick={(e) => e.stopPropagation()}>
                    {!isActive && (
                      <HiveBtn
                        size="sm"
                        variant="outline"
                        disabled={settingActive === p.id}
                        title="Bu projeyi aktif proje yap"
                        onClick={() => setActive(p.id, p.name)}
                      >
                        Aktif yap
                      </HiveBtn>
                    )}
                    <HiveBtn size="sm" title="Proje detayı" onClick={() => onNavigate(`/projects/${p.id}`)}>Aç</HiveBtn>
                    <HiveBtn size="sm" variant="outline" title="Projeyi sil" onClick={() => handleDelete(p.id, p.name)}>Sil</HiveBtn>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </HiveShell>
  );
}
