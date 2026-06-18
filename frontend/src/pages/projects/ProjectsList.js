import React, { useCallback, useEffect, useMemo, useState } from "react";
import API from "../../api";
import {
  HiveShell,
  HiveAlert,
  HivePanel,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveStatusBadge,
} from "../../components/HiveModuleUI";
import { PROJECT_SECTORS, PROJECT_STATUSES, sectorLabel } from "../../config/projectSectors";

const API_PREFIX = "/api/v3/projects";

function apiError(e) {
  return e?.response?.data?.detail || e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

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
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (statusFilter) params.status = statusFilter;
      if (sectorFilter) params.sector = sectorFilter;
      const res = await API.get(API_PREFIX, { params });
      setProjects(res.data?.projects || []);
    } catch (e) {
      setError(apiError(e));
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, sectorFilter]);

  useEffect(() => {
    const t = setTimeout(load, search ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, search]);

  const filteredCount = useMemo(() => projects.length, [projects]);

  const handleDelete = async (id, name) => {
    if (!window.confirm(`"${name}" projesini silmek istediğinize emin misiniz?`)) return;
    try {
      await API.delete(`${API_PREFIX}/${id}`);
      load();
    } catch (e) {
      setError(apiError(e));
    }
  };

  return (
    <HiveShell
      title="Projects"
      subtitle="HIVE V3 Project Engine — proje oluştur, yönet ve izle"
      actions={(
        <HiveBtn variant="primary" onClick={() => onNavigate("/projects/new")}>
          + Yeni Proje Oluştur
        </HiveBtn>
      )}
    >
      {error && <HiveAlert type="error">{error}</HiveAlert>}

      <HivePanel title="Filtreler">
        <div className="hive-form-grid" style={{ gridTemplateColumns: "2fr 1fr 1fr auto" }}>
          <HiveField label="Ara">
            <HiveInput
              placeholder="Proje adı, domain veya sektör..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </HiveField>
          <HiveField label="Durum">
            <select className="hive-input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              {PROJECT_STATUSES.map((s) => (
                <option key={s.id || "all"} value={s.id}>{s.label}</option>
              ))}
            </select>
          </HiveField>
          <HiveField label="Sektör">
            <select className="hive-input" value={sectorFilter} onChange={(e) => setSectorFilter(e.target.value)}>
              <option value="">Tümü</option>
              {PROJECT_SECTORS.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </HiveField>
          <div style={{ alignSelf: "end" }}>
            <HiveBtn onClick={load} disabled={loading}>Yenile</HiveBtn>
          </div>
        </div>
      </HivePanel>

      <div style={{ margin: "12px 0", opacity: 0.75, fontSize: 13 }}>
        {loading ? "Yükleniyor..." : `${filteredCount} proje`}
      </div>

      {!loading && projects.length === 0 && (
        <HivePanel>
          <p style={{ margin: 0 }}>Henüz proje yok. İlk projenizi oluşturmak için sihirbazı başlatın.</p>
          <div style={{ marginTop: 12 }}>
            <HiveBtn variant="primary" onClick={() => onNavigate("/projects/new")}>
              Yeni Proje Oluştur
            </HiveBtn>
          </div>
        </HivePanel>
      )}

      <div className="hive-project-grid">
        {projects.map((p) => (
          <article key={p.id} className="hive-project-card" onClick={() => onNavigate(`/projects/${p.id}`)}>
            <div className="hive-project-card-head">
              <h3>{p.name}</h3>
              <HiveStatusBadge status={p.status} />
            </div>
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
                <HiveBtn size="sm" onClick={() => onNavigate(`/projects/${p.id}`)}>Aç</HiveBtn>
                <HiveBtn size="sm" variant="outline" onClick={() => handleDelete(p.id, p.name)}>Sil</HiveBtn>
              </div>
            </div>
          </article>
        ))}
      </div>
    </HiveShell>
  );
}
