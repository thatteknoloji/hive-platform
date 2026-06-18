import React, { useState } from "react";
import API from "../api";


export default function WordPressManager() {
  const [tab, setTab] = useState("sites");

  const [siteSubdomain, setSiteSubdomain] = useState("");
  const [siteBaslik, setSiteBaslik] = useState("");
  const [siteEmail, setSiteEmail] = useState("");
  const [siteDomain, setSiteDomain] = useState("");

  const [domainAdi, setDomainAdi] = useState("");
  const [domainIp, setDomainIp] = useState("");
  const [domainSshUser, setDomainSshUser] = useState("root");
  const [domainSshPass, setDomainSshPass] = useState("");
  const [domainDbName, setDomainDbName] = useState("");
  const [domainDbUser, setDomainDbUser] = useState("");
  const [domainDbPass, setDomainDbPass] = useState("");

  const [subDomainId, setSubDomainId] = useState("");
  const [subAdi, setSubAdi] = useState("");
  const [subBaslik, setSubBaslik] = useState("");
  const [subEmail, setSubEmail] = useState("");

  const [cfApiToken, setCfApiToken] = useState("");
  const [cfApiEmail, setCfApiEmail] = useState("");
  const [cfDomainler, setCfDomainler] = useState([]);

  const [healthDomainId, setHealthDomainId] = useState("");
  const [healthResult, setHealthResult] = useState(null);

  const [backupDomainId, setBackupDomainId] = useState("");
  const [backupBulut, setBackupBulut] = useState("");
  const [restoreDomainId, setRestoreDomainId] = useState("");
  const [restoreBackupId, setRestoreBackupId] = useState("");
  const [backupList, setBackupList] = useState([]);

  const [batchDomainIds, setBatchDomainIds] = useState("");
  const [batchPluginAdi, setBatchPluginAdi] = useState("");
  const [batchSubIds, setBatchSubIds] = useState("");

  const [autoAnaDomain, setAutoAnaDomain] = useState("");
  const [autoAdet, setAutoAdet] = useState(10);

  const [talonDomainId, setTalonDomainId] = useState("");
  const [talonParentDomain, setTalonParentDomain] = useState("");
  const [talonKelimeList, setTalonKelimeList] = useState("");

  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [sonuc, setSonuc] = useState(null);
  const [siteList, setSiteList] = useState([]);
  const [domainList, setDomainList] = useState([]);
  const [subList, setSubList] = useState([]);
  const [csvData, setCsvData] = useState("");

  const hataGoster = (msg) => { setHata(msg); setTimeout(() => setHata(""), 4000); };

  const handleSiteOlustur = async () => {
    if (!siteSubdomain) { hataGoster("Subdomain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, siteOlustur: true }));
    try {
      const res = await API.post("/api/wp/site/create", {
        subdomain: siteSubdomain, baslik: siteBaslik, email: siteEmail, domain: siteDomain,
      });
      setSonuc(res.data);
    } catch { hataGoster("Backend hatası"); }
    setLoading(l => ({ ...l, siteOlustur: false }));
  };

  const handleSiteListele = async () => {
    setHata(""); setLoading(l => ({ ...l, siteListele: true }));
    try {
      const res = await API.get("/api/wp/sites/list");
      setSiteList(res.data.siteler || []);
      setSonuc(res.data);
    } catch { hataGoster("Backend hatası"); }
    setLoading(l => ({ ...l, siteListele: false }));
  };

  const handleSiteSil = async (id) => {
    if (!window.confirm(`Site #${id} silinecek?`)) return;
    setHata(""); setLoading(l => ({ ...l, [`siteSil_${id}`]: true }));
    try {
      const res = await API.delete(`/api/wp/site/${id}`);
      setSonuc(res.data);
      handleSiteListele();
    } catch { hataGoster("Silme başarısız"); }
    setLoading(l => ({ ...l, [`siteSil_${id}`]: false }));
  };

  const handleSifreSifirla = async (id) => {
    setHata(""); setLoading(l => ({ ...l, sifirla: true }));
    try {
      const res = await API.post("/api/wp/site/reset-password", { site_id: id });
      setSonuc(res.data);
    } catch { hataGoster("Şifre sıfırlama başarısız"); }
    setLoading(l => ({ ...l, sifirla: false }));
  };

  const handleDomainEkle = async () => {
    if (!domainAdi) { hataGoster("Domain adı gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, domainEkle: true }));
    try {
      const res = await API.post("/api/domain/add", {
        domain: domainAdi, ip: domainIp, ssh_user: domainSshUser,
        ssh_pass: domainSshPass, db_name: domainDbName, db_user: domainDbUser, db_pass: domainDbPass,
      });
      setSonuc(res.data);
    } catch { hataGoster("Backend hatası"); }
    setLoading(l => ({ ...l, domainEkle: false }));
  };

  const handleDomainListele = async () => {
    setHata(""); setLoading(l => ({ ...l, domainListele: true }));
    try {
      const res = await API.get("/api/domain/list");
      setDomainList(res.data.domainler || []);
      setSonuc(res.data);
    } catch { hataGoster("Backend hatası"); }
    setLoading(l => ({ ...l, domainListele: false }));
  };

  const handleWpKur = async (id) => {
    setHata(""); setLoading(l => ({ ...l, [`wpKur_${id}`]: true }));
    try {
      const res = await API.post(`/api/domain/install-wp/${id}`);
      setSonuc(res.data);
      handleDomainListele();
    } catch { hataGoster("Kurulum başarısız"); }
    setLoading(l => ({ ...l, [`wpKur_${id}`]: false }));
  };

  const handleBatchEkle = async () => {
    if (!csvData.trim()) { hataGoster("CSV/JSON verisi girin"); return; }
    setHata(""); setLoading(l => ({ ...l, batch: true }));
    try {
      let domainler;
      try { domainler = JSON.parse(csvData); }
      catch {
        domainler = csvData.split("\n").filter(Boolean).map(line => {
          const cols = line.split(",");
          return { domain: cols[0]?.trim(), ip: cols[1]?.trim(), ssh_user: cols[2]?.trim(), ssh_pass: cols[3]?.trim(), db_name: cols[4]?.trim(), db_user: cols[5]?.trim(), db_pass: cols[6]?.trim() };
        });
      }
      const res = await API.post("/api/domain/batch", { domainler });
      setSonuc(res.data);
    } catch { hataGoster("Toplu ekleme başarısız"); }
    setLoading(l => ({ ...l, batch: false }));
  };

  const handleSubEkle = async () => {
    if (!subAdi || !subDomainId) { hataGoster("Subdomain adı ve Domain ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, subEkle: true }));
    try {
      const domain = domainList.find(d => d.id === parseInt(subDomainId));
      const res = await API.post("/api/subdomain/add", {
        domain_id: parseInt(subDomainId), subdomain: subAdi,
        site_title: subBaslik, admin_email: subEmail,
        parent_domain: domain?.domain || "",
      });
      setSonuc(res.data);
    } catch { hataGoster("Backend hatası"); }
    setLoading(l => ({ ...l, subEkle: false }));
  };

  const handleSubListele = async () => {
    if (!subDomainId) { hataGoster("Domain ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, subListele: true }));
    try {
      const res = await API.get(`/api/subdomain/list/${subDomainId}`);
      setSubList(res.data.subdomainler || []);
      setSonuc(res.data);
    } catch { hataGoster("Backend hatası"); }
    setLoading(l => ({ ...l, subListele: false }));
  };

  const handleSubSil = async (id) => {
    if (!window.confirm(`Subdomain #${id} silinecek?`)) return;
    setHata(""); setLoading(l => ({ ...l, [`subSil_${id}`]: true }));
    try {
      const res = await API.delete(`/api/subdomain/${id}`);
      setSonuc(res.data);
      handleSubListele();
    } catch { hataGoster("Silme başarısız"); }
    setLoading(l => ({ ...l, [`subSil_${id}`]: false }));
  };

  const handleCfImport = async () => {
    setHata(""); setLoading(l => ({ ...l, cfImport: true }));
    try {
      const res = await API.post("/api/domain/cloudflare-import", { api_token: cfApiToken, api_email: cfApiEmail });
      setCfDomainler(res.data.domainler || []);
      setSonuc(res.data);
    } catch { hataGoster("Cloudflare import başarısız"); }
    setLoading(l => ({ ...l, cfImport: false }));
  };

  const handleHealthCheck = async () => {
    if (!healthDomainId) { hataGoster("Domain ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, health: true }));
    try {
      const res = await API.post(`/api/domain/health/${healthDomainId}`);
      setHealthResult(res.data);
      setSonuc(res.data);
    } catch { hataGoster("Sağlık kontrolü başarısız"); }
    setLoading(l => ({ ...l, health: false }));
  };

  const handleTopluHealth = async () => {
    setHata(""); setLoading(l => ({ ...l, topluHealth: true }));
    try {
      const res = await API.get("/api/domain/health-all");
      setHealthResult(res.data);
      setSonuc(res.data);
    } catch { hataGoster("Toplu sağlık kontrolü başarısız"); }
    setLoading(l => ({ ...l, topluHealth: false }));
  };

  const handleBackupAl = async () => {
    if (!backupDomainId) { hataGoster("Domain ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, backup: true }));
    try {
      const res = await API.post("/api/domain/backup", { domain_id: parseInt(backupDomainId), bulut: backupBulut });
      setSonuc(res.data);
    } catch { hataGoster("Yedekleme başarısız"); }
    setLoading(l => ({ ...l, backup: false }));
  };

  const handleRestore = async () => {
    if (!restoreDomainId) { hataGoster("Domain ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, restore: true }));
    try {
      const res = await API.post("/api/domain/restore", { domain_id: parseInt(restoreDomainId), backup_id: parseInt(restoreBackupId || 0) });
      setSonuc(res.data);
    } catch { hataGoster("Restore başarısız"); }
    setLoading(l => ({ ...l, restore: false }));
  };

  const handleBackupListele = async (did) => {
    setHata(""); setLoading(l => ({ ...l, backupList: true }));
    try {
      const url = did ? `/api/domain/backups/${did}` : "/api/domain/backups";
      const res = await API.get(url);
      setBackupList(res.data.yedekler || []);
      setSonuc(res.data);
    } catch { hataGoster("Yedek listeleme başarısız"); }
    setLoading(l => ({ ...l, backupList: false }));
  };

  const handleBatchDomainDelete = async () => {
    if (!batchDomainIds.trim()) { hataGoster("Domain ID'leri girin"); return; }
    setHata(""); setLoading(l => ({ ...l, batchDomainDelete: true }));
    try {
      const ids = batchDomainIds.split(",").map(s => parseInt(s.trim())).filter(Boolean);
      const res = await API.post("/api/domain/batch-delete", { domain_ids: ids });
      setSonuc(res.data);
      handleDomainListele();
    } catch { hataGoster("Toplu silme başarısız"); }
    setLoading(l => ({ ...l, batchDomainDelete: false }));
  };

  const handleBatchDomainReset = async () => {
    if (!batchDomainIds.trim()) { hataGoster("Domain ID'leri girin"); return; }
    setHata(""); setLoading(l => ({ ...l, batchDomainReset: true }));
    try {
      const ids = batchDomainIds.split(",").map(s => parseInt(s.trim())).filter(Boolean);
      const res = await API.post("/api/domain/batch-reset", { domain_ids: ids });
      setSonuc(res.data);
    } catch { hataGoster("Toplu şifre sıfırlama başarısız"); }
    setLoading(l => ({ ...l, batchDomainReset: false }));
  };

  const handleBatchDomainPlugin = async () => {
    if (!batchDomainIds.trim() || !batchPluginAdi.trim()) { hataGoster("Domain ID'leri ve plugin adı gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, batchDomainPlugin: true }));
    try {
      const ids = batchDomainIds.split(",").map(s => parseInt(s.trim())).filter(Boolean);
      const res = await API.post("/api/domain/batch-plugin", { domain_ids: ids, plugin_adi: batchPluginAdi });
      setSonuc(res.data);
    } catch { hataGoster("Toplu plugin yükleme başarısız"); }
    setLoading(l => ({ ...l, batchDomainPlugin: false }));
  };

  const handleBatchSubDelete = async () => {
    if (!batchSubIds.trim()) { hataGoster("Sub ID'leri girin"); return; }
    setHata(""); setLoading(l => ({ ...l, batchSubDelete: true }));
    try {
      const ids = batchSubIds.split(",").map(s => parseInt(s.trim())).filter(Boolean);
      const res = await API.post("/api/subdomain/batch-delete", { sub_ids: ids });
      setSonuc(res.data);
    } catch { hataGoster("Toplu subdomain silme başarısız"); }
    setLoading(l => ({ ...l, batchSubDelete: false }));
  };

  const handleBatchSubReset = async () => {
    if (!batchSubIds.trim()) { hataGoster("Sub ID'leri girin"); return; }
    setHata(""); setLoading(l => ({ ...l, batchSubReset: true }));
    try {
      const ids = batchSubIds.split(",").map(s => parseInt(s.trim())).filter(Boolean);
      const res = await API.post("/api/subdomain/batch-reset", { sub_ids: ids });
      setSonuc(res.data);
    } catch { hataGoster("Toplu subdomain şifre sıfırlama başarısız"); }
    setLoading(l => ({ ...l, batchSubReset: false }));
  };

  const handleBatchSubPlugin = async () => {
    if (!batchSubIds.trim() || !batchPluginAdi.trim()) { hataGoster("Sub ID'leri ve plugin adı gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, batchSubPlugin: true }));
    try {
      const ids = batchSubIds.split(",").map(s => parseInt(s.trim())).filter(Boolean);
      const res = await API.post("/api/subdomain/batch-plugin", { sub_ids: ids, plugin_adi: batchPluginAdi });
      setSonuc(res.data);
    } catch { hataGoster("Toplu subdomain plugin yükleme başarısız"); }
    setLoading(l => ({ ...l, batchSubPlugin: false }));
  };

  const handleTalonCreate = async () => {
    if (!talonDomainId) { hataGoster("Domain ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, talonCreate: true }));
    try {
      const kelimeler = talonKelimeList ? talonKelimeList.split("\n").filter(Boolean).map(s => s.trim()) : undefined;
      const res = await API.post("/api/subdomain/talon-create", {
        domain_id: parseInt(talonDomainId),
        kelimeler,
        parent_domain: talonParentDomain,
        icerik_doldur: true,
      });
      setSonuc(res.data);
    } catch { hataGoster("Talon'dan oluşturma başarısız"); }
    setLoading(l => ({ ...l, talonCreate: false }));
  };

  const handleAutoPilot = async () => {
    if (!autoAnaDomain) { hataGoster("Ana domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, autoPilot: true }));
    try {
      const res = await API.post("/api/domain/autonomous", { ana_domain: autoAnaDomain, adet: autoAdet });
      setSonuc(res.data);
    } catch { hataGoster("Otonom kurulum başarısız"); }
    setLoading(l => ({ ...l, autoPilot: false }));
  };

  const handleContentFill = async (domainId) => {
    setHata(""); setLoading(l => ({ ...l, contentFill: true }));
    try {
      const res = await API.post("/api/wp/site/content-fill", { domain_id: domainId || 0 });
      setSonuc(res.data);
    } catch { hataGoster("İçerik doldurma başarısız"); }
    setLoading(l => ({ ...l, contentFill: false }));
  };

  const Kart = ({ children, style }) => (
    <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", ...style }}>
      {children}
    </div>
  );

  const DurumRengi = (durum) => {
    if (durum === "iyi") return "var(--green)";
    if (durum === "orta") return "var(--orange)";
    if (durum === "kritik") return "var(--red)";
    return "var(--text2)";
  };

  const SiteKart = (site) => (
    <Kart key={site.id} style={{ marginTop: "0.8rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <strong style={{ color: "var(--honey)", fontSize: "1.1rem" }}>{site.baslik}</strong>
          <div style={{ color: "var(--text2)", fontSize: "0.85rem", marginTop: 4 }}>{site.domain}</div>
        </div>
        <span style={{ color: "var(--green)", fontSize: "0.8rem" }}>● {site.durum}</span>
      </div>
      <div style={{ marginTop: "0.8rem", display: "flex", gap: "0.5rem", flexWrap: "wrap", fontSize: "0.8rem" }}>
        <span>WP {site.wp_version}</span>
        <span>ID: {site.multisite_id}</span>
        <span>{site.admin_email}</span>
      </div>
      <div style={{ marginTop: "0.6rem", display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
        <button className="btn btn-sm btn-outline" onClick={() => handleSifreSifirla(site.id)}
          disabled={loading[`sifirla`]} style={{ fontSize: "0.75rem" }}>🔑 Şifre Sıfırla</button>
        <button className="btn btn-sm btn-outline" onClick={() => handleContentFill()}
          disabled={loading.contentFill} style={{ fontSize: "0.75rem" }}>📝 İçerik Doldur</button>
        <button className="btn btn-sm btn-danger" onClick={() => handleSiteSil(site.id)}
          disabled={loading[`siteSil_${site.id}`]} style={{ fontSize: "0.75rem" }}>🗑️ Sil</button>
      </div>
    </Kart>
  );

  const DomainKart = (dom) => (
    <Kart key={dom.id} style={{ marginTop: "0.8rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <strong style={{ color: "var(--blue)", fontSize: "1.1rem" }}>{dom.domain}</strong>
          <div style={{ color: "var(--text2)", fontSize: "0.85rem", marginTop: 4 }}>IP: {dom.ip}</div>
        </div>
        <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
          {dom.saglik_durumu && dom.saglik_durumu !== "bilinmiyor" && (
            <span style={{ color: DurumRengi(dom.saglik_durumu), fontSize: "0.75rem", fontWeight: "bold" }}>
              ● {dom.saglik_durumu.toUpperCase()}
            </span>
          )}
          {dom.wp_installed ? (
            <span style={{ color: "var(--green)", fontSize: "0.8rem" }}>● WP Kurulu</span>
          ) : (
            <span style={{ color: "var(--orange)", fontSize: "0.8rem" }}>○ Kurulum Bekliyor</span>
          )}
        </div>
      </div>
      <div style={{ marginTop: "0.6rem", display: "flex", gap: "1rem", fontSize: "0.8rem", color: "var(--text2)", flexWrap: "wrap" }}>
        <span>DB: {dom.db_name}</span>
        <span>SSH: {dom.ssh_user}</span>
        {dom.wp_versiyon && <span>WP: {dom.wp_versiyon}</span>}
        {dom.wp_theme && <span>Theme: {dom.wp_theme}</span>}
        {dom.ssl_saglayici && <span>SSL: {dom.ssl_saglayici}</span>}
        <span>Subdomain: {dom.subdomain_sayisi || 0}</span>
      </div>
      <div style={{ marginTop: "0.6rem", display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
        {!dom.wp_installed && (
          <button className="btn btn-sm btn-primary" onClick={() => handleWpKur(dom.id)}
            disabled={loading[`wpKur_${dom.id}`]} style={{ fontSize: "0.8rem", background: "var(--green)", color: "#000" }}>
            {loading[`wpKur_${dom.id}`] ? "Kuruluyor..." : "🚀 WP Kur"}
          </button>
        )}
        <button className="btn btn-sm btn-outline" onClick={() => { setHealthDomainId(String(dom.id)); handleHealthCheck(); }}
          style={{ fontSize: "0.75rem" }}>🔍 Sağlık</button>
        <button className="btn btn-sm btn-outline" onClick={() => { setBackupDomainId(String(dom.id)); handleBackupAl(); }}
          style={{ fontSize: "0.75rem" }}>💾 Yedek</button>
        {dom.wp_installed && (
          <button className="btn btn-sm btn-outline" onClick={() => handleContentFill(dom.id)}
            disabled={loading.contentFill} style={{ fontSize: "0.75rem" }}>📝 İçerik</button>
        )}
      </div>
    </Kart>
  );

  const SubKart = (sub) => (
    <Kart key={sub.id} style={{ marginTop: "0.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <strong>{sub.subdomain}</strong>
          <div style={{ color: "var(--text2)", fontSize: "0.8rem" }}>
            {sub.tam_domain} — {sub.site_title}
            {sub.icerik_dolu && <span style={{ color: "var(--green)", marginLeft: 8 }}>● İçerik Dolu</span>}
            {sub.sayfa_sayisi > 0 && <span style={{ color: "var(--text2)", marginLeft: 8 }}>{sub.sayfa_sayisi} sayfa</span>}
          </div>
        </div>
        <button className="btn btn-sm btn-danger" onClick={() => handleSubSil(sub.id)}
          disabled={loading[`subSil_${sub.id}`]} style={{ fontSize: "0.75rem" }}>🗑️</button>
      </div>
    </Kart>
  );

  const RenderSonuc = () => sonuc && (
    <Kart style={{ marginTop: "1rem", borderColor: "var(--honey)" }}>
      <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto" }}>
        {JSON.stringify(sonuc, null, 2)}
      </pre>
    </Kart>
  );

  const tabs = [
    { id: "sites", label: "🌐 WP Siteleri" },
    { id: "domains", label: "📦 Domainler" },
    { id: "subdomains", label: "🔗 Subdomainler" },
    { id: "health", label: "💚 Sağlık & Yedek" },
    { id: "batch", label: "📋 Toplu İşlemler" },
    { id: "autopilot", label: "🤖 Otonom & Cloudflare" },
  ];

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">🌐</div>
        <div className="info">
          <h2>WordPress Site Manager</h2>
          <p>
            Multisite REST API yönetimi, Cloudflare import, sağlık kontrolü,
            yedekleme/restore, toplu işlemler ve otonom mod.
          </p>
        </div>
      </div>

      <div style={{ display: "flex", gap: "0.4rem", marginTop: "1rem", borderBottom: "1px solid var(--border)", paddingBottom: "0.3rem", flexWrap: "wrap" }}>
        {tabs.map(t => (
          <button key={t.id} className={`btn btn-sm ${tab === t.id ? "btn-primary" : "btn-outline"}`}
            onClick={() => setTab(t.id)} style={{ fontSize: "0.85rem" }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "sites" && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ margin: 0, color: "var(--honey)" }}>Yeni WordPress Sitesi Oluştur</h3>
          <div className="talon-form" style={{ marginTop: "0.8rem" }}>
            <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
              <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
                <label>Subdomain</label>
                <input value={siteSubdomain} onChange={e => setSiteSubdomain(e.target.value)} placeholder="orn: vip-model" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
                <label>Site Başlığı</label>
                <input value={siteBaslik} onChange={e => setSiteBaslik(e.target.value)} placeholder="VIP Escort Model" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
                <label>Admin Email</label>
                <input type="email" value={siteEmail} onChange={e => setSiteEmail(e.target.value)} placeholder="admin@site.com" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
                <label>Domain</label>
                <input value={siteDomain} onChange={e => setSiteDomain(e.target.value)} placeholder="multisite.com" />
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleSiteOlustur}
              disabled={loading.siteOlustur} style={{ marginTop: "0.8rem", background: "var(--honey)", color: "#000" }}>
              {loading.siteOlustur ? "Oluşturuluyor..." : "➕ Site Oluştur"}
            </button>
          </div>

          <div style={{ marginTop: "2rem", display: "flex", gap: "0.6rem", alignItems: "center" }}>
            <h3 style={{ margin: 0, color: "var(--text)" }}>Mevcut Siteler</h3>
            <button className="btn btn-sm btn-outline" onClick={handleSiteListele}
              disabled={loading.siteListele}>{loading.siteListele ? "⏳" : "🔄"} Listele</button>
            <button className="btn btn-sm btn-outline" onClick={() => handleContentFill(0)}
              disabled={loading.contentFill}>{loading.contentFill ? "⏳" : "📝"} Tümüne İçerik Doldur</button>
          </div>
          {siteList.length > 0 && siteList.map(SiteKart)}

          <RenderSonuc />
        </div>
      )}

      {tab === "domains" && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ margin: 0, color: "var(--blue)" }}>Yeni Domain Ekle</h3>
          <div className="talon-form" style={{ marginTop: "0.8rem" }}>
            <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
              <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
                <label>Domain</label>
                <input value={domainAdi} onChange={e => setDomainAdi(e.target.value)} placeholder="balkutum.com" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                <label>VPS IP</label>
                <input value={domainIp} onChange={e => setDomainIp(e.target.value)} placeholder="192.168.1.1" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 120 }}>
                <label>SSH</label>
                <input value={domainSshUser} onChange={e => setDomainSshUser(e.target.value)} placeholder="root" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                <label>SSH Şifre</label>
                <input type="password" value={domainSshPass} onChange={e => setDomainSshPass(e.target.value)} />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                <label>DB Adı</label>
                <input value={domainDbName} onChange={e => setDomainDbName(e.target.value)} placeholder="wp_db" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 120 }}>
                <label>DB User</label>
                <input value={domainDbUser} onChange={e => setDomainDbUser(e.target.value)} placeholder="wp_user" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                <label>DB Şifre</label>
                <input type="password" value={domainDbPass} onChange={e => setDomainDbPass(e.target.value)} />
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleDomainEkle}
              disabled={loading.domainEkle} style={{ marginTop: "0.8rem", background: "var(--blue)", color: "#fff" }}>
              {loading.domainEkle ? "Ekleniyor..." : "📥 Domain Ekle"}
            </button>
          </div>

          <div style={{ marginTop: "2rem" }}>
            <h3 style={{ margin: 0, color: "var(--orange)" }}>Toplu Domain Ekle</h3>
            <div className="form-grup" style={{ marginTop: "0.5rem" }}>
              <label>CSV / JSON</label>
              <textarea rows={3} value={csvData} onChange={e => setCsvData(e.target.value)}
                placeholder='domain,ip,ssh_user,ssh_pass,db_name,db_user,db_pass
site1.com,1.2.3.4,root,pass1,wp1,user1,pass1'
                style={{ width: "100%", fontFamily: "monospace", fontSize: "0.8rem" }} />
            </div>
            <button className="btn btn-primary" onClick={handleBatchEkle}
              disabled={loading.batch} style={{ background: "var(--orange)", color: "#000" }}>
              {loading.batch ? "İşleniyor..." : "📤 Toplu Ekle"}
            </button>
          </div>

          <div style={{ marginTop: "2rem", display: "flex", gap: "0.6rem", alignItems: "center" }}>
            <h3 style={{ margin: 0, color: "var(--text)" }}>Domain Listesi</h3>
            <button className="btn btn-sm btn-outline" onClick={handleDomainListele}
              disabled={loading.domainListele}>{loading.domainListele ? "⏳" : "🔄"} Listele</button>
          </div>
          {domainList.length > 0 && domainList.map(DomainKart)}

          <RenderSonuc />
        </div>
      )}

      {tab === "subdomains" && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ margin: 0, color: "var(--purple)" }}>Subdomain Ekle</h3>
          <div className="talon-form" style={{ marginTop: "0.8rem" }}>
            <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                <label>Domain ID</label>
                <input type="number" value={subDomainId} onChange={e => setSubDomainId(e.target.value)} placeholder="1" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
                <label>Subdomain</label>
                <input value={subAdi} onChange={e => setSubAdi(e.target.value)} placeholder="vip-model" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
                <label>Başlık</label>
                <input value={subBaslik} onChange={e => setSubBaslik(e.target.value)} placeholder="VIP Escort Model" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
                <label>Admin Email</label>
                <input type="email" value={subEmail} onChange={e => setSubEmail(e.target.value)} placeholder="admin@site.com" />
              </div>
            </div>
            <div style={{ display: "flex", gap: "0.6rem", marginTop: "0.8rem" }}>
              <button className="btn btn-primary" onClick={handleSubEkle}
                disabled={loading.subEkle} style={{ background: "var(--purple)", color: "#fff" }}>
                {loading.subEkle ? "Ekleniyor..." : "➕ Subdomain Ekle"}
              </button>
              <button className="btn btn-outline" onClick={handleSubListele}
                disabled={loading.subListele}>
                {loading.subListele ? "⏳" : "📋"} Subdomain Listele
              </button>
            </div>
          </div>

          {subList.length > 0 && (
            <div style={{ marginTop: "1.5rem" }}>
              <h4 style={{ margin: 0, color: "var(--text2)" }}>Subdomainler (Domain #{subDomainId})</h4>
              {subList.map(SubKart)}
            </div>
          )}

          <div style={{ marginTop: "2rem" }}>
            <h3 style={{ margin: 0, color: "var(--honey)" }}>Talon ile Toplu Subdomain Oluştur</h3>
            <div className="talon-form" style={{ marginTop: "0.8rem" }}>
              <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
                <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                  <label>Domain ID</label>
                  <input type="number" value={talonDomainId} onChange={e => setTalonDomainId(e.target.value)} placeholder="1" />
                </div>
                <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
                  <label>Parent Domain</label>
                  <input value={talonParentDomain} onChange={e => setTalonParentDomain(e.target.value)} placeholder="balkutum.com" />
                </div>
              </div>
              <div className="form-grup" style={{ marginTop: "0.5rem" }}>
                <label>Özel Kelimeler (opsiyonel, her satıra bir kelime)</label>
                <textarea rows={4} value={talonKelimeList} onChange={e => setTalonKelimeList(e.target.value)}
                  placeholder="vip-escort
anal-escort
otel-escort
luks-model"
                  style={{ width: "100%", fontFamily: "monospace", fontSize: "0.8rem" }} />
              </div>
              <button className="btn btn-primary" onClick={handleTalonCreate}
                disabled={loading.talonCreate} style={{ marginTop: "0.5rem", background: "var(--honey)", color: "#000" }}>
                {loading.talonCreate ? "Oluşturuluyor..." : "🤖 Talon'dan Subdomain Oluştur"}
              </button>
            </div>
          </div>

          <RenderSonuc />
        </div>
      )}

      {tab === "health" && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ margin: 0, color: "var(--green)" }}>Sağlık Kontrolü</h3>
          <div className="talon-form" style={{ marginTop: "0.8rem" }}>
            <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                <label>Domain ID</label>
                <input type="number" value={healthDomainId} onChange={e => setHealthDomainId(e.target.value)} placeholder="1" />
              </div>
              <button className="btn btn-primary" onClick={handleHealthCheck}
                disabled={loading.health} style={{ background: "var(--green)", color: "#000" }}>
                {loading.health ? "⏳" : "🔍 Sağlık Kontrol Et"}
              </button>
              <button className="btn btn-outline" onClick={handleTopluHealth}
                disabled={loading.topluHealth}>
                {loading.topluHealth ? "⏳" : "📊 Tüm Domainleri Kontrol Et"}
              </button>
            </div>
          </div>

          {healthResult && healthResult.iyi !== undefined && (
            <Kart style={{ marginTop: "1rem" }}>
              <h4>Toplu Sağlık Durumu</h4>
              <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
                <span style={{ color: "var(--green)" }}>✅ İyi: {healthResult.iyi}</span>
                <span style={{ color: "var(--orange)" }}>⚠️ Orta: {healthResult.orta}</span>
                <span style={{ color: "var(--red)" }}>❌ Kritik: {healthResult.kritik}</span>
              </div>
            </Kart>
          )}

          <div style={{ marginTop: "2rem" }}>
            <h3 style={{ margin: 0, color: "var(--blue)" }}>Yedekleme & Restore</h3>
            <div className="talon-form" style={{ marginTop: "0.8rem" }}>
              <h4 style={{ color: "var(--text2)", marginBottom: "0.5rem" }}>Yedek Al</h4>
              <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
                <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                  <label>Domain ID</label>
                  <input type="number" value={backupDomainId} onChange={e => setBackupDomainId(e.target.value)} placeholder="1" />
                </div>
                <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
                  <label>Bulut Hedefi</label>
                  <input value={backupBulut} onChange={e => setBackupBulut(e.target.value)} placeholder="Google Drive (opsiyonel)" />
                </div>
                <button className="btn btn-primary" onClick={handleBackupAl}
                  disabled={loading.backup} style={{ background: "var(--blue)", color: "#fff" }}>
                  {loading.backup ? "⏳" : "💾 Yedek Al"}
                </button>
              </div>

              <h4 style={{ color: "var(--text2)", marginTop: "1.5rem", marginBottom: "0.5rem" }}>Restore Et</h4>
              <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
                <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                  <label>Domain ID</label>
                  <input type="number" value={restoreDomainId} onChange={e => setRestoreDomainId(e.target.value)} placeholder="1" />
                </div>
                <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
                  <label>Backup ID (0=son)</label>
                  <input type="number" value={restoreBackupId} onChange={e => setRestoreBackupId(e.target.value)} placeholder="0" />
                </div>
                <button className="btn btn-danger" onClick={handleRestore}
                  disabled={loading.restore}>
                  {loading.restore ? "⏳" : "🔄 Restore Et"}
                </button>
              </div>

              <h4 style={{ color: "var(--text2)", marginTop: "1.5rem", marginBottom: "0.5rem" }}>Yedek Listesi</h4>
              <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
                <button className="btn btn-sm btn-outline" onClick={() => handleBackupListele(0)} disabled={loading.backupList}>
                  {loading.backupList ? "⏳" : "📋 Tüm Yedekleri Listele"}
                </button>
                <button className="btn btn-sm btn-outline" onClick={() => handleBackupListele(parseInt(backupDomainId || 0))} disabled={loading.backupList}>
                  📋 Domain Yedeklerini Listele
                </button>
              </div>
              {backupList.length > 0 && (
                <div style={{ marginTop: "0.5rem" }}>
                  {backupList.map((b, i) => (
                    <Kart key={i} style={{ marginTop: "0.4rem", fontSize: "0.85rem" }}>
                      <strong>#{b.id}</strong> {b.domain} — {b.boyut_mb}MB → {b.hedef_bulut}
                      <div style={{ color: "var(--text2)", fontSize: "0.75rem" }}>{b.durum}</div>
                    </Kart>
                  ))}
                </div>
              )}
            </div>
          </div>

          <RenderSonuc />
        </div>
      )}

      {tab === "batch" && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ margin: 0, color: "var(--orange)" }}>Toplu Domain İşlemleri</h3>
          <Kart style={{ marginTop: "0.8rem" }}>
            <div className="form-grup">
              <label>Domain ID'leri (virgülle ayırın)</label>
              <input value={batchDomainIds} onChange={e => setBatchDomainIds(e.target.value)} placeholder="1, 2, 3, 4, 5" />
            </div>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.8rem" }}>
              <button className="btn btn-sm btn-danger" onClick={handleBatchDomainDelete}
                disabled={loading.batchDomainDelete}>
                {loading.batchDomainDelete ? "⏳" : "🗑️ Toplu Sil"}
              </button>
              <button className="btn btn-sm btn-outline" onClick={handleBatchDomainReset}
                disabled={loading.batchDomainReset}>
                {loading.batchDomainReset ? "⏳" : "🔑 Toplu Şifre Sıfırla"}
              </button>
            </div>
          </Kart>

          <h3 style={{ marginTop: "2rem", color: "var(--purple)" }}>Toplu Plugin Yükleme</h3>
          <Kart style={{ marginTop: "0.8rem" }}>
            <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
              <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
                <label>ID'ler</label>
                <input value={batchDomainIds} onChange={e => setBatchDomainIds(e.target.value)} placeholder="1, 2, 3" />
              </div>
              <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
                <label>Plugin Adı</label>
                <input value={batchPluginAdi} onChange={e => setBatchPluginAdi(e.target.value)} placeholder="Rank Math SEO" />
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleBatchDomainPlugin}
              disabled={loading.batchDomainPlugin} style={{ marginTop: "0.5rem" }}>
              {loading.batchDomainPlugin ? "⏳" : "📦 Domainlere Plugin Yükle"}
            </button>
          </Kart>

          <h3 style={{ marginTop: "2rem", color: "var(--green)" }}>Toplu Subdomain İşlemleri</h3>
          <Kart style={{ marginTop: "0.8rem" }}>
            <div className="form-grup">
              <label>Subdomain ID'leri (virgülle ayırın)</label>
              <input value={batchSubIds} onChange={e => setBatchSubIds(e.target.value)} placeholder="1, 2, 3" />
            </div>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.8rem" }}>
              <button className="btn btn-sm btn-danger" onClick={handleBatchSubDelete}
                disabled={loading.batchSubDelete}>
                {loading.batchSubDelete ? "⏳" : "🗑️ Subdomainleri Sil"}
              </button>
              <button className="btn btn-sm btn-outline" onClick={handleBatchSubReset}
                disabled={loading.batchSubReset}>
                {loading.batchSubReset ? "⏳" : "🔑 Subdomain Şifre Sıfırla"}
              </button>
              <button className="btn btn-sm btn-outline" onClick={handleBatchSubPlugin}
                disabled={loading.batchSubPlugin}>
                {loading.batchSubPlugin ? "⏳" : "📦 Subdomainlere Plugin Yükle"}
              </button>
            </div>
          </Kart>

          <RenderSonuc />
        </div>
      )}

      {tab === "autopilot" && (
        <div style={{ marginTop: "1.5rem" }}>
          <h3 style={{ margin: 0, color: "var(--honey)" }}>Cloudflare Domain Import</h3>
          <Kart style={{ marginTop: "0.8rem" }}>
            <p style={{ fontSize: "0.85rem", color: "var(--text2)", marginBottom: "0.8rem" }}>
              Cloudflare API ile domain'lerinizi otomatik içe aktarın. Domainler otomatik eklenip WP kuruluma hazır hale getirilir.
            </p>
            <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
              <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
                <label>API Token (opsiyonel)</label>
                <input type="password" value={cfApiToken} onChange={e => setCfApiToken(e.target.value)} placeholder="cf_api_token" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
                <label>API Email (opsiyonel)</label>
                <input value={cfApiEmail} onChange={e => setCfApiEmail(e.target.value)} placeholder="user@example.com" />
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleCfImport}
              disabled={loading.cfImport} style={{ marginTop: "0.8rem", background: "var(--honey)", color: "#000" }}>
              {loading.cfImport ? "İçe aktarılıyor..." : "☁️ Cloudflare'den Domain İçe Aktar"}
            </button>
            {cfDomainler.length > 0 && (
              <div style={{ marginTop: "0.8rem" }}>
                <h4 style={{ color: "var(--green)", fontSize: "0.9rem" }}>
                  ✅ {cfDomainler.length} domain içe aktarıldı
                </h4>
                <div style={{ display: "flex", gap: "0.3rem", flexWrap: "wrap", marginTop: "0.4rem" }}>
                  {cfDomainler.map((d, i) => <span key={i} className="tag" style={{ background: "var(--bg)" }}>{d}</span>)}
                </div>
              </div>
            )}
          </Kart>

          <h3 style={{ marginTop: "2rem", color: "var(--green)" }}>Otonom Kurulum (Autopilot)</h3>
          <Kart style={{ marginTop: "0.8rem" }}>
            <p style={{ fontSize: "0.85rem", color: "var(--text2)", marginBottom: "0.8rem" }}>
              Tek tıkla: domain ekle → WP kur → Talon'dan keyword çek → subdomain oluştur → içerik doldur.
              Tam otomatik escort imparatorluğu kurulumu.
            </p>
            <div style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
              <div className="form-grup" style={{ flex: 2, minWidth: 250 }}>
                <label>Ana Domain</label>
                <input value={autoAnaDomain} onChange={e => setAutoAnaDomain(e.target.value)} placeholder="balkutum.com" />
              </div>
              <div className="form-grup" style={{ flex: 1, minWidth: 100 }}>
                <label>Subdomain Adedi</label>
                <input type="number" value={autoAdet} onChange={e => setAutoAdet(parseInt(e.target.value))} />
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleAutoPilot}
              disabled={loading.autoPilot}
              style={{ marginTop: "0.8rem", background: "linear-gradient(135deg, var(--honey), var(--green))", color: "#000", fontWeight: "bold" }}>
              {loading.autoPilot ? "🚀 İmparatorluk Kuruluyor..." : "🤖 OTONOM KUR - TEK TIKLA İMPARATORLUK"}
            </button>
          </Kart>

          <RenderSonuc />
        </div>
      )}

      {hata && (
        <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>
      )}
    </div>
  );
}
