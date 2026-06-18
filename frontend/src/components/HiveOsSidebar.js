import React, { useState, useMemo, useEffect } from "react";
import { HIVE_OS_DASHBOARD, HIVE_OS_PROJECTS, HIVE_OS_NAV_GROUPS, HIVE_OS_PRIMARY_IDS } from "../config/hiveOsNav";
import { pathFromGosterge } from "../config/hiveOsRoutes";

export default function HiveOsSidebar({
  gosterge,
  arama,
  acikGrup,
  setAcikGrup,
  onNavigate,
  onDashboard,
  onOpenPalette,
  moduller,
  grupluModuller,
  seciliModul,
  onSelectModule,
  blackFlagSection,
  canView,
}) {
  const [meshTab, setMeshTab] = useState(() => sessionStorage.getItem("hive_mesh_tab") || "dashboard");

  useEffect(() => {
    const sync = () => setMeshTab(sessionStorage.getItem("hive_mesh_tab") || "dashboard");
    window.addEventListener("hive-mesh-tab", sync);
    return () => window.removeEventListener("hive-mesh-tab", sync);
  }, []);

  const [openGroups, setOpenGroups] = useState(() => {
    const init = {};
    HIVE_OS_NAV_GROUPS.forEach((g) => {
      init[g.id] = g.defaultOpen !== false;
    });
    init.all_modules = false;
    return init;
  });

  const toggleOsGroup = (id) => {
    setOpenGroups((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const search = arama.toLowerCase().trim();

  const filteredNavGroups = useMemo(() => {
    const visible = HIVE_OS_NAV_GROUPS.map((g) => ({
      ...g,
      items: g.items.filter((item) => (canView ? canView(item.id) : true)),
    })).filter((g) => g.items.length > 0);
    if (!search) return visible;
    return visible.map((g) => ({
      ...g,
      items: g.items.filter(
        (item) =>
          item.label.toLowerCase().includes(search)
          || item.id.includes(search)
          || (item.short || "").toLowerCase().includes(search)
      ),
    })).filter((g) => g.items.length > 0);
  }, [search]);

  const extraModules = useMemo(() => {
    const out = {};
    Object.entries(grupluModuller || {}).forEach(([grupAdi, modulList]) => {
      const filtered = modulList.filter((m) => {
        if (HIVE_OS_PRIMARY_IDS.has(m.id)) return false;
        if (!search) return true;
        return m.ad.toLowerCase().includes(search) || m.aciklama.toLowerCase().includes(search);
      });
      if (filtered.length) out[grupAdi] = filtered;
    });
    return out;
  }, [grupluModuller, search]);

  const isActive = (item) => {
    if (gosterge !== item.id) return false;
    if (item.meshTab) return meshTab === item.meshTab;
    if (item.id === "authority_mesh_engine" && meshTab && meshTab !== "dashboard") {
      return false;
    }
    return true;
  };

  const handleNav = (item) => {
    const opts = item.meshTab ? { meshTab: item.meshTab } : {};
    if (item.meshTab) {
      sessionStorage.setItem("hive_mesh_tab", item.meshTab);
      setMeshTab(item.meshTab);
      window.dispatchEvent(new Event("hive-mesh-tab"));
    }
    onNavigate(item.id, opts);
  };

  const isProjectsActive = gosterge === "projects"
    || gosterge === "project_wizard"
    || (typeof gosterge === "string" && gosterge.startsWith("project_detail:"));

  return (
    <>
      <div className="hive-os-nav hive-os-nav-v3">
        <button
          type="button"
          className={`hive-os-nav-item ${gosterge === HIVE_OS_DASHBOARD.id ? "active" : ""}`}
          onClick={onDashboard}
          title={pathFromGosterge(HIVE_OS_DASHBOARD.id) || "/"}
        >
          <span className="hive-os-nav-icon">{HIVE_OS_DASHBOARD.icon}</span>
          <span className="hive-os-nav-label">{HIVE_OS_DASHBOARD.label}</span>
        </button>

        <button
          type="button"
          className={`hive-os-nav-item hive-os-nav-primary ${isProjectsActive ? "active" : ""}`}
          onClick={() => onNavigate(HIVE_OS_PROJECTS.id)}
          title={pathFromGosterge(HIVE_OS_PROJECTS.id) || "/projects"}
        >
          <span className="hive-os-nav-icon">{HIVE_OS_PROJECTS.icon}</span>
          <span className="hive-os-nav-label">{HIVE_OS_PROJECTS.label}</span>
        </button>

        {onOpenPalette && (
          <button type="button" className="hive-os-nav-cmd" onClick={onOpenPalette}>
            <span>⌘K</span>
            <span>Command Palette</span>
          </button>
        )}

        {filteredNavGroups.map((group) => (
          <div key={group.id} className="hive-os-nav-group">
            <button
              type="button"
              className="hive-os-nav-group-header"
              onClick={() => toggleOsGroup(group.id)}
            >
              <span className="hive-os-nav-chevron">{openGroups[group.id] ? "▼" : "▶"}</span>
              <span>{group.label}</span>
              <span className="hive-os-nav-count">{group.items.length}</span>
            </button>
            {openGroups[group.id] && (
              <div className="hive-os-nav-items">
                {group.items.map((item, idx) => {
                  const route = pathFromGosterge(item.id, item.meshTab ? { meshTab: item.meshTab } : {});
                  return (
                    <button
                      key={`${group.id}-${item.id}-${item.meshTab || idx}`}
                      type="button"
                      className={`hive-os-nav-item ${item.primary ? "hive-os-nav-primary" : ""} ${isActive(item) ? "active" : ""}`}
                      onClick={() => handleNav(item)}
                      title={route || item.id}
                    >
                      <span className="hive-os-nav-icon">{item.icon}</span>
                      <span className="hive-os-nav-label-wrap">
                        <span className="hive-os-nav-label">{item.label}</span>
                        {item.short && item.short !== item.label && (
                          <span className="hive-os-nav-short">{item.short}</span>
                        )}
                      </span>
                      {item.primary && <span className="hive-os-nav-dot" aria-hidden />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ))}

        {Object.keys(extraModules).length > 0 && (
          <div className="hive-os-nav-group hive-os-nav-all">
            <button
              type="button"
              className="hive-os-nav-group-header"
              onClick={() => toggleOsGroup("all_modules")}
            >
              <span className="hive-os-nav-chevron">{openGroups.all_modules ? "▼" : "▶"}</span>
              <span>ALL MODULES</span>
              <span className="hive-os-nav-count">{moduller?.length ?? 0}</span>
            </button>
            {openGroups.all_modules && (
              <div className="modul-liste hive-os-modul-liste">
                {Object.entries(extraModules).map(([grupAdi, modulList]) => {
                  const isOpen = acikGrup === grupAdi;
                  return (
                    <div key={grupAdi}>
                      <div
                        className="grup-header"
                        onClick={() => setAcikGrup(acikGrup === grupAdi ? null : grupAdi)}
                        role="button"
                        tabIndex={0}
                      >
                        <span className="grup-ok">{isOpen ? "▼" : "▶"}</span>
                        <span className="grup-isim">{grupAdi}</span>
                        <span className="grup-sayi">{modulList.length}</span>
                      </div>
                      {isOpen && modulList.map((mod) => (
                        <div
                          key={mod.id}
                          className={`modul-item ${seciliModul?.id === mod.id ? "active" : ""}`}
                          onClick={() => onSelectModule(mod)}
                          role="button"
                          tabIndex={0}
                        >
                          <div className="dot active-dot" />
                          <div className="info">
                            <div className="isim">{mod.ad}</div>
                            <div className="aciklama">{mod.aciklama}</div>
                          </div>
                          <span className="aktif-badge">aktif</span>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {blackFlagSection}
    </>
  );
}
