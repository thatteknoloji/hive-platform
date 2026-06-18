import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveToolbar,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveTable,
  HiveBadge,
  HiveEmptyState,
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/expireddomain";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "available", label: "Available" },
  { id: "expiring", label: "Expiring" },
  { id: "authority", label: "Authority" },
  { id: "scores", label: "Scores" },
  { id: "watchlist", label: "Watchlist" },
  { id: "reports", label: "Reports" },
];

const EXPIRY_TONE = {
  active: "ok",
  expiring_90: "info",
  expiring_60: "warn",
  expiring_30: "warn",
  expired: "err",
  provider_missing: "info",
};

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "API hatası";
}

export default function ExpiredDomain() {
  const [tab, setTab] = useState("dashboard");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [kelime, setKelime] = useState("");
  const [adet, setAdet] = useState(10);
  const [domainAdi, setDomainAdi] = useState("");
  const [keyword, setKeyword] = useState("");
  const [exportFormat, setExportFormat] = useState("csv");
  const [reportType, setReportType] = useState("overview");

  const [dashboard, setDashboard] = useState(null);
  const [bulSonuc, setBulSonuc] = useState(null);
  const [expiring, setExpiring] = useState(null);
  const [watchlist, setWatchlist] = useState(null);
  const [scores, setScores] = useState(null);
  const [authority, setAuthority] = useState(null);
  const [integrations, setIntegrations] = useState(null);
  const [report, setReport] = useState(null);
  const [health, setHealth] = useState(null);
  const [scoreResult, setScoreResult] = useState(null);

  const setLoad = (key, val) => setLoading((l) => ({ ...l, [key]: val }));

  const fetchDashboard = useCallback(async () => {
    setLoad("dashboard", true);
    setHata("");
    try {
      const [dash, h] = await Promise.all([
        API.get(`${API_PREFIX}/dashboard`),
        API.get(`${API_PREFIX}/health`),
      ]);
      setDashboard(dash.data);
      setHealth(h.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("dashboard", false);
  }, []);

  const fetchWatchlist = useCallback(async () => {
    setLoad("watchlist", true);
    try {
      const res = await API.get(`${API_PREFIX}/watchlist`);
      setWatchlist(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("watchlist", false);
  }, []);

  const fetchExpiring = useCallback(async () => {
    setLoad("expiring", true);
    try {
      const res = await API.get(`${API_PREFIX}/expiring`);
      setExpiring(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("expiring", false);
  }, []);

  const fetchScores = useCallback(async () => {
    setLoad("scores", true);
    try {
      const res = await API.get(`${API_PREFIX}/scores`);
      setScores(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("scores", false);
  }, []);

  const fetchIntegrations = useCallback(async () => {
    try {
      const res = await API.get(`${API_PREFIX}/integrations`);
      setIntegrations(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    fetchIntegrations();
  }, [fetchDashboard, fetchIntegrations]);

  useEffect(() => {
    if (tab === "watchlist") fetchWatchlist();
    if (tab === "expiring") fetchExpiring();
    if (tab === "scores") fetchScores();
  }, [tab, fetchWatchlist, fetchExpiring, fetchScores]);

  const handleBul = async () => {
    if (!kelime) { setHata("Kelime gerekli"); return; }
    setHata("");
    setLoad("bul", true);
    try {
      const res = await API.post(API_PREFIX, { kelime, adet });
      setBulSonuc(res.data);
      setTab("available");
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("bul", false);
  };

  const handleKaydet = async (dom) => {
    const d = dom || domainAdi;
    if (!d) { setHata("Domain adı gerekli"); return; }
    setHata("");
    setLoad("kaydet", true);
    try {
      await API.post(`${API_PREFIX}/kaydet`, { domain: d, keyword: kelime || keyword });
      await fetchWatchlist();
      setTab("watchlist");
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("kaydet", false);
  };

  const handleSil = async (dom) => {
    setLoad("sil", true);
    try {
      await API.delete(`${API_PREFIX}/sil/${encodeURIComponent(dom)}`);
      await fetchWatchlist();
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("sil", false);
  };

  const handleExport = async () => {
    if (!kelime) { setHata("Kelime gerekli"); return; }
    setLoad("export", true);
    try {
      const res = await API.post(`${API_PREFIX}/export`, { kelime, format: exportFormat });
      const blob = new Blob([res.data.icerik || ""], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `domains.${exportFormat}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("export", false);
  };

  const handleRefreshExpiry = async () => {
    setLoad("refresh", true);
    try {
      await API.post(`${API_PREFIX}/expiry/refresh`, {});
      await Promise.all([fetchExpiring(), fetchWatchlist(), fetchDashboard()]);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("refresh", false);
  };

  const handleAuthority = async () => {
    if (!domainAdi) { setHata("Domain gerekli"); return; }
    setLoad("authority", true);
    try {
      const res = await API.get(`${API_PREFIX}/authority/${encodeURIComponent(domainAdi)}`);
      setAuthority(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("authority", false);
  };

  const handleScore = async () => {
    if (!domainAdi) { setHata("Domain gerekli"); return; }
    setLoad("score", true);
    try {
      const res = await API.post(`${API_PREFIX}/score`, { domain: domainAdi, keyword: keyword || kelime });
      setScoreResult(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("score", false);
  };

  const handleReport = async () => {
    setLoad("report", true);
    try {
      const res = await API.get(`${API_PREFIX}/reports`, { params: { report_type: reportType } });
      setReport(res.data);
    } catch (e) {
      setHata(apiError(e));
    }
    setLoad("report", false);
  };

  const expiryBadge = (status) => (
    <HiveBadge tone={EXPIRY_TONE[status] || "info"}>{status || "—"}</HiveBadge>
  );

  return (
    <HiveShell
      title="Domain Intelligence Engine V2"
      subtitle="Expired Domain Avcısı — availability, expiry watch, authority discovery, scoring"
      meta={health ? `Provider: ${health.provider || "—"} · v${health.version || "2"}` : null}
      actions={
        <HiveBtn variant="outline" onClick={fetchDashboard} disabled={loading.dashboard}>
          Yenile
        </HiveBtn>
      }
    >
      {hata && <HiveAlert type="err">{hata}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <>
          <HiveStatGrid
            stats={[
              { label: "Watchlist", value: dashboard?.watchlist_total ?? "—" },
              { label: "Müsait", value: dashboard?.available_in_watchlist ?? "—" },
              { label: "Yakında Dolan", value: dashboard?.expiring_soon ?? "—", tone: "warn" },
              { label: "HIVE Entegrasyon", value: dashboard?.integrations_ready ? "Hazır" : "Kısmi", tone: dashboard?.integrations_ready ? "ok" : "warn" },
            ]}
          />
          <HivePanel title="Hızlı Arama" description="Keyword ile müsait domain adayları">
            <HiveToolbar>
              <HiveField label="Kelime">
                <HiveInput value={kelime} onChange={(e) => setKelime(e.target.value)} placeholder="örn: seo-tools" />
              </HiveField>
              <HiveField label="Adet">
                <HiveInput type="number" value={adet} onChange={(e) => setAdet(parseInt(e.target.value, 10) || 10)} min={1} max={50} />
              </HiveField>
              <HiveBtn onClick={handleBul} disabled={loading.bul}>
                {loading.bul ? "Aranıyor…" : "Domain Ara"}
              </HiveBtn>
            </HiveToolbar>
          </HivePanel>
          {dashboard?.expiry_status_counts && (
            <HivePanel title="Expiry Durumları">
              <div className="hm-stat-row">
                {Object.entries(dashboard.expiry_status_counts).map(([k, v]) => (
                  <span key={k} className="hm-stat-chip">{k}: {v}</span>
                ))}
              </div>
            </HivePanel>
          )}
        </>
      )}

      {tab === "available" && (
        <HivePanel title="Müsait Domainler" description="Katman 1 — availability check">
          <HiveToolbar>
            <HiveField label="Kelime">
              <HiveInput value={kelime} onChange={(e) => setKelime(e.target.value)} />
            </HiveField>
            <HiveBtn onClick={handleBul} disabled={loading.bul}>Ara</HiveBtn>
            <HiveBtn variant="outline" onClick={handleExport} disabled={loading.export}>Export</HiveBtn>
            <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value)} className="hm-select">
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
              <option value="txt">TXT</option>
            </select>
          </HiveToolbar>
          {!bulSonuc?.domainler?.length ? (
            <HiveEmptyState title="Henüz arama yok" why="Keyword ile domain arayın — sahte DR/TF üretilmez." navigateLabel="Dashboard'a git" onNavigate={() => setTab("dashboard")} />
          ) : (
            <HiveTable
              columns={[
                { key: "domain", label: "Domain" },
                { key: "durum", label: "Durum" },
                { key: "musait", label: "Müsait" },
                { key: "actions", label: "" },
              ]}
              rows={bulSonuc.domainler.map((d) => ({
                id: d.domain,
                domain: d.domain,
                durum: d.durum,
                musait: d.musait ? "Evet" : "Hayır",
                actions: (
                  <HiveBtn variant="outline" size="sm" onClick={() => handleKaydet(d.domain)} disabled={loading.kaydet}>
                    Watchlist
                  </HiveBtn>
                ),
              }))}
            />
          )}
        </HivePanel>
      )}

      {tab === "expiring" && (
        <HivePanel title="Expiry Watcher" description="WHOIS / RDAP — sahte tarih yok">
          <HiveToolbar>
            <HiveBtn onClick={handleRefreshExpiry} disabled={loading.refresh}>
              {loading.refresh ? "Güncelleniyor…" : "Tümünü Yenile"}
            </HiveBtn>
            <HiveBtn variant="outline" onClick={fetchExpiring} disabled={loading.expiring}>Listele</HiveBtn>
          </HiveToolbar>
          {!expiring?.domainler?.length ? (
            <HiveEmptyState title="Yakında dolan domain yok" why="Watchlist'e domain ekleyip expiry refresh çalıştırın." />
          ) : (
            <HiveTable
              columns={[
                { key: "domain", label: "Domain" },
                { key: "expires_at", label: "Bitiş" },
                { key: "days", label: "Gün" },
                { key: "status", label: "Status" },
              ]}
              rows={(expiring.domainler || []).map((d) => ({
                id: d.domain,
                domain: d.domain,
                expires_at: d.expiry?.expires_at || "—",
                days: d.expiry?.days_remaining ?? "—",
                status: expiryBadge(d.expiry?.status),
              }))}
            />
          )}
        </HivePanel>
      )}

      {tab === "authority" && (
        <HivePanel title="Authority Discovery" description="Wayback CDX — archive snapshots">
          <HiveToolbar>
            <HiveField label="Domain">
              <HiveInput value={domainAdi} onChange={(e) => setDomainAdi(e.target.value)} placeholder="example.com" />
            </HiveField>
            <HiveBtn onClick={handleAuthority} disabled={loading.authority}>Keşfet</HiveBtn>
          </HiveToolbar>
          {!authority ? (
            <HiveEmptyState title="Authority verisi yok" why="Domain girin — bulunamazsa unknown döner." />
          ) : (
            <HiveStatGrid
              stats={[
                { label: "Snapshots", value: authority.archive_snapshots ?? 0 },
                { label: "First Seen", value: authority.first_seen || "unknown" },
                { label: "Last Seen", value: authority.last_seen || "unknown" },
                { label: "Category", value: authority.historical_category || "unknown" },
              ]}
            />
          )}
          {authority?.brand_signals && (
            <p className="hm-meta">
              Brand: {authority.brand_signals.status} — {(authority.brand_signals.signals || []).join(", ") || "—"}
            </p>
          )}
        </HivePanel>
      )}

      {tab === "scores" && (
        <HivePanel title="Domain Score" description="0–100 bileşen skorları">
          <HiveToolbar>
            <HiveField label="Domain">
              <HiveInput value={domainAdi} onChange={(e) => setDomainAdi(e.target.value)} />
            </HiveField>
            <HiveField label="Keyword (opsiyonel)">
              <HiveInput value={keyword} onChange={(e) => setKeyword(e.target.value)} />
            </HiveField>
            <HiveBtn onClick={handleScore} disabled={loading.score}>Skorla</HiveBtn>
            <HiveBtn variant="outline" onClick={fetchScores} disabled={loading.scores}>Watchlist Skorları</HiveBtn>
          </HiveToolbar>
          {scoreResult && (
            <HiveStatGrid
              stats={[
                { label: "Overall", value: scoreResult.overall_domain_score, highlight: true },
                { label: "Brandability", value: scoreResult.brandability_score },
                { label: "Authority", value: scoreResult.authority_score },
                { label: "Age", value: scoreResult.age_score },
                { label: "Spam Risk", value: scoreResult.spam_risk_score },
                { label: "Topical Match", value: scoreResult.topical_match_score },
              ]}
            />
          )}
          {scores?.scores?.length > 0 && (
            <HiveTable
              columns={[
                { key: "domain", label: "Domain" },
                { key: "overall", label: "Overall" },
                { key: "brand", label: "Brand" },
                { key: "authority", label: "Authority" },
              ]}
              rows={scores.scores.map((s) => ({
                id: s.domain,
                domain: s.domain,
                overall: s.overall_domain_score,
                brand: s.brandability_score,
                authority: s.authority_score,
              }))}
            />
          )}
        </HivePanel>
      )}

      {tab === "watchlist" && (
        <HivePanel title="Watchlist" description="Kayıtlı domainler + expiry metadata">
          <HiveToolbar>
            <HiveField label="Domain ekle">
              <HiveInput value={domainAdi} onChange={(e) => setDomainAdi(e.target.value)} />
            </HiveField>
            <HiveBtn onClick={() => handleKaydet()} disabled={loading.kaydet}>Kaydet</HiveBtn>
            <HiveBtn variant="outline" onClick={fetchWatchlist} disabled={loading.watchlist}>Yenile</HiveBtn>
          </HiveToolbar>
          {!watchlist?.domainler?.length ? (
            <HiveEmptyState title="Watchlist boş" why="Available sekmesinden veya buradan domain ekleyin." />
          ) : (
            <HiveTable
              columns={[
                { key: "domain", label: "Domain" },
                { key: "musait", label: "Müsait" },
                { key: "expiry", label: "Expiry" },
                { key: "actions", label: "" },
              ]}
              rows={(watchlist.domainler || []).map((d) => ({
                id: d.domain,
                domain: d.domain,
                musait: d.musait == null ? "—" : d.musait ? "Evet" : "Hayır",
                expiry: expiryBadge((d.expiry || {}).status),
                actions: (
                  <HiveBtn variant="outline" size="sm" onClick={() => handleSil(d.domain)} disabled={loading.sil}>
                    Sil
                  </HiveBtn>
                ),
              }))}
            />
          )}
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel title="Reports" description="Özet, expiring, scores, integrations">
          <HiveToolbar>
            <select value={reportType} onChange={(e) => setReportType(e.target.value)} className="hm-select">
              <option value="overview">Overview</option>
              <option value="expiring">Expiring</option>
              <option value="scores">Scores</option>
              <option value="authority">Authority</option>
              <option value="integrations">Integrations</option>
            </select>
            <HiveBtn onClick={handleReport} disabled={loading.report}>Rapor Oluştur</HiveBtn>
          </HiveToolbar>
          {integrations && (
            <p className="hm-meta">
              HIVE read-only: {integrations.ready ? "tüm modüller erişilebilir" : "kısmi erişim"}
            </p>
          )}
          {report && (
            <pre className="hm-code-block" style={{ maxHeight: 400, overflow: "auto", fontSize: "0.75rem" }}>
              {JSON.stringify(report, null, 2)}
            </pre>
          )}
        </HivePanel>
      )}
    </HiveShell>
  );
}
