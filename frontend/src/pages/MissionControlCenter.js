import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useActiveProject } from "../context/ActiveProjectContext";
import { HiveShell, HiveAlert, HiveBtn, HiveToast, HiveSkeleton } from "../components/HiveModuleUI";
import CustomerJourneyCard from "../components/CustomerJourneyCard";
import { HiveWarRoom } from "../components/HiveWarRoom";
import { HiveStickyActionBar } from "../components/HiveStickyActionBar";
import { NextBestActionsPanel, ReleaseReadinessPanel } from "../components/HiveOSComponents";
import HiveApiErrorCard from "../components/HiveApiErrorCard";
import { formatMissionControlApiError } from "../utils/missionControlErrors";

const API_PREFIX = "/api/mission-control";
const POLL_MS = 90000;

export default function MissionControlCenter({ onNavigate, onOpenPalette }) {
  const { activeProjectId, loading: projectLoading } = useActiveProject();
  const [dash, setDash] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [journey, setJourney] = useState(null);

  const go = useCallback((link) => {
    if (link && onNavigate) onNavigate(link);
  }, [onNavigate]);

  const refresh = useCallback(async (silent = false, full = false) => {
    if (!activeProjectId) {
      setDash({ empty: true, message: "Aktif proje seçilmedi — üst menüden veya Projects ekranından proje seçin." });
      setLoading(false);
      setError("");
      return;
    }
    if (!silent) setLoading(true);
    setError("");
    try {
      const path = full ? `${API_PREFIX}/dashboard-full` : `${API_PREFIX}/dashboard`;
      const d = await API.get(path);
      setDash(d.data);
    } catch (err) {
      setError(formatMissionControlApiError(err, `${API_PREFIX}/dashboard`));
    } finally {
      if (!silent) setLoading(false);
    }
  }, [activeProjectId]);

  useEffect(() => { refresh(false); }, [refresh, activeProjectId]);

  const loadJourney = useCallback(async () => {
    try {
      const res = await API.get("/api/phoenix/customer-journey");
      setJourney(res.data);
    } catch {
      setJourney(null);
    }
  }, []);

  useEffect(() => { loadJourney(); }, [loadJourney, activeProjectId]);

  useEffect(() => {
    if (dash) {
      window.dispatchEvent(new CustomEvent("hive-os-palette-context", { detail: dash }));
    }
  }, [dash]);

  useEffect(() => {
    const onRefreshEvent = () => refresh(false);
    window.addEventListener("hive-war-room-refresh", onRefreshEvent);
    return () => window.removeEventListener("hive-war-room-refresh", onRefreshEvent);
  }, [refresh]);

  useEffect(() => {
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
      refresh(true);
    }, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const ackAction = async (actionId) => {
    try {
      await API.post(`${API_PREFIX}/action/${actionId}/ack`);
      setMessage(`Aksiyon onaylandı: ${actionId}`);
      await refresh(true);
    } catch (err) {
      setError(formatMissionControlApiError(err, `${API_PREFIX}/action/${actionId}/ack`));
    }
  };

  const doneAction = async (actionId) => {
    try {
      await API.post(`${API_PREFIX}/action/${actionId}/done`);
      setMessage(`Aksiyon tamamlandı: ${actionId}`);
      await refresh(true);
    } catch (err) {
      setError(formatMissionControlApiError(err, `${API_PREFIX}/action/${actionId}/done`));
    }
  };

  return (
    <div className="hive-module hive-os-command-center hive-war-room-shell">
      {!projectLoading && !activeProjectId ? (
        <HiveShell title="Mission Control" subtitle="Aktif proje yok">
          <CustomerJourneyCard journey={journey} onNavigate={go} />
          <HiveAlert type="info">
            Dashboard görmek için üst menüden bir proje seçin veya Projects ekranından yeni proje oluşturun.
          </HiveAlert>
          <HiveBtn onClick={() => onNavigate?.("projects")}>Projects&apos;e git</HiveBtn>
        </HiveShell>
      ) : (
        <>
      <HiveWarRoom
        dash={dash}
        loading={loading}
        onNavigate={go}
        onRefresh={() => refresh()}
        onLoadFull={() => refresh(false, true)}
        onOpenPalette={onOpenPalette}
      />

      <HiveShell title="" subtitle="">
        {loading && !dash && <HiveSkeleton lines={6} />}
        <CustomerJourneyCard journey={journey} onNavigate={go} />
        <ReleaseReadinessPanel release={dash?.release_readiness} onNavigate={go} />
        {error && <HiveApiErrorCard errorInfo={error} />}
        <HiveToast message={message} onClose={() => setMessage("")} />

        <NextBestActionsPanel
          actions={dash?.next_best_actions}
          onNavigate={go}
          onAck={ackAction}
          onDone={doneAction}
        />
      </HiveShell>

      <HiveStickyActionBar
        hint="Quick ops"
        actions={[
          { id: "cmd", label: "Command", icon: "⌘", shortcut: "⌘K", onClick: () => onOpenPalette?.() },
          { id: "mesh", label: "Authority", onClick: () => go("authority_mesh_engine") },
          { id: "camp", label: "Campaigns", onClick: () => go("campaign_engine") },
          { id: "serp", label: "SERP Defense", onClick: () => go("serp_defense_engine") },
          { id: "rev", label: "Revenue", onClick: () => go("revenue_lead_engine") },
          { id: "brain", label: "Brain", onClick: () => go("hive_brain_engine") },
          { id: "pub", label: "Publisher", onClick: () => go("publisher_hub") },
          { id: "prov", label: "Providers", onClick: () => go("provider_control_center") },
          { id: "refresh", label: "Refresh", onClick: () => refresh() },
        ]}
      />
        </>
      )}
    </div>
  );
}
