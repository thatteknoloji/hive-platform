import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import Talon from "./Talon";
import TalonOrchestrator from "./TalonOrchestrator";
import {
  HiveShell,
  HiveAlert,
  HiveToolbar,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveBtn,
  HiveCard,
  HiveSkeleton,
  HiveEmptyState,
  HiveTooltip,
  HiveToast,
} from "../components/HiveModuleUI";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "keywords", label: "Anahtar Kelime Avcısı" },
  { id: "orchestrator", label: "Orchestrator" },
];

const PROVIDER_LABELS = {
  searxng: "SearXNG",
  tavily: "Tavily",
  exa: "Exa",
  autocomplete: "Autocomplete",
  openstreetmap: "OpenStreetMap",
  openrouter: "OpenRouter",
  ollama: "Ollama",
};

export default function TalonHub({
  onNavigateToSSS,
  onNavigateAstro,
  onNavigatePageHub,
  onNavigateSSS,
}) {
  const [tab, setTab] = useState(() => sessionStorage.getItem("talon_hub_tab") || "dashboard");
  const [talonHealth, setTalonHealth] = useState(null);
  const [talonStatus, setTalonStatus] = useState({});
  const [orchHealth, setOrchHealth] = useState(null);
  const [settingsPulse, setSettingsPulse] = useState(0);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);

  const refreshDashboard = useCallback(async () => {
    try {
      const [healthRes, statusRes, orchRes] = await Promise.all([
        API.get("/api/talon/health"),
        API.get("/api/talon/status"),
        API.get("/api/talon/orchestrator/health"),
      ]);
      setTalonHealth(healthRes.data);
      setTalonStatus(statusRes.data.api || {});
      setOrchHealth(orchRes.data);
      setError("");
    } catch (e) {
      setError(e.hiveMessage || e.message || "Talon durumu alınamadı");
    } finally {
      setInitialLoading(false);
    }
  }, []);

  useEffect(() => { refreshDashboard(); }, [refreshDashboard]);

  useEffect(() => {
    sessionStorage.setItem("talon_hub_tab", tab);
  }, [tab]);

  const v2Active = Boolean(
    talonStatus.stack?.var || talonStatus.searxng?.var || talonStatus.tavily?.var || talonStatus.exa?.var
  );

  const openSettings = () => {
    setTab("keywords");
    setSettingsPulse((n) => n + 1);
  };

  const providerChips = Object.entries(PROVIDER_LABELS).map(([key, label]) => {
    const svc = talonStatus[key];
    const ok = svc?.var || svc === "configured" || svc === "available";
    return { key, label, ok };
  });

  const orchProviders = orchHealth?.providers || {};
  const orchReady = orchHealth?.ready;

  const allProvidersConfigured = providerChips.some((p) => p.ok);
  const hasAnyData = talonHealth || Object.keys(talonStatus).length > 0;

  if (initialLoading) {
    return (
      <HiveShell
        title="🎯 Talon"
        subtitle="Hiper-lokal anahtar kelime avcısı + merkezi SEO karar motoru"
      >
        <HiveSkeleton lines={6} />
      </HiveShell>
    );
  }

  return (
    <HiveShell
      title="🎯 Talon"
      subtitle="Hiper-lokal anahtar kelime avcısı + merkezi SEO karar motoru — intent, sayfa tipi, GEO cluster, rakip analizi ve içerik brief"
    >
      <HiveToolbar>
        <HiveTooltip content={v2Active ? "V2 Stack aktif — keyword araştırması kullanılabilir" : "Hiçbir V2 provider yapılandırılmamış — API ayarlarından ekleyin"}>
          <span className={`hm-badge hm-badge-${v2Active ? "low" : "high"}`} style={{ alignSelf: "center" }}>
            V2 Stack: {v2Active ? "aktif" : "eksik"}
          </span>
        </HiveTooltip>
        <HiveTooltip content={orchReady ? "Orchestrator hazır — intent, GEO ve rakip analizi çalışabilir" : "Orchestrator kısıtlı — API provider'ları kontrol edin"}>
          <span className={`hm-badge hm-badge-${orchReady ? "low" : "medium"}`} style={{ alignSelf: "center" }}>
            Orchestrator: {orchReady ? "hazır" : "kısıtlı"}
          </span>
        </HiveTooltip>
        <HiveBtn variant="secondary" onClick={() => setTab("keywords")}>Kelime Üret</HiveBtn>
        <HiveBtn variant="secondary" onClick={() => setTab("orchestrator")}>Full Research</HiveBtn>
        <HiveBtn variant="ghost" onClick={openSettings}>API Ayarları</HiveBtn>
        <HiveBtn variant="ghost" onClick={refreshDashboard}>Yenile</HiveBtn>
      </HiveToolbar>

      {error && <HiveAlert variant="error">{error}</HiveAlert>}
      {toast && <HiveToast message={toast} onClose={() => setToast("")} />}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <HivePanel>
          {!hasAnyData ? (
            <HiveEmptyState
              title="Talon bağlantısı kurulamamış"
              message="Talon API'ye bağlanamadı. Backend'in çalıştığından ve provider ayarlarının yapıldığından emin olun. API Ayarları butonundan V2 Stack provider'larını (SearXNG, Tavily, Exa) yapılandırabilirsiniz."
            />
          ) : (
            <>
              <HiveStatGrid items={[
                ["V2 Provider", v2Active ? "Aktif" : "Eksik"],
                ["Orchestrator", orchReady ? "Hazır" : "Kısıtlı"],
                ["Stack", talonHealth?.stack || talonStatus.stack?.ad || "—"],
                ["Geçmiş", talonHealth?.gecmis_count ?? "—"],
              ]} />

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
                <HiveCard title="Search Provider'lar" meta="Anahtar kelime avcısı">
                  {!allProvidersConfigured ? (
                    <HiveEmptyState title="Provider yok" message="API Ayarları'ndan SearXNG, Tavily veya Exa ekleyin." />
                  ) : (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {providerChips.map(({ key, label, ok }) => (
                        <HiveTooltip key={key} content={ok ? `${label} yapılandırılmış` : `${label} yapılandırılmamış`}>
                          <span className={`hm-badge hm-badge-${ok ? "low" : "medium"}`}>
                            {label}: {ok ? "✓" : "—"}
                          </span>
                        </HiveTooltip>
                      ))}
                    </div>
                  )}
                </HiveCard>
                <HiveCard title="Orchestrator Provider'lar" meta="Intent · GEO · brief">
                  {Object.entries(orchProviders).length === 0 ? (
                    <HiveEmptyState title="Provider yok" message="OpenRouter veya Ollama yapılandırması gerekiyor." />
                  ) : (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {Object.entries(orchProviders).map(([name, status]) => (
                        <HiveTooltip key={name} content={`${name}: ${status}`}>
                          <span className={`hm-badge hm-badge-${status === "configured" || status === "available" ? "low" : "medium"}`}>
                            {name}: {status}
                          </span>
                        </HiveTooltip>
                      ))}
                    </div>
                  )}
                </HiveCard>
                <HiveCard title="Hızlı Başlangıç">
                  <HiveToolbar>
                    <HiveBtn onClick={() => setTab("keywords")}>Anahtar Kelime Üret</HiveBtn>
                    <HiveBtn variant="secondary" onClick={() => setTab("orchestrator")}>Orchestrator Araştırması</HiveBtn>
                    {onNavigateToSSS && (
                      <HiveBtn variant="ghost" onClick={() => onNavigateToSSS({})}>SSS Zinciri</HiveBtn>
                    )}
                  </HiveToolbar>
                </HiveCard>
              </div>
            </>
          )}
        </HivePanel>
      )}

      {tab === "keywords" && (
        <HivePanel className="talon-hub-keywords">
          <Talon
            embedded
            settingsPulse={settingsPulse}
            onNavigateToSSS={onNavigateToSSS || onNavigateSSS}
          />
        </HivePanel>
      )}

      {tab === "orchestrator" && (
        <HivePanel>
          <TalonOrchestrator
            embedded
            onNavigateAstro={onNavigateAstro}
            onNavigatePageHub={onNavigatePageHub}
            onNavigateSSS={onNavigateSSS || onNavigateToSSS}
          />
        </HivePanel>
      )}
    </HiveShell>
  );
}
