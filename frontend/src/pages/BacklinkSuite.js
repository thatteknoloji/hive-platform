import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";

import ProviderSelector from "../components/ProviderSelector";


const TABS = [
  { id: "dashboard", label: "📊 Dashboard" },
  { id: "hunter", label: "🎯 Backlink Hunter" },
  { id: "hijacker", label: "🕵️ Competitor Hijacker" },
  { id: "linksprayer", label: "💬 LinkSprayer" },
  { id: "directory", label: "📁 Directory Submitter" },
  { id: "internal", label: "🔗 Internal Links" },
  { id: "seoagent", label: "✍️ SEO Content Agent" },
];

function errMsg(e) {
  return e.response?.data?.detail || e.response?.data?.hata || e.message || "Bilinmeyen hata";
}

export default function BacklinkSuite() {
  const [tab, setTab] = useState("dashboard");
  const [loading, setLoading] = useState({});
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState(null);

  const [competitors, setCompetitors] = useState("example.com,rakip.com");
  const [ourDomain, setOurDomain] = useProjectDomainField();
  const [hunterResult, setHunterResult] = useState(null);

  const [rivalDomain, setRivalDomain] = useState("");
  const [hijackerResult, setHijackerResult] = useState(null);

  const [lsUrl, setLsUrl] = useProjectSiteField();
  const [lsKeyword, setLsKeyword] = useState("");
  const [lsAdet, setLsAdet] = useState(10);
  const [lsResult, setLsResult] = useState(null);

  const [dirSite, setDirSite] = useProjectSiteField();
  const [dirName, setDirName] = useState("Balkutusu");
  const [dirLimit, setDirLimit] = useState(20);
  const [dirResult, setDirResult] = useState(null);
  const [dirCount, setDirCount] = useState(0);

  const [internalResult, setInternalResult] = useState(null);

  const [agentKonu, setAgentKonu] = useState("");
  const [agentKeyword, setAgentKeyword] = useState("");
  const [agentDelay, setAgentDelay] = useState(60);
  const [agentResult, setAgentResult] = useState(null);
  const [backlinkProvider, setBacklinkProvider] = useState("");

  const setLoad = (key, val) => setLoading((l) => ({ ...l, [key]: val }));

  const loadDashboard = useCallback(async () => {
    try {
      const res = await API.get("/api/backlink-dashboard");
      setDashboard(res.data);
    } catch (e) {
      setError(errMsg(e));
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const runAll = async () => {
    setError("");
    setLoad("runAll", true);
    try {
      const res = await API.post("/api/backlink-suite/run-all", { domain: rivalDomain || competitors.split(",")[0] });
      setDashboard(res.data.sonuclar?.dashboard || dashboard);
      setHunterResult(res.data.sonuclar?.hunter);
      setHijackerResult(res.data.sonuclar?.competitor);
      setLsResult(res.data.sonuclar?.linksprayer);
      setDirResult(res.data.sonuclar?.directory);
      setInternalResult(res.data.sonuclar?.internal_links);
      setAgentResult(res.data.sonuclar?.seo_agent);
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("runAll", false);
  };

  const hunterFetch = async () => {
    setError("");
    setLoad("hunter", true);
    try {
      const comps = competitors.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await API.post("/api/backlink-hunter/opportunities", {
        competitors: comps,
        our_domain: ourDomain,
        limit: 50,
        provider: backlinkProvider || undefined,
      });
      setHunterResult(res.data);
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("hunter", false);
  };

  const hunterExport = async (fmt) => {
    setError("");
    setLoad("export", true);
    try {
      const res = await API.post("/api/backlink-hunter/export", { format: fmt });
      if (fmt === "csv" && res.data.content) {
        const blob = new Blob([res.data.content], { type: "text/csv" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "backlink_opportunities.csv";
        a.click();
      } else {
        setHunterResult(res.data);
      }
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("export", false);
  };

  const hijackerAnalyze = async () => {
    if (!rivalDomain) { setError("Rakip domain gerekli"); return; }
    setError("");
    setLoad("hijacker", true);
    try {
      const res = await API.post("/api/competitor-hijacker/analyze", {
        domain: rivalDomain,
        send_to_hunter: true,
        limit: 100,
        provider: backlinkProvider || undefined,
      });
      setHijackerResult(res.data);
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("hijacker", false);
  };

  const linksprayerStart = async () => {
    if (!lsKeyword) { setError("Anahtar kelime gerekli"); return; }
    setError("");
    setLoad("ls", true);
    try {
      const res = await API.post("/api/linksprayer/campaign", { hedef_url: lsUrl, keyword: lsKeyword, site_url: lsUrl, adet: lsAdet });
      setLsResult(res.data);
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("ls", false);
  };

  const loadDirectories = async () => {
    setError("");
    setLoad("dirLoad", true);
    try {
      const res = await API.get("/api/directory-submitter/directories");
      setDirCount(res.data.toplam || 0);
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("dirLoad", false);
  };

  const directorySubmit = async () => {
    setError("");
    setLoad("dir", true);
    try {
      const res = await API.post("/api/directory-submitter/submit", { site_url: dirSite, site_name: dirName, limit: dirLimit });
      setDirResult(res.data);
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("dir", false);
  };

  const internalSuggest = async () => {
    setError("");
    setLoad("internal", true);
    try {
      const res = await API.post("/api/internal-link-builder/suggest", { min_score: 1.0, limit: 30 });
      setInternalResult(res.data);
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("internal", false);
  };

  const internalApply = async () => {
    setError("");
    setLoad("apply", true);
    try {
      const res = await API.post("/api/internal-link-builder/apply", { max_apply: 5 });
      setInternalResult((prev) => ({ ...prev, uygulama: res.data }));
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("apply", false);
  };

  const agentPublish = async () => {
    if (!agentKonu && !agentKeyword) { setError("Konu veya anahtar kelime gerekli"); return; }
    setError("");
    setLoad("agent", true);
    try {
      const res = await API.post("/api/seo-agent/generate", { konu: agentKonu, keyword: agentKeyword, publish: true });
      setAgentResult(res.data);
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("agent", false);
  };

  const agentSchedule = async () => {
    if (!agentKonu && !agentKeyword) { setError("Konu veya anahtar kelime gerekli"); return; }
    setError("");
    setLoad("schedule", true);
    try {
      const res = await API.post("/api/seo-agent/schedule", { konu: agentKonu, keyword: agentKeyword, delay_minutes: agentDelay });
      setAgentResult(res.data);
      await loadDashboard();
    } catch (e) {
      setError(errMsg(e));
    }
    setLoad("schedule", false);
  };

  const Table = ({ rows, cols }) => (
    <div style={{ overflowX: "auto", marginTop: "0.75rem" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c.key} style={{ textAlign: "left", padding: "0.4rem", borderBottom: "1px solid var(--border)" }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(rows || []).slice(0, 50).map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c.key} style={{ padding: "0.4rem", borderBottom: "1px solid var(--border)", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {String(r[c.key] ?? "").slice(0, 120)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div style={{ padding: "1.5rem" }}>
      <div className="header" style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
        <div style={{ fontSize: "2rem" }}>🔗</div>
        <div>
          <h2>Backlink Suite</h2>
          <p style={{ color: "var(--text-muted)", margin: 0 }}>6 entegre modül — tek panelden yönetim</p>
        </div>
        <button
          onClick={runAll}
          disabled={loading.runAll}
          style={{ marginLeft: "auto" }}
        >
          {loading.runAll ? "Çalışıyor…" : "⚡ Hepsini Çalıştır"}
        </button>
      </div>

      {error && (
        <div style={{ background: "#3a1a1a", border: "1px solid #a44", padding: "0.75rem", borderRadius: 8, marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      <ProviderSelector
        category="backlink"
        label="Backlink Provider"
        compact
        onChange={(m) => setBacklinkProvider(m)}
      />

      <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => { setTab(t.id); setError(""); }}
            style={{
              opacity: tab === t.id ? 1 : 0.7,
              fontWeight: tab === t.id ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "dashboard" && dashboard && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "0.75rem" }}>
            <Stat label="Fırsatlar" value={dashboard.opportunities_count} />
            <Stat label="Kampanyalar" value={dashboard.campaigns_count} />
            <Stat label="Dizin İşleri" value={dashboard.directory_jobs_count} />
            <Stat label="Link Önerileri" value={dashboard.link_suggestions_count} />
            <Stat label="Zamanlanmış" value={dashboard.scheduled_posts_count} />
          </div>
          <h4 style={{ marginTop: "1.5rem" }}>Son Aktiviteler</h4>
          <ul style={{ fontSize: "0.85rem" }}>
            {(dashboard.son_aktiviteler || []).map((a, i) => (
              <li key={i}>{a.modul} — {a.zaman?.slice(0, 19)} ({a.durum})</li>
            ))}
          </ul>
        </div>
      )}

      {tab === "hunter" && (
        <div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
            <input value={competitors} onChange={(e) => setCompetitors(e.target.value)} placeholder="rakip1.com,rakip2.com" style={{ flex: 2, minWidth: 200 }} />
            <input value={ourDomain} onChange={(e) => setOurDomain(e.target.value)} placeholder="bizim domain" style={{ flex: 1, minWidth: 140 }} />
            <button onClick={hunterFetch} disabled={loading.hunter}>{loading.hunter ? "…" : "🎯 Fırsatları Yakala"}</button>
            <button onClick={() => hunterExport("csv")} disabled={loading.export}>CSV</button>
            <button onClick={() => hunterExport("json")} disabled={loading.export}>JSON</button>
          </div>
          {hunterResult && (
            <>
              <p>Toplam: {hunterResult.toplam} | Yeni: {hunterResult.yeni_eklenen} | Provider: {hunterResult.provider_mode || (hunterResult.free_stack ? "free" : hunterResult.provider?.join?.(", ") || "auto")} {hunterResult.dataforseo ? "· DFS ✓" : ""}</p>
              <Table
                rows={hunterResult.firsatlar}
                cols={[
                  { key: "domain_from", label: "Domain" },
                  { key: "source_url", label: "Kaynak" },
                  { key: "anchor", label: "Anchor" },
                  { key: "rank", label: "Rank" },
                  { key: "rakip", label: "Rakip" },
                ]}
              />
            </>
          )}
        </div>
      )}

      {tab === "hijacker" && (
        <div>
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <input value={rivalDomain} onChange={(e) => setRivalDomain(e.target.value)} placeholder="rakip.com" style={{ flex: 1 }} />
            <button onClick={hijackerAnalyze} disabled={loading.hijacker}>{loading.hijacker ? "…" : "🔍 Analiz Et → Hunter'a Gönder"}</button>
          </div>
          {hijackerResult && (
            <>
              <p>Backlink: {hijackerResult.backlink_sayisi} | Hunter'a aktarılan: {hijackerResult.hunter_a_aktarilan} | Provider: {hijackerResult.provider_mode || hijackerResult.provider || "auto"} {hijackerResult.dataforseo ? "· DFS ✓" : ""}</p>
              <h4>En Güçlü Domainler</h4>
              <Table rows={hijackerResult.top_referring_domains} cols={[{ key: "domain", label: "Domain" }, { key: "adet", label: "Adet" }]} />
              <h4>Örnek Backlinkler</h4>
              <Table
                rows={hijackerResult.ornek_backlinkler}
                cols={[{ key: "domain_from", label: "Domain" }, { key: "anchor", label: "Anchor" }, { key: "rank", label: "Rank" }]}
              />
            </>
          )}
        </div>
      )}

      {tab === "linksprayer" && (
        <div>
          <div style={{ display: "grid", gap: "0.5rem", maxWidth: 480, marginBottom: "0.75rem" }}>
            <input value={lsUrl} onChange={(e) => setLsUrl(e.target.value)} placeholder="Hedef URL / Site URL" />
            <input value={lsKeyword} onChange={(e) => setLsKeyword(e.target.value)} placeholder="Anahtar Kelime" />
            <input type="number" value={lsAdet} onChange={(e) => setLsAdet(Number(e.target.value))} placeholder="Adet" />
            <button onClick={linksprayerStart} disabled={loading.ls}>{loading.ls ? "…" : "🚀 Kampanya Başlat"}</button>
          </div>
          {lsResult && <pre style={{ fontSize: "0.8rem", overflow: "auto" }}>{JSON.stringify(lsResult, null, 2)}</pre>}
        </div>
      )}

      {tab === "directory" && (
        <div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
            <input value={dirSite} onChange={(e) => setDirSite(e.target.value)} placeholder="Site URL" />
            <input value={dirName} onChange={(e) => setDirName(e.target.value)} placeholder="Site Adı" />
            <input type="number" value={dirLimit} onChange={(e) => setDirLimit(Number(e.target.value))} style={{ width: 80 }} />
            <button onClick={loadDirectories} disabled={loading.dirLoad}>{loading.dirLoad ? "…" : "📂 Dizinleri Yükle"}</button>
            <button onClick={directorySubmit} disabled={loading.dir}>{loading.dir ? "…" : "📤 Toplu Gönder"}</button>
          </div>
          {dirCount > 0 && <p>Yüklü dizin: {dirCount}</p>}
          {dirResult && <pre style={{ fontSize: "0.8rem" }}>{JSON.stringify(dirResult, null, 2)}</pre>}
        </div>
      )}

      {tab === "internal" && (
        <div>
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <button onClick={internalSuggest} disabled={loading.internal}>{loading.internal ? "…" : "🔗 Link Önerilerini Göster"}</button>
            <button onClick={internalApply} disabled={loading.apply}>{loading.apply ? "…" : "✅ WordPress'e Uygula"}</button>
          </div>
          {internalResult?.oneriler && (
            <Table
              rows={internalResult.oneriler}
              cols={[
                { key: "kaynak_baslik", label: "Kaynak" },
                { key: "hedef_baslik", label: "Hedef" },
                { key: "skor", label: "Skor" },
              ]}
            />
          )}
          {internalResult?.status === "hata" && <p style={{ color: "#f88" }}>{internalResult.hata}</p>}
        </div>
      )}

      {tab === "seoagent" && (
        <div>
          <div style={{ display: "grid", gap: "0.5rem", maxWidth: 480, marginBottom: "0.75rem" }}>
            <input value={agentKonu} onChange={(e) => setAgentKonu(e.target.value)} placeholder="Konu" />
            <input value={agentKeyword} onChange={(e) => setAgentKeyword(e.target.value)} placeholder="Anahtar Kelime" />
            <input type="number" value={agentDelay} onChange={(e) => setAgentDelay(Number(e.target.value))} placeholder="Dakika (zamanla)" />
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button onClick={agentPublish} disabled={loading.agent}>{loading.agent ? "…" : "📰 Şimdi Yayınla"}</button>
              <button onClick={agentSchedule} disabled={loading.schedule}>{loading.schedule ? "…" : "⏰ Zamanla"}</button>
            </div>
          </div>
          {agentResult && <pre style={{ fontSize: "0.8rem" }}>{JSON.stringify(agentResult, null, 2)}</pre>}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div style={{ background: "var(--bg3)", padding: "0.75rem", borderRadius: 8, border: "1px solid var(--border)" }}>
      <div style={{ fontSize: "1.4rem", fontWeight: 600 }}>{value ?? 0}</div>
      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{label}</div>
    </div>
  );
}
