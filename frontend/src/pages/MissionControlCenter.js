import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { HiveShell, HiveAlert } from "../components/HiveModuleUI";
import { HiveWarRoom } from "../components/HiveWarRoom";
import { HiveStickyActionBar } from "../components/HiveStickyActionBar";
import { NextBestActionsPanel } from "../components/HiveOSComponents";
import HiveApiErrorCard from "../components/HiveApiErrorCard";
import { formatMissionControlApiError } from "../utils/missionControlErrors";

const API_PREFIX = "/api/mission-control";
const POLL_MS = 90000;

export default function MissionControlCenter({ onNavigate, onOpenPalette }) {
  const [dash, setDash] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const go = useCallback((link) => {
    if (link && onNavigate) onNavigate(link);
  }, [onNavigate]);

  const refresh = useCallback(async (silent = false, full = false) => {
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
  }, []);

  useEffect(() => { refresh(false); }, [refresh]);

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
      <HiveWarRoom
        dash={dash}
        loading={loading}
        onNavigate={go}
        onRefresh={() => refresh()}
        onLoadFull={() => refresh(false, true)}
        onOpenPalette={onOpenPalette}
      />

      <HiveShell title="" subtitle="">
        {error && <HiveApiErrorCard errorInfo={error} />}
        {message && <HiveAlert type="success">{message}</HiveAlert>}

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
    </div>
  );
}
