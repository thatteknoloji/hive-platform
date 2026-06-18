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

  return (
    <HiveShell
      title="🎯 Talon"
      subtitle="Hiper-lokal anahtar kelime avcısı + merkezi SEO karar motoru — intent, sayfa tipi, GEO cluster, rakip analizi ve içerik brief"
    >
      <HiveToolbar>
        <span className={`hm-badge hm-badge-${v2Active ? "low" : "high"}`} style={{ alignSelf: "center" }}>
          V2 Stack: {v2Active ? "aktif" : "eksik"}
        </span>
        <span className={`hm-badge hm-badge-${orchReady ? "low" : "medium"}`} style={{ alignSelf: "center" }}>
          Orchestrator: {orchReady ? "hazır" : "kısıtlı"}
        </span>
        <HiveBtn variant="secondary" onClick={() => setTab("keywords")}>Kelime Üret</HiveBtn>
        <HiveBtn variant="secondary" onClick={() => setTab("orchestrator")}>Full Research</HiveBtn>
        <HiveBtn variant="ghost" onClick={openSettings}>API Ayarları</HiveBtn>
        <HiveBtn variant="ghost" onClick={refreshDashboard}>Yenile</HiveBtn>
      </HiveToolbar>

      {error && <HiveAlert type="err">{error}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <HivePanel>
          <HiveStatGrid items={[
            ["V2 Provider", v2Active ? "Aktif" : "Eksik"],
            ["Orchestrator", orchReady ? "Hazır" : "Kısıtlı"],
            ["Stack", talonHealth?.stack || talonStatus.stack?.ad || "—"],
            ["Geçmiş", talonHealth?.gecmis_count ?? "—"],
          ]} />

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
            <HiveCard title="Search Provider'lar" meta="Anahtar kelime avcısı">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {providerChips.map(({ key, label, ok }) => (
                  <span key={key} className={`hm-badge hm-badge-${ok ? "low" : "medium"}`}>
                    {label}: {ok ? "✓" : "—"}
                  </span>
                ))}
              </div>
            </HiveCard>
            <HiveCard title="Orchestrator Provider'lar" meta="Intent · GEO · brief">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {Object.entries(orchProviders).length === 0 ? (
                  <span className="hm-empty">Veri yok</span>
                ) : (
                  Object.entries(orchProviders).map(([name, status]) => (
                    <span
                      key={name}
                      className={`hm-badge hm-badge-${status === "configured" || status === "available" ? "low" : "medium"}`}
                    >
                      {name}: {status}
                    </span>
                  ))
                )}
              </div>
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
