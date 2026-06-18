import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { flattenNavItems, HIVE_OS_QUICK_ACTIONS, buildPaletteContextItems } from "../config/hiveOsNav";
import { pathFromGosterge } from "../config/hiveOsRoutes";

const RECENT_KEY = "hive_cmd_recent_v2";
const MAX_RECENT = 8;

function loadRecent() {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRecent(id) {
  if (!id || id.startsWith("action:") || id.startsWith("ctx:")) return;
  const prev = loadRecent().filter((x) => x !== id);
  prev.unshift(id);
  localStorage.setItem(RECENT_KEY, JSON.stringify(prev.slice(0, MAX_RECENT)));
}

function scoreMatch(query, item) {
  const q = query.trim().toLowerCase();
  if (!q) return 1;
  const label = (item.label || "").toLowerCase();
  const id = (item.id || "").toLowerCase();
  const hint = (item.hint || "").toLowerCase();
  if (label === q || id === q) return 100;
  if (label.startsWith(q) || id.startsWith(q)) return 80;
  if (label.includes(q) || id.includes(q) || hint.includes(q)) return 60;
  const keys = (item.keys || []).join(" ");
  if (keys.includes(q)) return 50;
  const words = q.split(/\s+/).filter(Boolean);
  const hit = words.filter((w) => label.includes(w) || keys.includes(w) || hint.includes(w)).length;
  return hit * 15;
}

function parseIntent(query) {
  const q = query.trim().toLowerCase();
  if (!q) return null;
  const openMatch = q.match(/^open\s+(.+)$/);
  if (openMatch) return { type: "open", target: openMatch[1].trim() };
  const campaignMatch = q.match(/^campaign\s+(.+)$/);
  if (campaignMatch) return { type: "campaign", target: campaignMatch[1].trim() };
  const searchBrain = q.match(/^search\s+brain\s*(.*)$/);
  if (searchBrain) return { type: "brain", target: searchBrain[1].trim() };
  const searchEvents = q.match(/^search\s+events?\s*(.*)$/);
  if (searchEvents) return { type: "events", target: searchEvents[1].trim() };
  const searchProviders = q.match(/^search\s+providers?\s*(.*)$/);
  if (searchProviders) return { type: "providers", target: searchProviders[1].trim() };
  const searchRevenue = q.match(/^search\s+revenue\s*(.*)$/);
  if (searchRevenue) return { type: "revenue", target: searchRevenue[1].trim() };
  return null;
}

export default function HiveCommandPalette({ open, onClose, onNavigate, onAction, getContext }) {
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const [recentIds, setRecentIds] = useState(loadRecent);
  const [contextVersion, setContextVersion] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    const onCtx = () => setContextVersion((v) => v + 1);
    window.addEventListener("hive-os-palette-context", onCtx);
    return () => window.removeEventListener("hive-os-palette-context", onCtx);
  }, []);

  const contextItems = useMemo(() => {
    const dash = getContext?.() || null;
    return buildPaletteContextItems(dash);
  }, [getContext, contextVersion, open]);

  const allItems = useMemo(() => {
    const nav = flattenNavItems();
    const actions = HIVE_OS_QUICK_ACTIONS.map((a) => ({ ...a, isAction: Boolean(!a.navId), isQuick: true }));
    return [...actions, ...contextItems, ...nav];
  }, [contextItems]);

  const recentItems = useMemo(() => {
    const map = new Map(allItems.map((i) => [i.id, i]));
    return recentIds.map((id) => map.get(id)).filter(Boolean);
  }, [allItems, recentIds]);

  const filtered = useMemo(() => {
    const q = query.trim();
    const intent = parseIntent(q);

    if (!q) {
      const recentSet = new Set(recentItems.map((r) => r.id));
      const quick = HIVE_OS_QUICK_ACTIONS.map((a) => ({ ...a, isAction: Boolean(!a.navId), isQuick: true }));
      const ctx = contextItems.slice(0, 6);
      const rest = allItems.filter((i) => !recentSet.has(i.id) && !i.isQuick && !i.id?.startsWith("ctx:"));
      return [...quick, ...ctx, ...recentItems, ...rest.slice(0, 20)];
    }

    let list = allItems
      .map((item) => ({ item, score: scoreMatch(q, item) }))
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ item }) => item);

    if (intent?.type === "open") {
      const t = intent.target;
      list = allItems
        .filter((i) => !i.isAction && i.id !== "dashboard")
        .map((item) => {
          let bonus = 0;
          const blob = `${item.label} ${item.id} ${(item.keys || []).join(" ")}`.toLowerCase();
          if (blob.includes(t)) bonus = 40;
          return { item, score: scoreMatch(q, item) + bonus };
        })
        .filter(({ score }) => score > 0)
        .sort((a, b) => b.score - a.score)
        .map(({ item }) => item);
    }

    return list.slice(0, 24);
  }, [query, allItems, recentItems, contextItems]);

  const grouped = useMemo(() => {
    if (query.trim()) return [{ label: "Results", items: filtered }];
    const groups = {};
    filtered.forEach((item) => {
      let g = "Modules";
      if (item.isQuick) g = "Quick Actions";
      else if (item.id?.startsWith("ctx:")) g = item.group || "Context";
      else if (item.isAction) g = "Actions";
      else g = item.group || "Modules";
      if (!groups[g]) groups[g] = [];
      groups[g].push(item);
    });
    const order = [
      "Quick Actions", "Open Campaign", "Open Keyword", "Open Domain",
      "Search Events", "Search Providers", "Home", "COMMAND", "SEO CORE",
      "CONTENT", "NETWORK", "WORKERS", "LEARN", "TOOLS", "Modules",
    ];
    return Object.entries(groups)
      .sort(([a], [b]) => {
        const ia = order.indexOf(a);
        const ib = order.indexOf(b);
        return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
      })
      .map(([label, items]) => ({ label, items }));
  }, [filtered, query]);

  const flatList = useMemo(() => grouped.flatMap((g) => g.items), [grouped]);

  const run = useCallback(
    (cmd) => {
      if (!cmd) return;
      const intent = parseIntent(query);

      if (intent?.type === "brain" && intent.target) {
        try { sessionStorage.setItem("hive_brain_search", intent.target); } catch { /* ignore */ }
        saveRecent("hive_brain_engine");
        onNavigate?.("hive_brain_engine");
        onClose?.();
        setQuery("");
        return;
      }
      if (intent?.type === "events" && intent.target) {
        try { sessionStorage.setItem("hive_brain_search", intent.target); } catch { /* ignore */ }
        onNavigate?.("hive_brain_engine");
        onClose?.();
        setQuery("");
        return;
      }
      if (intent?.type === "campaign" && intent.target) {
        try { sessionStorage.setItem("hive_campaign_search", intent.target); } catch { /* ignore */ }
        onNavigate?.("campaign_engine");
        onClose?.();
        setQuery("");
        return;
      }
      if (intent?.type === "revenue") {
        onNavigate?.("revenue_lead_engine");
        onClose?.();
        setQuery("");
        return;
      }
      if (intent?.type === "providers") {
        onNavigate?.("provider_control_center");
        onClose?.();
        setQuery("");
        return;
      }

      if (cmd.navId && (cmd.isQuick || cmd.id?.startsWith("ctx:"))) {
        if (cmd.hint) {
          try {
            if (cmd.group === "Open Campaign") sessionStorage.setItem("hive_campaign_search", cmd.hint);
            if (cmd.group?.includes("Event")) sessionStorage.setItem("hive_brain_search", cmd.hint);
          } catch { /* ignore */ }
        }
        saveRecent(cmd.navId);
        onNavigate?.(cmd.navId, cmd.meshTab ? { meshTab: cmd.meshTab } : {});
        onClose?.();
        setQuery("");
        return;
      }

      if (cmd.isAction || cmd.id?.startsWith("action:")) {
        if (cmd.navId) {
          saveRecent(cmd.navId);
          onNavigate?.(cmd.navId);
          onClose?.();
        } else {
          onAction?.(cmd.id);
          if (cmd.id !== "action:open-palette") onClose?.();
        }
      } else {
        const opts = cmd.meshTab ? { meshTab: cmd.meshTab } : {};
        saveRecent(cmd.id);
        setRecentIds(loadRecent());
        onNavigate?.(cmd.id, opts);
        onClose?.();
      }
      setQuery("");
      setActiveIdx(0);
    },
    [onNavigate, onAction, onClose, query]
  );

  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIdx(0);
      setRecentIds(loadRecent());
      setContextVersion((v) => v + 1);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose?.();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, flatList.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && flatList[activeIdx]) {
        e.preventDefault();
        run(flatList[activeIdx]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, flatList, activeIdx, run, onClose]);

  if (!open) return null;

  let rowIdx = -1;

  return (
    <div className="hive-cmd-overlay hive-cmd-v2" role="dialog" aria-modal="true" aria-label="Command palette">
      <button type="button" className="hive-cmd-backdrop" onClick={onClose} aria-label="Kapat" />
      <div className="hive-cmd-panel">
        <div className="hive-cmd-input-wrap">
          <span className="hive-cmd-icon">⌘</span>
          <input
            ref={inputRef}
            className="hive-cmd-input"
            placeholder="Modül, campaign kuşadası, open authority mesh, search brain…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIdx(0);
            }}
          />
          <kbd className="hive-cmd-kbd">esc</kbd>
        </div>

        <div className="hive-cmd-hints">
          <span>open module</span>
          <span>campaign keyword</span>
          <span>search brain</span>
          <span>search events</span>
        </div>

        <div className="hive-cmd-list hive-cmd-list-v2">
          {flatList.length === 0 ? (
            <p className="hive-cmd-empty">Sonuç yok — open authority mesh, campaign kuşadası veya modül adı dene</p>
          ) : (
            grouped.map((group) => (
              <div key={group.label} className="hive-cmd-group">
                <div className="hive-cmd-group-label">{group.label}</div>
                <ul>
                  {group.items.map((cmd) => {
                    rowIdx += 1;
                    const idx = rowIdx;
                    const navId = cmd.navId || cmd.id;
                    const route = cmd.isAction && !cmd.navId ? null : pathFromGosterge(navId, cmd.meshTab ? { meshTab: cmd.meshTab } : {});
                    return (
                      <li key={`${cmd.id}-${cmd.meshTab || ""}-${cmd.label}`}>
                        <button
                          type="button"
                          className={`hive-cmd-item ${idx === activeIdx ? "active" : ""}`}
                          onMouseEnter={() => setActiveIdx(idx)}
                          onClick={() => run(cmd)}
                        >
                          <span className="hive-cmd-item-left">
                            {cmd.icon && <span className="hive-cmd-item-icon">{cmd.icon}</span>}
                            <span className="hive-cmd-label">{cmd.label}</span>
                          </span>
                          <span className="hive-cmd-item-right">
                            {route && <span className="hive-cmd-route">{route}</span>}
                            <span className="hive-cmd-group">{cmd.group}</span>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))
          )}
        </div>

        <footer className="hive-cmd-footer">
          <span>↑↓ navigate</span>
          <span>↵ open</span>
          <span>⌘K toggle</span>
          <span>{flatList.length} results</span>
        </footer>
      </div>
    </div>
  );
}

export function useCommandPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return { open, setOpen, toggle: () => setOpen((v) => !v), close: () => setOpen(false) };
}
