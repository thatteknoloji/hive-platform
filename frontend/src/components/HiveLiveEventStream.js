import React, { memo, useMemo } from "react";
import { HiveStatusPill } from "./HiveWarRoom";

const MODULE_ROUTES = {
  serp_defense_engine: "serp_defense_engine",
  campaign_engine: "campaign_engine",
  authority_mesh_engine: "authority_mesh_engine",
  publisher_hub: "publisher_hub",
  revenue_lead_engine: "revenue_lead_engine",
  hive_brain_engine: "hive_brain_engine",
  mission_control_center: "mission_control_center",
};

function moduleRoute(mod) {
  if (!mod) return "hive_brain_engine";
  if (MODULE_ROUTES[mod]) return mod;
  const key = Object.keys(MODULE_ROUTES).find((k) => mod.includes(k.replace(/_engine$/, "")));
  return key || "hive_brain_engine";
}
function formatTime(ts) {
  if (!ts) return "--:--";
  const raw = String(ts).replace(" UTC", "Z").replace(" ", "T");
  const d = new Date(raw);
  if (!Number.isNaN(d.getTime())) {
    return d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  return String(ts).slice(11, 19) || "--:--";
}

function inferSeverity(ev) {
  const blob = `${ev.severity || ""} ${ev.level || ""} ${ev.event_type || ""} ${ev.type || ""} ${ev.status || ""} ${ev.reason || ""}`.toLowerCase();
  if (blob.includes("critical") || blob.includes("error") || blob.includes("fail") || blob.includes("threat")) return "critical";
  if (blob.includes("warn") || blob.includes("degraded") || blob.includes("risk")) return "warning";
  if (blob.includes("success") || blob.includes("complete") || blob.includes("publish") || blob.includes("won") || blob.includes("convert")) return "success";
  return "info";
}

function inferMessage(ev) {
  if (ev.reason) return String(ev.reason).slice(0, 90);
  if (ev.summary) return String(ev.summary).slice(0, 90);
  if (ev.message) return String(ev.message).slice(0, 90);
  const type = (ev.event_type || ev.type || "").replace(/_/g, " ");
  const mod = (ev.module || "").replace(/_/g, " ");
  return type || mod || "System event";
}

export const HiveLiveEventStream = memo(function HiveLiveEventStream({
  events = [],
  onNavigate,
  title = "Live Event Stream",
}) {
  const rows = useMemo(() => {
    return (events || []).slice(0, 24).map((ev, i) => ({
      id: ev.id || ev.event_id || `ev-${i}`,
      time: formatTime(ev.timestamp || ev.at),
      module: (ev.module || "system").replace(/_/g, " "),
      message: inferMessage(ev),
      severity: inferSeverity(ev),
      link: moduleRoute(ev.module),
    }));
  }, [events]);

  const go = (link) => {
    if (link && onNavigate) onNavigate(link);
  };

  return (
    <footer className="hive-war-stream hive-live-stream">
      <header className="hive-war-stream-head">
        <div className="hive-live-stream-title">
          <span className="hive-live-pulse" aria-hidden />
          <span>{title}</span>
        </div>
        <div className="hive-live-legend">
          <HiveStatusPill label="critical" tone="danger" size="xs" />
          <HiveStatusPill label="warning" tone="warning" size="xs" />
          <HiveStatusPill label="info" tone="neutral" size="xs" />
          <HiveStatusPill label="success" tone="success" size="xs" />
        </div>
      </header>
      <div className="hive-live-stream-viewport">
        <div className={`hive-live-stream-track ${rows.length > 4 ? "animate" : ""}`}>
          {rows.length === 0 ? (
            <p className="hive-war-empty">Olay akışı boş — modüller çalıştıkça canlı akar</p>
          ) : (
            <>
              {rows.map((ev) => (
                <button
                  key={ev.id}
                  type="button"
                  className={`hive-war-event hive-live-event sev-${ev.severity}`}
                  onClick={() => go(ev.link)}
                >
                  <HiveStatusPill label={ev.severity} tone={
                    ev.severity === "critical" ? "danger"
                      : ev.severity === "warning" ? "warning"
                        : ev.severity === "success" ? "success" : "neutral"
                  } size="xs" />
                  <time>{ev.time}</time>
                  <span className="hive-war-event-module">{ev.module}</span>
                  <span className="hive-war-event-msg">{ev.message}</span>
                </button>
              ))}
              {rows.length > 4 && rows.map((ev) => (
                <button
                  key={`dup-${ev.id}`}
                  type="button"
                  className={`hive-war-event hive-live-event sev-${ev.severity}`}
                  onClick={() => go(ev.link)}
                  aria-hidden
                  tabIndex={-1}
                >
                  <HiveStatusPill label={ev.severity} tone={
                    ev.severity === "critical" ? "danger"
                      : ev.severity === "warning" ? "warning"
                        : ev.severity === "success" ? "success" : "neutral"
                  } size="xs" />
                  <time>{ev.time}</time>
                  <span className="hive-war-event-module">{ev.module}</span>
                  <span className="hive-war-event-msg">{ev.message}</span>
                </button>
              ))}
            </>
          )}
        </div>
      </div>
    </footer>
  );
});
