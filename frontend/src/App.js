import React, { useState, useEffect, useCallback, useMemo, Suspense } from "react";
import API from "./api";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import {
  LazyTalonHub,
  LazyAstroFactory,
  LazyStoryForge,
  LazyCrawlGapEngine,
  LazyAuthorityMeshEngine,
  LazyEntityGeoGraph,
  LazyPlaceSEOPipeline,
  LazyQuestionIntelligenceEngine,
  LazyExecutiveAI,
  PageLoadFallback,
} from "./lazyPages";
import Kefen from "./pages/Kefen";
import HiveCommandPalette, { useCommandPalette } from "./components/HiveCommandPalette";
import WPManager from "./pages/WPManager";
import Zeus from "./pages/Zeus";
import Mystic from "./pages/Mystic";
import RankTracker from "./pages/RankTracker";
import WebScraper from "./pages/WebScraper";
import OpportunityEngine from "./pages/OpportunityEngine";
import DataMinerEngine from "./pages/DataMinerEngine";
import MediumBot from "./pages/MediumBot";
import SEOPoisoning from "./pages/SEOPoisoning";
import RedditCrows from "./pages/RedditCrows";
import RedditManager from "./pages/RedditManager";
import MapsBot from "./pages/MapsBot";
import BTKGargoyle from "./pages/BTKGargoyle";
import ExpiredDomain from "./pages/ExpiredDomain";
import BacklinkHijacker from "./pages/BacklinkHijacker";
import SpamBacklink from "./pages/SpamBacklink";
import ApiHunter from "./pages/ApiHunter";
import AnalyticsHub from "./pages/AnalyticsHub";
import ConversionTracker from "./pages/ConversionTracker";
import ABTestPanel from "./pages/ABTestPanel";
import HeatmapViewer from "./pages/HeatmapViewer";
import FunnelAnalyzer from "./pages/FunnelAnalyzer";
import CitationBuilder from "./pages/CitationBuilder";
import ReviewManager from "./pages/ReviewManager";
import TrendAnalyzer from "./pages/TrendAnalyzer";
import SentimentAI from "./pages/SentimentAI";
import ForecastModule from "./pages/ForecastModule";
import AlertSystem from "./pages/AlertSystem";
import NotificationCenter from "./pages/NotificationCenter";
import ReportGenerator from "./pages/ReportGenerator";
import ScheduleManager from "./pages/ScheduleManager";
import BackupCenter from "./pages/BackupCenter";
import RestoreManager from "./pages/RestoreManager";
import LogViewer from "./pages/LogViewer";
import SystemMonitor from "./pages/SystemMonitor";
import DebugConsole from "./pages/DebugConsole";
import ApiSettings from "./pages/ApiSettings";
import ExposedKeyHunter from "./pages/ExposedKeyHunter";
import AiChat from "./pages/AiChat";
import DomainManager from "./pages/DomainManager";
import UsersRoles from "./pages/UsersRoles";
import ProjectsHub from "./pages/projects/ProjectsHub";
import TumblrManager from "./pages/TumblrManager";
import BloggerManager from "./pages/BloggerManager";
import IndexingFix from "./pages/IndexingFix";
import BacklinkSuite from "./pages/BacklinkSuite";
import Replicator from "./pages/Replicator";
import CategoryHub from "./pages/CategoryHub";
import PageHub from "./pages/PageHub";
import SSSAutomation from "./pages/SSSAutomation";
import SEOQualityGate from "./pages/SEOQualityGate";
import RankIndexWatcher from "./pages/RankIndexWatcher";
import ListingHub from "./pages/ListingHub";
import EntityDetailGenerator from "./pages/EntityDetailGenerator";
import SiteReplicator from "./pages/SiteReplicator";
import NetworkReplicator from "./pages/NetworkReplicator";
import AstroAutoPublisher from "./pages/AstroAutoPublisher";
import ContentRefreshEngine from "./pages/ContentRefreshEngine";
import PublisherHub from "./pages/PublisherHub";
import SupportNetworkEngine from "./pages/SupportNetworkEngine";
import SerpDefenseEngine from "./pages/SerpDefenseEngine";
import AuthorityFactory from "./pages/AuthorityFactory";
import RevenueLeadEngine from "./pages/RevenueLeadEngine";
import CitationEngine from "./pages/CitationEngine";
import ProviderControlCenter from "./pages/ProviderControlCenter";
import HiveAuditEngine from "./pages/HiveAuditEngine";
import CampaignEngine from "./pages/CampaignEngine";
import AutonomousSEOAgent from "./pages/AutonomousSEOAgent";
import MissionControlCenter from "./pages/MissionControlCenter";
import HiveBrain from "./pages/HiveBrain";
import HiveAcademy from "./pages/HiveAcademy.jsx";
import HiveAcademyLegacy from "./pages/HiveAcademyLegacy";
import HiveMentor from "./pages/HiveMentor";
import FirstRunWizard from "./pages/FirstRunWizard";
import HiveSuccessPath from "./pages/HiveSuccessPath";
import ProductionReadinessEngine from "./pages/ProductionReadinessEngine";
import ActionOrchestrator from "./pages/ActionOrchestrator";
import { HiveTopBar, HivePageFrame } from "./components/HiveAppShell";
import HiveOsSidebar from "./components/HiveOsSidebar";
import { gostergeFromPath, pathFromGosterge } from "./config/hiveOsRoutes";
import { canViewNav } from "./rbac";
import BlackModulePanel from "./pages/black/BlackModulePanel";
import {
  BLACK_FLAG_GROUP,
  BLACK_FLAG_MODULES,
  BLACK_FLAG_IDS,
  blackFlagPath,
  blackFlagGosterge,
  parseBlackFlagPath,
} from "./blackFlagModules";

const BLACK_FLAG_DEDICATED = new Set([
  "zeus", "kefen", "mystic", "reddit_mcp", "medium_bot", "maps", "btk",
  "backlinkhijacker", "spambacklink", "backlink_suite", "expireddomain",
]);

const BLACK_FLAG_MODUL_UI = new Set(["phishing", "zeroday", "blackops"]);

const MODUL_BESLEME = {
  talon: ["ranktracker", "linkbuilder", "contentgen", "keywordresearch"],
  kefen: ["spambacklink", "backlinkhijacker", "competitor", "seoaudit"],
  zeus: ["ranktracker", "brandmention", "ai_citation"],
  mystic: ["penalty"],
  eksisozluk: ["brandmention", "reputation", "crisis", "sentiment"],
  reddit: ["brandmention", "reputation", "sentiment"],
  maps: ["reputation", "review", "localseo", "citation"],
  btk: ["crisis", "reputation"],
  expireddomain: ["backlinkhijacker", "linkbuilder", "seoaudit"],
  backlinkhijacker: ["linkbuilder", "seoaudit", "penalty"],
  spambacklink: ["penalty", "seoaudit", "mystic"],
  ranktracker: ["seoaudit", "penalty", "analytics"],
  ai_citation: ["brandmention", "reputation"],
  penalty: ["mystic", "seoaudit", "spambacklink"],
  ddos: ["crisis"],
  indexing: ["seoaudit", "sitemap", "robots", "speedopt"],
  brandmention: ["ai_citation", "reputation", "sentiment"],
  messenger: ["emailblast", "socialmedia"],
  veri: ["leadscraper", "webscraper"],
  topiccluster: ["contentgen", "internallink", "seoaudit"],
  internallink: ["seoaudit", "sitemap", "speedopt"],
  aiagent: ["emailblast", "contentgen"],
  hyperlocal: ["localseo", "maps", "citation"],
  yorum: ["reputation", "sentiment", "review"],
  phishing: ["zeroday", "ddos", "crisis"],
  zeroday: ["ddos"],
  blackops: [],
  indexnow: ["seoaudit", "sitemap", "indexing"],
  brandmentions: ["ai_citation", "reputation", "sentiment", "crisis"],
  seoaudit: ["penalty", "speedopt", "mobilecheck", "schemamarkup"],
  contentgen: ["socialmedia", "emailblast", "autoblog", "spinner"],
  socialmedia: ["brandmention", "reputation", "trend"],
  emailblast: ["messenger", "leadscraper", "conversion"],
  webscraper: ["leadscraper", "competitor", "keywordresearch"],
  keywordresearch: ["contentgen", "talon", "topiccluster"],
  competitor: ["kefen", "seoaudit", "backlinkhijacker"],
  linkbuilder: ["backlinkhijacker", "seoaudit", "penalty"],
  redirect: ["seoaudit", "speedopt", "indexing"],
  sitemap: ["indexing", "seoaudit", "robots"],
  robots: ["seoaudit", "indexing", "sitemap"],
  schemamarkup: ["seoaudit"],
  speedopt: ["seoaudit", "mobilecheck", "userbehavior"],
  mobilecheck: ["seoaudit", "speedopt", "userbehavior"],
  analytics: ["conversion", "funnel", "heatmap", "userbehavior"],
  conversion: ["analytics", "funnel", "abtest"],
  abtest: ["conversion", "heatmap", "userbehavior"],
  heatmap: ["userbehavior", "conversion", "abtest"],
  userbehavior: ["heatmap", "conversion", "analytics"],
  funnel: ["conversion", "analytics"],
  leadscraper: ["emailblast", "messenger", "webscraper"],
  autoblog: ["contentgen", "socialmedia", "indexing"],
  spinner: ["contentgen", "autoblog"],
  translator: ["contentgen", "spinner"],
  localseo: ["maps", "citation", "review"],
  citation: ["localseo", "maps", "review"],
  review: ["reputation", "maps", "localseo"],
  reputation: ["crisis", "brandmention", "sentiment"],
  crisis: ["reputation", "ddos"],
  trend: ["contentgen", "socialmedia", "keywordresearch"],
  sentiment: ["reputation", "crisis", "brandmention"],
  openseo: ["keywordresearch", "contentgen", "talon", "serpbear"],
  serpbear: ["ranktracker", "seoaudit", "openseo", "penalty"],
  seointel: ["ai_citation", "brandmention", "reputation", "sentiment"],
  dataseo: ["competitor", "kefen", "seoaudit", "backlinkhijacker"],
  seoagent: ["seoaudit", "penalty", "speedopt", "schemamarkup"],
  wordpress: ["kefen", "competitor", "spambacklink", "backlinkhijacker"],
  analytics: ["conversion", "funnel", "heatmap", "userbehavior"],
  conversion: ["analytics", "funnel", "abtest"],
  abtest: ["conversion", "heatmap", "userbehavior"],
  heatmap: ["userbehavior", "conversion", "abtest"],
  funnel: ["conversion", "analytics"],
  citation: ["localseo", "maps", "review"],
  review: ["reputation", "maps", "localseo"],
  trend: ["contentgen", "socialmedia", "keywordresearch"],
  sentiment: ["reputation", "crisis", "brandmention"],
  forecast: ["analytics", "trend"],
  alert: ["notification", "monitor"],
  notification: ["alert"],
  report: ["analytics", "forecast"],
  schedule: ["report", "backup"],
  backup: ["restore", "report"],
  restore: ["backup"],
  log: ["monitor", "debug"],
  monitor: ["alert", "log"],
  debug: ["log", "monitor"]
};

const MODUL_KONFIG = {
  talon: { inputs: [
    { key: "ana_kelime", label: "Ana Kelime", default: "kuşadası escort" },
    { key: "adet", label: "Adet", type: "number", default: 10 }
  ], button: "🎯 Anahtar Kelime Üret" },
  kefen: { inputs: [{ key: "domain", label: "Rakip Domain" }], button: "☠️ Analiz Et", danger: true },
  zeus: { dedicated: "zeus" },
  mystic: { dedicated: "mystic" },
  medium_bot: { dedicated: "medium_bot" },
  seo_poisoning: { dedicated: "seo_poisoning" },
  reddit: { dedicated: "reddit" },
  blogger: { dedicated: "blogger" },
  maps: { dedicated: "maps" },
  btk: { dedicated: "btk" },
  expireddomain: { dedicated: "expireddomain" },
  backlinkhijacker: { dedicated: "backlinkhijacker" },
  spambacklink: { dedicated: "spambacklink" },
  ranktracker: { dedicated: "ranktracker" },
  webscraper: { dedicated: "webscraper" },
  leadscraper: { dedicated: "leadscraper" },
  ai_citation: { inputs: [{ key: "marka", label: "Marka Adı" }], button: "🤖 Sorgula" },
  penalty: { inputs: [{ key: "domain", label: "Domain (opsiyonel)" }], button: "🔍 Analiz Et" },
  ddos: { button: "🛡️ Koruma Durumunu Kontrol Et", get: true },
  indexing: { inputs: [{ key: "url", label: "Sayfa URL" }], button: "📤 İndeksleme İste" },
  brandmention: { inputs: [{ key: "marka", label: "Marka Adı" }], button: "📢 Blast Yap" },
  messenger: { inputs: [{ key: "mesaj", label: "Mesaj", type: "textarea" }], button: "💬 Gönder" },
  veri: { inputs: [{ key: "veri", label: "Veri", type: "textarea" }], button: "🔍 Tara" },
  topiccluster: { inputs: [{ key: "konu", label: "Ana Konu" }], button: "📚 Cluster Oluştur" },
  internallink: { inputs: [{ key: "url", label: "Site URL" }], button: "🔗 Optimize Et" },
  aiagent: { inputs: [{ key: "hedef", label: "Hedef" }], button: "🤖 Ajan Gönder" },
  hyperlocal: { inputs: [{ key: "lokasyon", label: "Lokasyon" }], button: "📝 Hikaye Üret" },
  yorum: { inputs: [{ key: "url", label: "Sayfa URL" }, { key: "adet", label: "Adet", type: "number", default: 5 }], button: "💬 Yorum Gönder" },
  phishing: { inputs: [{ key: "hedef", label: "Hedef" }], button: "🎣 Gönder", danger: true, uyari: "⚠️ Yasa dışıdır! Sadece eğitim amaçlı." },
  zeroday: { inputs: [{ key: "hedef", label: "Hedef URL" }], button: "🔍 Zafiyet Tara", danger: true },
  blackops: { blackops: true },
  indexnow: { inputs: [{ key: "url", label: "Sayfa URL" }], button: "📤 IndexNow'a Bildir" },
  brandmentions: { inputs: [{ key: "marka", label: "Marka Adı" }], button: "🔍 Marka Mention Tara" },
  seoaudit: { inputs: [{ key: "url", label: "Site URL" }], button: "🔍 SEO Denetle" },
  contentgen: { inputs: [{ key: "konu", label: "Konu" }, { key: "adet", label: "Adet", type: "number", default: 3 }], button: "✍️ İçerik Başlıkları Oluştur" },
  socialmedia: { inputs: [{ key: "platform", label: "Platform", type: "select", options: ["Twitter","LinkedIn","Facebook","Instagram"], default: "Twitter" }, { key: "mesaj", label: "Mesaj", type: "textarea" }], button: "📱 Paylaş" },
  emailblast: { inputs: [{ key: "konu", label: "Konu" }, { key: "adet", label: "Adet", type: "number", default: 100 }], button: "📧 E-posta Gönder" },
  keywordresearch: { inputs: [{ key: "kelime", label: "Anahtar Kelime" }], button: "🔍 Araştır" },
  competitor: { inputs: [{ key: "domain", label: "Rakip Domain" }], button: "🔍 Rakip Analiz Et" },
  linkbuilder: { inputs: [{ key: "kelime", label: "Kelime" }, { key: "adet", label: "Adet", type: "number", default: 10 }], button: "🔗 Link İnşa Et" },
  redirect: { inputs: [{ key: "url", label: "Site URL" }], button: "🔀 Yönlendirme Tara" },
  sitemap: { inputs: [{ key: "url", label: "Site URL" }], button: "🗺️ Sitemap Oluştur" },
  robots: { inputs: [{ key: "url", label: "Site URL" }], button: "🤖 Robots.txt Düzenle" },
  schemamarkup: { inputs: [{ key: "url", label: "Sayfa URL" }], button: "📋 Şema Ekle" },
  speedopt: { inputs: [{ key: "url", label: "Site URL" }], button: "⚡ Hız Optimize Et" },
  mobilecheck: { inputs: [{ key: "url", label: "Site URL" }], button: "📱 Mobil Kontrol Et" },
  analytics: { inputs: [{ key: "url", label: "Site URL" }], button: "📊 Analitik Raporla" },
  conversion: { inputs: [{ key: "url", label: "Site URL" }], button: "📈 Dönüşüm Takip Et" },
  abtest: { inputs: [{ key: "varyant_a", label: "Varyant A" }, { key: "varyant_b", label: "Varyant B" }], button: "🧪 A/B Test Başlat" },
  heatmap: { inputs: [{ key: "url", label: "Sayfa URL" }], button: "🔥 Isı Haritası Oluştur" },
  userbehavior: { inputs: [{ key: "url", label: "Site URL" }], button: "👤 Kullanıcı Davranış Analiz Et" },
  funnel: { inputs: [{ key: "url", label: "Site URL" }], button: "🔻 Dönüşüm Hunisi Analiz Et" },
  autoblog: { inputs: [{ key: "konu", label: "Konu" }], button: "📝 Otomatik Blog Yayınla" },
  spinner: { inputs: [{ key: "metin", label: "Metin", type: "textarea" }], button: "🔄 İçerik Döndür" },
  translator: { inputs: [{ key: "metin", label: "Metin", type: "textarea" }, { key: "dil", label: "Hedef Dil", default: "İngilizce" }], button: "🌐 Çevir" },
  localseo: { inputs: [{ key: "isletme", label: "İşletme Adı" }, { key: "adres", label: "Adres" }], button: "📍 Yerel SEO Optimize Et" },
  citation: { inputs: [{ key: "isletme", label: "İşletme Adı" }], button: "📑 Alıntı Oluştur" },
  review: { inputs: [{ key: "url", label: "Sayfa URL" }], button: "⭐ Yorum Topla" },
  reputation: { inputs: [{ key: "marka", label: "Marka Adı" }], button: "🔍 İtibar Tara" },
  crisis: { inputs: [{ key: "marka", label: "Marka Adı" }], button: "🚨 Kriz İzle", danger: true },
  trend: { inputs: [{ key: "konu", label: "Konu" }], button: "📈 Trend Analiz Et" },
  sentiment: { inputs: [{ key: "metin", label: "Metin", type: "textarea" }], button: "💭 Duygu Analiz Et" },
  openseo: { sub: [
    { label: "🔍 İlgili Kelimeler", endpoint: "/api/openseo/keyword" },
    { label: "💡 Öneriler", endpoint: "/api/openseo/keyword" },
    { label: "🧠 Fikirler", endpoint: "/api/openseo/keyword" }
  ], globalInput: "kelime" },
  serpbear: { sub: [
    { label: "📊 Sıra Takip Et", endpoint: "/api/serpbear/track" },
    { label: "📝 Keyword Kaydet", endpoint: "/api/serpbear/register" },
    { label: "📋 Kayıtlı Kelimeler", endpoint: "/api/serpbear/keywords", get: true },
    { label: "🗑️ Keyword Sil", endpoint: "/api/serpbear/delete", danger: true },
    { label: "📈 Geçmiş", endpoint: "/api/serpbear/history" },
    { label: "🖼️ SERP Görüntüsü", endpoint: "/api/serpbear/serp" }
  ], globalInput: "keyword" },
  seointel: { sub: [
    { label: "🤖 AI Görünürlük", endpoint: "/api/seointel/ai-visibility" },
    { label: "🏷️ Marka Varlığı", endpoint: "/api/seointel/brand-presence" },
    { label: "🏆 AI Liderlik Tablosu", endpoint: "/api/seointel/leaderboard", get: true },
    { label: "💬 Prompt Simülasyonu", endpoint: "/api/seointel/prompt" },
    { label: "🔗 AI Backlink Profili", endpoint: "/api/seointel/backlinks" }
  ], globalInput: "marka" },
  dataseo: { sub: [
    { label: "🔗 Backlink Genel Bakış", endpoint: "/api/dataseo/backlinks" },
    { label: "📋 Backlink Listesi", endpoint: "/api/dataseo/backlinks/list" },
    { label: "🌐 Yönlendiren Domainler", endpoint: "/api/dataseo/backlinks/domains" },
    { label: "💡 Keyword Fikirleri", endpoint: "/api/dataseo/keyword-ideas" },
    { label: "📊 Keyword Zorluğu", endpoint: "/api/dataseo/keyword-difficulty" },
    { label: "📈 Trafik Tahmini", endpoint: "/api/dataseo/traffic" }
  ], globalInput: "domain" },
  seoagent: { sub: [
    { label: "🕷️ Site Crawl", endpoint: "/api/seoagent/crawl" },
    { label: "🔍 Sayfa Audit", endpoint: "/api/seoagent/audit" }
  ], globalInput: "domain" },
  wordpress: { wordpress: true },
  analytics: { dedicated: "analytics" },
  conversion: { dedicated: "conversion" },
  abtest: { dedicated: "abtest" },
  heatmap: { dedicated: "heatmap" },
  funnel: { dedicated: "funnel" },
  citation: { dedicated: "citation" },
  review: { dedicated: "review" },
  trend: { dedicated: "trend" },
  sentiment: { dedicated: "sentiment" },
  forecast: { dedicated: "forecast" },
  alert: { dedicated: "alert" },
  notification: { dedicated: "notification" },
  report: { dedicated: "report" },
  schedule: { dedicated: "schedule" },
  backup: { dedicated: "backup" },
  restore: { dedicated: "restore" },
  log: { dedicated: "log" },
  monitor: { dedicated: "monitor" },
  debug: { dedicated: "debug" }
};

function ModuleDashboard({ modul }) {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const feeds = MODUL_BESLEME[modul.id] || [];

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      API.get(`/api/modul-istatistik/${modul.id}`).then(r => setStats(r.data)).catch(() => {}),
      API.get(`/api/modul-tarihce/${modul.id}`).then(r => setLogs(r.data || [])).catch(() => {})
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [modul.id]);

  const deleteHistory = async () => {
    if (!window.confirm(`${modul.ad} kayıtlarını silmek istediğinize emin misiniz?`)) return;
    try {
      await API.delete(`/api/modul-tarihce/${modul.id}`);
      setStats(null); setLogs([]);
    } catch { alert("Silme işlemi başarısız."); }
  };

  const chartData = [];
  if (logs.length > 0) {
    const gunMap = {};
    const gunIsim = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"];
    logs.forEach(l => {
      if (l.timestamp) {
        const d = new Date(l.timestamp);
        const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
        gunMap[key] = (gunMap[key] || 0) + 1;
      }
    });
    Object.entries(gunMap).slice(-7).forEach(([k, v]) => {
      const d = new Date(k);
      chartData.push({ gun: gunIsim[d.getDay()] || k.slice(-2), islem: v });
    });
  }

  const trh = (ts) => {
    if (!ts) return "-";
    const d = new Date(ts);
    return d.toLocaleString("tr-TR", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });
  };

  return (
    <div className="modul-dashboard">
      <div className="md-toolbar">
        <button className="btn btn-sm btn-outline" onClick={fetchData} disabled={loading}>
          {loading ? "⏳" : "🔄"} Yenile
        </button>
        <button className="btn btn-sm btn-danger" onClick={deleteHistory}>🗑️ Kayıtları Sil</button>
      </div>
      {stats && (
        <div className="md-stats">
          <div className="md-stat-card">
            <div className="md-stat-val">{stats.toplam}</div>
            <div className="md-stat-label">Toplam Çalıştırma</div>
          </div>
          <div className="md-stat-card">
            <div className="md-stat-val" style={{ color: "var(--orange)" }}>{trh(stats.son_calisma)}</div>
            <div className="md-stat-label">Son Çalıştırma</div>
          </div>
          <div className="md-stat-card">
            <div className="md-stat-val">{feeds.length}</div>
            <div className="md-stat-label">Bağlı Modül</div>
          </div>
        </div>
      )}

      <div className="md-grid">
        {chartData.length > 0 && (
          <div className="md-chart-box">
            <h4>📊 Aktivite (son 7 gün)</h4>
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="gun" tick={{fill:"var(--text2)",fontSize:10}} />
                <Bar dataKey="islem" fill="var(--honey)" radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="md-log-box">
          <h4>⚡ Geçmiş Çalıştırmalar</h4>
          {logs.length === 0 && <p style={{color:"var(--text2)",fontSize:"0.8rem"}}>Henüz çalıştırma kaydı yok.</p>}
          <div className="md-log-list">
            {logs.slice(-6).reverse().map((l,i) => (
              <div key={i} className="md-log-item">
                <span className="md-log-z">{trh(l.timestamp)}</span>
                <span className="md-log-t">{l.inputs ? Object.values(l.inputs).filter(Boolean).join(", ").slice(0, 30) : "-"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {feeds.length > 0 && (
        <div className="md-besleme">
          <h4>🔗 Bu Modülün Verilerini Kullananlar</h4>
          <div className="md-besleme-list">
            {feeds.map((f,i) => <span key={i} className="md-badge">{f}</span>)}
          </div>
        </div>
      )}

      {logs.length > 0 && (
        <details className="md-detay">
          <summary>📋 Tüm Kayıtlar ({logs.length})</summary>
          {logs.slice().reverse().map((l,i) => (
            <div key={i} className="md-kayit">
              <div className="md-kayit-header">
                <span className="md-kayit-z">{trh(l.timestamp)}</span>
                <span className="md-kayit-girdi">{l.inputs ? JSON.stringify(l.inputs) : "-"}</span>
              </div>
              {l.output && (
                <div className="md-kayit-cikti">
                  {Object.entries(l.output).filter(([k]) => k !== "status" && k !== "modul").map(([k,v]) => (
                    <div key={k} className="item">
                      <span className="key">{k}: </span>
                      <span className="val">{Array.isArray(v) ? v.join(", ").slice(0,100) : String(v).slice(0,100)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </details>
      )}
    </div>
  );
}

function ModulUI({ modul, sonuc, setSonuc, yukleniyor, setYukleniyor, hata, setHata }) {
  const [inputs, setInputs] = useState({});
  const cfg = MODUL_KONFIG[modul.id] || {};

  useEffect(() => { setInputs({}); setSonuc(null); setHata(""); }, [modul.id]);

  const handleChange = (key, val) => setInputs(prev => ({ ...prev, [key]: val }));

  const apiPost = async (endpoint, data) => {
    setYukleniyor(true); setSonuc(null); setHata("");
    try { const res = await API.post(endpoint, { ...data, ...inputs }); setSonuc(res.data); }
    catch { setHata("İstek başarısız oldu. Backend çalışıyor mu?"); }
    finally { setYukleniyor(false); }
  };

  const apiGet = async (endpoint) => {
    setYukleniyor(true); setSonuc(null); setHata("");
    try { const res = await API.get(endpoint); setSonuc(res.data); }
    catch { setHata("İstek başarısız oldu."); }
    finally { setYukleniyor(false); }
  };

  const renderSonuc = () => {
    if (!sonuc) return null;
    if (typeof sonuc === "string") return <div className="pre">{sonuc}</div>;
    return Object.entries(sonuc).map(([key, val]) => {
      if (key === "kelimeler" && Array.isArray(val))
        return <div key={key} className="item"><div className="key">Anahtar Kelimeler</div><div className="kelime-list">{val.map((k,i) => <span key={i} className="tag">{k}</span>)}</div></div>;
      if (key === "yorumlar" && Array.isArray(val))
        return <div key={key} className="item"><div className="key">Yorumlar</div>{val.map((y,i) => <div key={i} style={{margin:"0.5rem 0",padding:"0.5rem",background:"var(--bg3)",borderRadius:6}}><strong>{y.isim||"İsimsiz"}</strong> {y.puan ? `★${y.puan}`:""}<div style={{color:"var(--text2)",fontSize:"0.85rem",marginTop:4}}>{y.yorum||""}</div></div>)}</div>;
      if (key === "gecmis" && Array.isArray(val))
        return <div key={key} className="item"><div className="key">Sıralama Geçmişi</div><table className="table"><thead><tr><th>Gün</th><th>Pozisyon</th></tr></thead><tbody>{val.map((g,i) => <tr key={i}><td>{g.gun}</td><td>{g.pozisyon}</td></tr>)}</tbody></table></div>;
      if (key === "hikaye") return <div key={key} className="item"><div className="key">Hikaye</div><div className="pre" style={{marginTop:8,color:"var(--text2)",lineHeight:1.7}}>{val}</div></div>;
      if (key === "icerik") return <div key={key} className="item"><div className="key">Disavow İçeriği</div><div className="pre" style={{marginTop:8,color:"var(--orange)",fontSize:"0.8rem"}}>{val}</div></div>;
      if (key === "uyari") return <div key={key} className="uyari danger">{val}</div>;
      if (key === "status" || key === "modul") return null;
      if (Array.isArray(val)) return <div key={key} className="item"><span className="key">{key}: </span><span className="val">{val.join(", ")}</span></div>;
      if (typeof val === "object" && val !== null) return <div key={key} className="item"><span className="key">{key}: </span><span className="val">{JSON.stringify(val)}</span></div>;
      return <div key={key} className="item"><span className="key">{key}: </span><span className="val">{String(val)}</span></div>;
    });
  };

  const renderInput = (inp) => {
    const val = inputs[inp.key] ?? inp.default ?? "";
    if (inp.type === "textarea") return <textarea placeholder={inp.label} value={val} onChange={e => handleChange(inp.key, e.target.value)} />;
    if (inp.type === "select") return <select value={val} onChange={e => handleChange(inp.key, e.target.value)}>{inp.options.map(o => <option key={o} value={o}>{o}</option>)}</select>;
    return <input type={inp.type || "text"} placeholder={inp.label} value={val} onChange={e => handleChange(inp.key, inp.type === "number" ? parseInt(e.target.value) : e.target.value)} />;
  };

  const renderUI = () => {
    if (cfg.blackops) return (<>
      <div className="uyari danger">⚠️⚠️⚠️ TÜM BLACK OPS MODÜLLERİ AKTİF<br/>Sorumluluk tamamen kullanıcıya aittir.</div>
      <div className="btn-group">
        <button className="btn btn-danger" onClick={() => apiGet("/api/blackops")}>💀 Aktifleştir</button>
        <button className="btn btn-primary" onClick={() => apiGet("/api/blackops/deactivate")}>✅ Devre Dışı Bırak</button>
      </div>
    </>);
    if (cfg.wordpress) return (<WPManager />);
    if (cfg.dedicated) return (<p style={{color:"var(--text2)"}}>Bu modül özel sayfasında yönetilir.</p>);
    if (cfg.sub) return (<>
      {cfg.globalInput && <div className="form-grup"><label>{cfg.globalInput === "marka" ? "Marka Adı" : cfg.globalInput === "kelime" ? "Anahtar Kelime" : cfg.globalInput === "keyword" ? "Keyword" : cfg.globalInput === "domain" ? "Domain" : "Girdi"}</label><input placeholder={cfg.globalInput === "marka" ? "marka-adiniz" : "değer girin"} value={inputs[cfg.globalInput] || ""} onChange={e => handleChange(cfg.globalInput, e.target.value)} /></div>}
      <div className="btn-group">{cfg.sub.map((s,i) => {
        const payload = {};
        if (cfg.globalInput && inputs[cfg.globalInput]) payload[cfg.globalInput] = inputs[cfg.globalInput];
        return <button key={i} className={`btn ${s.danger?"btn-danger":"btn-outline"}`} onClick={() => s.get ? apiGet(s.endpoint) : apiPost(s.endpoint, payload)}>{s.label}</button>;
      })}</div>
    </>);
    if (!cfg.inputs && !cfg.button) return <p style={{color:"var(--text2)"}}>Standart arayüz.</p>;
    return (<>
      {cfg.uyari && <div className="uyari">{cfg.uyari}</div>}
      {cfg.inputs && <div className="form-row" style={{flexWrap:"wrap"}}>{cfg.inputs.map(inp => <div key={inp.key} className="form-grup" style={{flex:1,minWidth:inp.type==="textarea"?"100%":"150px"}}><label>{inp.label}</label>{renderInput(inp)}</div>)}</div>}
      <button className={`btn ${cfg.danger?"btn-danger":"btn-primary"}`} onClick={() => cfg.get?apiGet(`/api/${modul.id}`):apiPost(`/api/${modul.id}`,{})}>{cfg.button}</button>
    </>);
  };

  return (
    <div>
      <div className="header">
        <div className="icon">{modul.icon || "⚙️"}</div>
        <div className="info"><h2>{modul.ad}</h2><p>{modul.aciklama}</p></div>
      </div>
      <div className="status-badge aktif"><span style={{width:8,height:8,borderRadius:"50%",background:"var(--olive2)",display:"inline-block"}} /> Aktif</div>
      <ModuleDashboard modul={modul} />
      <div className="modul-icerik">{renderUI()}</div>
      {yukleniyor && <div className="yukleniyor">⏳ İşlem yapılıyor...</div>}
      {hata && <div className="hata">{hata}</div>}
      {sonuc && <div className="sonuc">{renderSonuc()}</div>}
    </div>
  );
}

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [aktiviteler, setAktiviteler] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      API.get("/api/dashboard/stats").then(r => setStats(r.data)).catch(() => {}),
      API.get("/api/dashboard/activities").then(r => setAktiviteler(r.data || [])).catch(() => setAktiviteler([])),
      API.get("/api/dashboard/chart").then(r => setChartData(r.data || [])).catch(() => setChartData([])),
      API.get("/health").then(r => setHealth(r.data)).catch(() => {})
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div className="dashboard">
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"1.5rem"}}>
        <h2 style={{fontSize:"1.6rem",margin:0}}>🐝 HIVE Dashboard</h2>
        <button className="btn btn-outline" onClick={fetchData} disabled={loading} style={{fontSize:"0.85rem"}}>
          {loading ? "⏳" : "🔄"} Yenile
        </button>
      </div>

      <div className="stats-row">
        <div className="dash-card">
          <div className="dash-sayi">{stats?.toplam_modul ?? "-"}</div>
          <div className="dash-label">Toplam Modül</div>
        </div>
        <div className="dash-card">
          <div className="dash-sayi" style={{color:"var(--olive2)"}}>{stats?.aktif_modul ?? "-"}</div>
          <div className="dash-label">Aktif Modül</div>
        </div>
        <div className="dash-card">
          <div className="dash-sayi" style={{color:"var(--blue)"}}>{stats?.bugun_calistirma ?? "-"}</div>
          <div className="dash-label">Bugün Çalıştırma</div>
        </div>
        <div className="dash-card">
          <div className="dash-sayi" style={{color:"var(--honey)"}}>{stats?.versiyon || health?.versiyon || "3.0"}</div>
          <div className="dash-label">Versiyon</div>
        </div>
      </div>

      {stats?.wordpress && (
        <div className="stats-row" style={{marginTop:"0.75rem"}}>
          <div className="dash-card">
            <div className="dash-sayi" style={{color: stats.wordpress.connected ? "var(--olive2)" : "#ff9f43", fontSize:"1.4rem"}}>
              {stats.wordpress.connected ? "●" : "○"}
            </div>
            <div className="dash-label">WordPress {stats.wordpress.connected ? "Bağlı" : "Kapalı"}</div>
          </div>
          <div className="dash-card">
            <div className="dash-sayi">{stats.wordpress.profiles ?? "—"}</div>
            <div className="dash-label">Canlı İlan</div>
          </div>
          <div className="dash-card">
            <div className="dash-sayi">{stats.wordpress.stories ?? "—"}</div>
            <div className="dash-label">Hikaye</div>
          </div>
          <div className="dash-card">
            <div className="dash-sayi">{stats.wordpress.gece_hayati ?? "—"}</div>
            <div className="dash-label">Gece Hayatı</div>
          </div>
        </div>
      )}

      <div className="dash-grid">
        <div className="dash-panel">
          <h3>📊 Aktivite Grafiği (Son 7 Gün)</h3>
          {chartData.length === 0 ? (
            <p style={{color:"var(--text2)",fontSize:"0.85rem",padding:"2rem 0",textAlign:"center"}}>
              Henüz aktivite verisi yok.<br/>Bir modül çalıştırınca grafik görünecek.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="gun" tick={{fill:"var(--text2)",fontSize:11}} />
                <YAxis tick={{fill:"var(--text2)",fontSize:11}} allowDecimals={false} />
                <Tooltip contentStyle={{background:"var(--bg2)",border:"1px solid var(--border)",borderRadius:6}} labelStyle={{color:"var(--honey)"}} />
                <Bar dataKey="islem" fill="var(--olive2)" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="dash-panel">
          <h3>⚡ Son Aktiviteler</h3>
          {aktiviteler.length === 0 ? (
            <p style={{color:"var(--text2)",fontSize:"0.85rem",padding:"2rem 0",textAlign:"center"}}>
              Henüz aktivite yok.<br/>Bir modül çalıştırınca burada görünecek.
            </p>
          ) : (
            <div className="log-list">
              {aktiviteler.slice(0, 10).map((l,i) => (
                <div key={i} className="log-item">
                  <div className="log-zaman">{l.zaman ? new Date(l.zaman).toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"}) : "-"}</div>
                  <div className="log-islem">{l.modul}</div>
                  <div className="log-modul">{l.islem ? l.islem.slice(0,25) : ""}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="dash-panel" style={{marginTop:"1.5rem"}}>
        <h3>💚 Sistem Durumu</h3>
        <div className="health-grid">
          <div className="health-item">
            <div className="health-label">Backend</div>
            <div className="health-val" style={{color:health?"var(--green)":"var(--red)"}}>
              {health ? "🟢 Çalışıyor" : "🔴 Bağlantı Yok"}
            </div>
          </div>
          <div className="health-item">
            <div className="health-label">Modül Sayısı</div>
            <div className="health-val">{stats?.toplam_modul ?? (health?.modul_sayisi ?? "-")}</div>
          </div>
          <div className="health-item">
            <div className="health-label">Durum</div>
            <div className="health-val">{health?.durum || "-"}</div>
          </div>
          <div className="health-item">
            <div className="health-label">Port</div>
            <div className="health-val">4001</div>
          </div>
        </div>
      </div>
    </div>
  );
}

const MODULE_LABELS = {
  mission_control_center: "Command Center",
  dashboard: "Dashboard",
  authority_mesh_engine: "Authority Mesh Engine",
  authority_factory: "Authority Factory",
  revenue_lead_engine: "Revenue / Lead Engine",
  citation_engine: "Citation Engine",
  executive_ai: "Executive AI",
  autonomous_seo_agent: "Autonomous SEO Agent",
  support_network_engine: "Support Network Engine",
  serp_defense_engine: "SERP Defense Engine",
  publisher_hub: "Publisher Hub",
  opportunity_engine: "Opportunity Engine",
  data_miner_engine: "Data Miner Engine",
  crawl_gap_engine: "Crawl & Gap Engine",
  hive_brain_engine: "HIVE Brain",
  content_refresh_engine: "Content Refresh Engine",
  rank_index_watcher: "Rank & Index Watcher",
  astro_auto_publisher: "Astro Auto Publisher",
  hive_academy: "HIVE Academy",
  hive_academy_legacy: "HIVE Academy — Modül Rehberi",
  hive_mentor: "HIVE Mentor",
  first_run_wizard: "First Run Wizard",
  hive_success_path: "Success Path",
  action_orchestrator: "Action Orchestrator",
  production_readiness_engine: "Production Readiness",
  projects: "Projects",
  project_wizard: "New Project",
  talon: "Talon SEO",
  listing_hub: "Listing Hub",
  apikeys: "API Settings",
};

function App({ onLogout, user }) {
  const [moduller, setModuller] = useState([]);
  const [seciliModul, setSeciliModul] = useState(null);
  const [modulDetay, setModulDetay] = useState(null);
  const [arama, setArama] = useState("");
  const [sonuc, setSonuc] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState("");
  const [acikGrup, setAcikGrup] = useState(null);
  const [gosterge, setGosterge] = useState("mission_control_center");
  const [systemHealth, setSystemHealth] = useState(null);
  const [storyForgeTab, setStoryForgeTab] = useState("url");
  const [sssImportHint, setSssImportHint] = useState(null);
  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState("");
  const activeProjectLabel = useMemo(() => {
    const p = projects.find((x) => (x.project_id || x.id) === activeProjectId);
    return p?.name || (activeProjectId ? activeProjectId : "Proje seçilmedi");
  }, [projects, activeProjectId]);
  const palette = useCommandPalette();
  const paletteContextRef = React.useRef(null);
  const getPaletteContext = useCallback(() => paletteContextRef.current, []);

  useEffect(() => {
    const onCtx = (e) => { paletteContextRef.current = e.detail || null; };
    window.addEventListener("hive-os-palette-context", onCtx);
    return () => window.removeEventListener("hive-os-palette-context", onCtx);
  }, []);

  const talondanSSSZincirine = useCallback((hint) => {
    setSssImportHint(hint || { autoStart: false });
    setGosterge("sss_automation");
    setSeciliModul(null);
    setSonuc(null);
    setHata("");
  }, []);

  useEffect(() => {
    if (gosterge !== "mission_control_center") return undefined;
    const id = setTimeout(() => {
      API.get("/api/mission-control/health")
        .then((r) => setSystemHealth(r.data))
        .catch(() => setSystemHealth(null));
    }, 300);
    return () => clearTimeout(id);
  }, [gosterge]);

  const activeModuleLabel = (() => {
    if (typeof gosterge === "string" && gosterge.startsWith("project_detail:")) return "Project Dashboard";
    return MODULE_LABELS[gosterge] || seciliModul?.ad || gosterge.replace(/_/g, " ");
  })();

  const goBlack = useCallback(async (moduleId, { skipHistory = false } = {}) => {
    const mod = BLACK_FLAG_MODULES.find((m) => m.id === moduleId);
    if (!mod) return;
    const g = blackFlagGosterge(moduleId);
    if (!skipHistory) {
      window.history.pushState({ blackModule: moduleId }, "", blackFlagPath(moduleId));
    }
    setSeciliModul(null);
    setSonuc(null);
    setHata("");
    setAcikGrup(BLACK_FLAG_GROUP);

    if (moduleId === "spam_backlink") {
      setGosterge("spambacklink");
      setModulDetay(null);
      return;
    }
    if (BLACK_FLAG_DEDICATED.has(g) || (mod.dedicated && moduleId !== "spam_backlink")) {
      setGosterge(g);
      setModulDetay(null);
      return;
    }
    if (BLACK_FLAG_MODUL_UI.has(g)) {
      setGosterge("modul");
      setSeciliModul({ id: g, ad: mod.label, aciklama: "", grup: BLACK_FLAG_GROUP });
      try {
        const res = await API.get(`/api/modul/${g}`);
        setModulDetay({ ...res.data, id: g, ad: mod.label, grup: BLACK_FLAG_GROUP });
      } catch {
        setModulDetay({ id: g, ad: mod.label, grup: BLACK_FLAG_GROUP });
      }
      return;
    }
    setModulDetay(null);
    setGosterge(`black:${moduleId}`);
  }, []);

  useEffect(() => {
    API.get("/api/moduller").then(res => {
      if (Array.isArray(res.data)) setModuller(res.data);
      else if (res.data.moduller) setModuller(res.data.moduller);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    API.get("/api/v3/projects", { params: { limit: 200 } })
      .then((res) => {
        const items = (res.data?.projects || []).map((p) => ({
          project_id: p.id,
          id: p.id,
          name: p.name,
          domain: p.domain || "",
          status: p.status,
        }));
        setProjects(items);
        return API.get("/api/v3/projects/active");
      })
      .then((res) => {
        setActiveProjectId(res.data?.active_project_id || "");
      })
      .catch(() => {});
  }, []);

  // Tumblr OAuth dönüşü — callback panel origin'ine gelmeli (balkutusu.com değil)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_token") && params.get("oauth_verifier")) {
      setGosterge("tumblr");
      setSeciliModul(null);
      setSonuc(null);
      setHata("");
    }
  }, []);

  // HIVE OS + BLACK FLAG URL routing
  useEffect(() => {
    const osId = gostergeFromPath(window.location.pathname, window.location.search);
    if (osId) {
      setGosterge(osId);
      setSeciliModul(null);
      setModulDetay(null);
      return;
    }
    const id = parseBlackFlagPath(window.location.pathname);
    if (id) goBlack(id, { skipHistory: true });
    const onPop = () => {
      const osFromPath = gostergeFromPath(window.location.pathname, window.location.search);
      if (osFromPath) {
        setGosterge(osFromPath);
        setSeciliModul(null);
        setModulDetay(null);
        return;
      }
      const mid = parseBlackFlagPath(window.location.pathname);
      if (mid) goBlack(mid, { skipHistory: true });
      else setGosterge("dashboard");
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [goBlack]);

  const grupluModuller = moduller.reduce((acc, m) => {
    if (BLACK_FLAG_IDS.has(m.id)) return acc;
    const g = m.grup || "Diğer";
    if (!acc[g]) acc[g] = [];
    acc[g].push(m);
    return acc;
  }, {});

  const sec = async (mod) => {
    setSeciliModul(mod); setSonuc(null); setHata(""); setAcikGrup(mod.grup);
    if (mod.id === "talon" || mod.id === "talon_orchestrator") {
      if (mod.id === "talon_orchestrator") sessionStorage.setItem("talon_hub_tab", "orchestrator");
      setGosterge("talon"); setModulDetay(null); return;
    }
    if (mod.id === "kefen") {
      setGosterge("kefen"); setModulDetay(null); return;
    }
    if (mod.id === "wordpress") {
      setGosterge("wordpress"); setModulDetay(null); return;
    }
    if (mod.id === "zeus") {
      setGosterge("zeus"); setModulDetay(null); return;
    }
    if (mod.id === "mystic") {
      setGosterge("mystic"); setModulDetay(null); return;
    }
    if (mod.id === "ranktracker") {
      setGosterge("ranktracker"); setModulDetay(null); return;
    }
    if (mod.id === "webscraper") {
      setGosterge("webscraper"); setModulDetay(null); return;
    }
    if (mod.id === "opportunity_engine") { setGosterge("opportunity_engine"); setModulDetay(null); return; }
    if (mod.id === "data_miner_engine") { setGosterge("data_miner_engine"); setModulDetay(null); return; }
    if (mod.id === "hive_brain_engine") { setGosterge("hive_brain_engine"); setModulDetay(null); return; }
    if (mod.id === "leadscraper") {
      setGosterge("leadscraper"); setModulDetay(null); return;
    }
    if (mod.id === "medium_bot") {
      setGosterge("medium_bot"); setModulDetay(null); return;
    }
    if (mod.id === "seo_poisoning") {
      setGosterge("seo_poisoning"); setModulDetay(null); return;
    }
    if (mod.id === "reddit") {
      setGosterge("reddit"); setModulDetay(null); return;
    }
    if (mod.id === "maps") {
      setGosterge("maps"); setModulDetay(null); return;
    }
    if (mod.id === "btk") {
      setGosterge("btk"); setModulDetay(null); return;
    }
    if (mod.id === "expireddomain") {
      setGosterge("expireddomain"); setModulDetay(null); return;
    }
    if (mod.id === "backlinkhijacker") {
      setGosterge("backlinkhijacker"); setModulDetay(null); return;
    }
    if (mod.id === "spambacklink") {
      setGosterge("spambacklink"); setModulDetay(null); return;
    }
    if (mod.id === "apihunter") {
      setGosterge("apihunter"); setModulDetay(null); return;
    }
    if (mod.id === "analytics") { setGosterge("analytics"); setModulDetay(null); return; }
    if (mod.id === "conversion") { setGosterge("conversion"); setModulDetay(null); return; }
    if (mod.id === "abtest") { setGosterge("abtest"); setModulDetay(null); return; }
    if (mod.id === "heatmap") { setGosterge("heatmap"); setModulDetay(null); return; }
    if (mod.id === "funnel") { setGosterge("funnel"); setModulDetay(null); return; }
    if (mod.id === "citation") { setGosterge("citation"); setModulDetay(null); return; }
    if (mod.id === "review") { setGosterge("review"); setModulDetay(null); return; }
    if (mod.id === "trend") { setGosterge("trend"); setModulDetay(null); return; }
    if (mod.id === "sentiment") { setGosterge("sentiment"); setModulDetay(null); return; }
    if (mod.id === "forecast") { setGosterge("forecast"); setModulDetay(null); return; }
    if (mod.id === "alert") { setGosterge("alert"); setModulDetay(null); return; }
    if (mod.id === "notification") { setGosterge("notification"); setModulDetay(null); return; }
    if (mod.id === "report") { setGosterge("report"); setModulDetay(null); return; }
    if (mod.id === "schedule") { setGosterge("schedule"); setModulDetay(null); return; }
    if (mod.id === "backup") { setGosterge("backup"); setModulDetay(null); return; }
    if (mod.id === "restore") { setGosterge("restore"); setModulDetay(null); return; }
    if (mod.id === "log") { setGosterge("log"); setModulDetay(null); return; }
    if (mod.id === "monitor") { setGosterge("monitor"); setModulDetay(null); return; }
    if (mod.id === "debug") { setGosterge("debug"); setModulDetay(null); return; }
    if (mod.id === "apikeys") { setGosterge("apikeys"); setModulDetay(null); return; }
    if (mod.id === "exposedkeyhunter") { setGosterge("exposedkeyhunter"); setModulDetay(null); return; }
    if (mod.id === "ai_chat") { setGosterge("ai_chat"); setModulDetay(null); return; }
    if (mod.id === "tumblr") { setGosterge("tumblr"); setModulDetay(null); return; }
    if (mod.id === "blogger") { setGosterge("blogger"); setModulDetay(null); return; }
    if (mod.id === "replicator") { setGosterge("replicator"); setModulDetay(null); return; }
    if (mod.id === "storyforge" || mod.id === "storyforge_v3") {
      setStoryForgeTab(mod.id === "storyforge_v3" ? "url" : "studio");
      setGosterge("storyforge");
      setModulDetay(null);
      return;
    }
    if (mod.id === "sss_automation") { setGosterge("sss_automation"); setModulDetay(null); return; }
    if (mod.id === "seo_quality_gate") { setGosterge("seo_quality_gate"); setModulDetay(null); return; }
    if (mod.id === "rank_index_watcher") { setGosterge("rank_index_watcher"); setModulDetay(null); return; }
    if (mod.id === "entity_geo_graph") { setGosterge("entity_geo_graph"); setModulDetay(null); return; }
    if (mod.id === "listing_hub") { setGosterge("listing_hub"); setModulDetay(null); return; }
    if (mod.id === "place_seo_pipeline") { setGosterge("place_seo_pipeline"); setModulDetay(null); return; }
    if (mod.id === "entity_detail_generator") { setGosterge("entity_detail_generator"); setModulDetay(null); return; }
    if (mod.id === "site_replicator") { setGosterge("site_replicator"); setModulDetay(null); return; }
    if (mod.id === "network_replicator") { setGosterge("network_replicator"); setModulDetay(null); return; }
    if (mod.id === "astro_auto_publisher") { setGosterge("astro_auto_publisher"); setModulDetay(null); return; }
    if (mod.id === "content_refresh_engine") { setGosterge("content_refresh_engine"); setModulDetay(null); return; }
    if (mod.id === "question_intelligence_engine") { setGosterge("question_intelligence_engine"); setModulDetay(null); return; }
    if (mod.id === "publisher_hub") { setGosterge("publisher_hub"); setModulDetay(null); return; }
    if (mod.id === "support_network_engine") { setGosterge("support_network_engine"); setModulDetay(null); return; }
    if (mod.id === "serp_defense_engine") { setGosterge("serp_defense_engine"); setModulDetay(null); return; }
    if (mod.id === "crawl_gap_engine") { setGosterge("crawl_gap_engine"); setModulDetay(null); return; }
    if (mod.id === "authority_mesh_engine") { setGosterge("authority_mesh_engine"); setModulDetay(null); return; }
    if (mod.id === "authority_factory") { setGosterge("authority_factory"); setModulDetay(null); return; }
    if (mod.id === "revenue_lead_engine") { setGosterge("revenue_lead_engine"); setModulDetay(null); return; }
    if (mod.id === "citation_engine") { setGosterge("citation_engine"); setModulDetay(null); return; }
    if (mod.id === "executive_ai") { setGosterge("executive_ai"); setModulDetay(null); return; }
    if (mod.id === "autonomous_seo_agent") { setGosterge("autonomous_seo_agent"); setModulDetay(null); return; }
    if (mod.id === "mission_control_center") { setGosterge("mission_control_center"); setModulDetay(null); return; }
    if (mod.id === "hive_academy") { setGosterge("hive_academy"); setModulDetay(null); return; }
    if (mod.id === "hive_mentor") { setGosterge("hive_mentor"); setModulDetay(null); return; }
    if (mod.id === "first_run_wizard") { setGosterge("first_run_wizard"); setModulDetay(null); return; }
    if (mod.id === "hive_success_path") { setGosterge("hive_success_path"); setModulDetay(null); return; }
    if (mod.id === "action_orchestrator") { setGosterge("action_orchestrator"); setModulDetay(null); return; }
    if (mod.id === "production_readiness_engine") { setGosterge("production_readiness_engine"); setModulDetay(null); return; }
    if (mod.id === "wordpress") { setGosterge("wordpress"); setModulDetay(null); return; }
    if (mod.id === "domain") { setGosterge("domain_manager"); setModulDetay(null); return; }
    setGosterge("modul");
    try {
      const res = await API.get(`/api/modul/${mod.id}`);
      setModulDetay({ ...res.data, id: mod.id, ad: mod.ad, aciklama: mod.aciklama, grup: mod.grup });
    } catch { setModulDetay({ ...mod, durum: "hata" }); }
  };

  const navigateTo = useCallback((id, opts = {}) => {
    setGosterge(id);
    setSeciliModul(null);
    setSonuc(null);
    setHata("");
    if (opts.meshTab) {
      sessionStorage.setItem("hive_mesh_tab", opts.meshTab);
      window.dispatchEvent(new Event("hive-mesh-tab"));
    }
    const path = pathFromGosterge(id, opts);
    if (path) {
      window.history.pushState({ hiveOsPage: id, meshTab: opts.meshTab || null }, "", path);
    }
  }, []);

  const toggleGrup = (g) => setAcikGrup(acikGrup === g ? null : g);
  const gotoDashboard = () => {
    setSeciliModul(null);
    setGosterge("dashboard");
    setSonuc(null);
    setHata("");
    window.history.pushState({}, "", "/");
  };

  const blackFlagActiveId = (() => {
    if (gosterge.startsWith("black:")) return gosterge.slice(6);
    const fromPath = parseBlackFlagPath(window.location.pathname);
    if (fromPath) return fromPath;
    if (gosterge === "spambacklink" && window.location.pathname.includes("spam_backlink")) return "spam_backlink";
    if (BLACK_FLAG_IDS.has(gosterge)) return gosterge;
    return null;
  })();

  const blackFlagFiltered = BLACK_FLAG_MODULES.filter(
    (m) => m.label.toLowerCase().includes(arama.toLowerCase()) || m.id.includes(arama.toLowerCase())
  );

  return (
    <div className="panel">
      <HiveCommandPalette
        open={palette.open}
        onClose={palette.close}
        onNavigate={navigateTo}
        getContext={getPaletteContext}
        onAction={(actionId) => {
          if (actionId === "action:refresh-mcc") {
            window.dispatchEvent(new Event("hive-war-room-refresh"));
            navigateTo("mission_control_center");
          }
        }}
      />
      <div className="sidebar">
        <div className="sidebar-header" onClick={gotoDashboard} style={{cursor:"pointer"}}>
          <h1>◆ HIVE SEO OS</h1>
          <span>Command Center · {moduller.length} modül</span>
        </div>
        <div className="sidebar-search">
          <input placeholder="🔍 Modül ara..." value={arama} onChange={e => setArama(e.target.value)} />
        </div>
        <div className="sidebar-scroll">
        <HiveOsSidebar
          gosterge={gosterge}
          arama={arama}
          acikGrup={acikGrup}
          setAcikGrup={setAcikGrup}
          onNavigate={navigateTo}
          onDashboard={gotoDashboard}
          onOpenPalette={palette.toggle}
          moduller={moduller}
          grupluModuller={grupluModuller}
          seciliModul={seciliModul}
          onSelectModule={sec}
          canView={(navId) => canViewNav(user?.role, navId)}
          blackFlagSection={(
            <div className="modul-liste modul-liste-black-flag">
              <div className="grup-header grup-header-black" onClick={() => toggleGrup(BLACK_FLAG_GROUP)}>
                <span className="grup-ok">{acikGrup === BLACK_FLAG_GROUP ? "▼" : "▶"}</span>
                <span className="grup-isim">{BLACK_FLAG_GROUP}</span>
                <span className="grup-sayi">{BLACK_FLAG_MODULES.length}</span>
              </div>
              {acikGrup === BLACK_FLAG_GROUP && blackFlagFiltered.map((mod) => (
                <a
                  key={mod.id}
                  href={blackFlagPath(mod.id)}
                  className={`modul-item modul-item-black ${blackFlagActiveId === mod.id ? "active" : ""}`}
                  onClick={(e) => { e.preventDefault(); goBlack(mod.id); }}
                >
                  <div className="dot active-dot" style={{ background: "#8b0000" }} />
                  <div className="info">
                    <div className="isim">{mod.label}</div>
                    <div className="aciklama">{mod.id}</div>
                  </div>
                  <span className="aktif-badge" style={{ background: "#4a0000", color: "#ff6b6b" }}>black</span>
                </a>
              ))}
            </div>
          )}
        />
        </div>
      </div>
      <div className="main hive-main-v2">
        <HiveTopBar
          projectName="HIVE SEO OS"
          moduleLabel={activeModuleLabel}
          systemHealth={systemHealth?.system_health}
          onQuickAction={() => navigateTo("mission_control_center")}
          quickActionLabel="◆ Command Center"
          onLogout={onLogout}
          userEmail={user?.email}
          projects={projects}
          activeProjectName={activeProjectLabel}
          onProjectChange={async (projectId) => {
            await API.post(`/api/v3/projects/${projectId}/set-active`);
            setActiveProjectId(projectId);
            window.dispatchEvent(new CustomEvent("hive-active-project-changed"));
          }}
        />
        <HivePageFrame pageKey={gosterge}>
        <Suspense fallback={<PageLoadFallback />}>
        {gosterge === "dashboard" && <Dashboard />}
        {gosterge === "mission_control_center" && (
          <MissionControlCenter onNavigate={navigateTo} onOpenPalette={palette.toggle} />
        )}
        {gosterge === "hive_academy" && (
          <HiveAcademy onNavigate={navigateTo} />
        )}
        {gosterge === "hive_academy_legacy" && (
          <HiveAcademyLegacy onNavigate={navigateTo} />
        )}
        {gosterge === "hive_mentor" && (
          <HiveMentor onNavigate={navigateTo} />
        )}
        {gosterge === "first_run_wizard" && (
          <FirstRunWizard onNavigate={navigateTo} />
        )}
        {gosterge === "hive_success_path" && (
          <HiveSuccessPath onNavigate={navigateTo} />
        )}
        {gosterge === "action_orchestrator" && (
          <ActionOrchestrator onNavigate={navigateTo} />
        )}
        {gosterge === "production_readiness_engine" && (
          <ProductionReadinessEngine />
        )}
        {gosterge === "talon" && (
          <div className="modul-card">
            <LazyTalonHub
              onNavigateToSSS={talondanSSSZincirine}
              onNavigateAstro={() => { setGosterge("astro_factory"); setSeciliModul(null); setSonuc(null); setHata(""); }}
              onNavigatePageHub={() => { setGosterge("page_hub"); setSeciliModul(null); setSonuc(null); setHata(""); }}
              onNavigateSSS={() => { setGosterge("sss_automation"); setSeciliModul(null); setSonuc(null); setHata(""); }}
            />
          </div>
        )}
        {gosterge === "kefen" && (
          <div className="modul-card">
            <Kefen />
          </div>
        )}
        {gosterge === "wordpress" && (
          <div className="modul-card">
            <WPManager />
          </div>
        )}
        {gosterge === "zeus" && (
          <div className="modul-card">
            <Zeus />
          </div>
        )}
        {gosterge === "mystic" && (
          <div className="modul-card">
            <Mystic />
          </div>
        )}
        {gosterge === "ranktracker" && (
          <div className="modul-card">
            <RankTracker />
          </div>
        )}
        {gosterge === "webscraper" && (
          <div className="modul-card">
            <WebScraper />
          </div>
        )}
        {gosterge === "leadscraper" && (
          <div className="modul-card">
            <LeadScraper />
          </div>
        )}
        {gosterge === "medium_bot" && (
          <div className="modul-card">
            <MediumBot />
          </div>
        )}
        {gosterge === "seo_poisoning" && (
          <div className="modul-card">
            <SEOPoisoning />
          </div>
        )}
        {gosterge === "reddit" && (
          <div className="modul-card">
            <RedditManager />
          </div>
        )}
        {gosterge === "reddit_mcp" && (
          <div className="modul-card">
            <RedditManager />
          </div>
        )}
        {gosterge === "maps" && (
          <div className="modul-card">
            <MapsBot />
          </div>
        )}
        {gosterge === "btk" && (
          <div className="modul-card">
            <BTKGargoyle />
          </div>
        )}
        {gosterge === "expireddomain" && (
          <div className="modul-card">
            <ExpiredDomain />
          </div>
        )}
        {gosterge === "backlinkhijacker" && (
          <div className="modul-card">
            <BacklinkHijacker />
          </div>
        )}
        {gosterge === "spambacklink" && (
          <div className="modul-card">
            <SpamBacklink />
          </div>
        )}
        {gosterge === "apihunter" && (
          <div className="modul-card">
            <ApiHunter />
          </div>
        )}
        {gosterge === "analytics" && (
          <div className="modul-card">
            <AnalyticsHub />
          </div>
        )}
        {gosterge === "indexing_fix" && (
          <div className="modul-card">
            <IndexingFix />
          </div>
        )}
        {gosterge === "backlink_suite" && (
          <div className="modul-card">
            <BacklinkSuite />
          </div>
        )}
        {gosterge === "conversion" && (
          <div className="modul-card">
            <ConversionTracker />
          </div>
        )}
        {gosterge === "abtest" && (
          <div className="modul-card">
            <ABTestPanel />
          </div>
        )}
        {gosterge === "heatmap" && (
          <div className="modul-card">
            <HeatmapViewer />
          </div>
        )}
        {gosterge === "funnel" && (
          <div className="modul-card">
            <FunnelAnalyzer />
          </div>
        )}
        {gosterge === "citation" && (
          <div className="modul-card">
            <CitationBuilder />
          </div>
        )}
        {gosterge === "review" && (
          <div className="modul-card">
            <ReviewManager />
          </div>
        )}
        {gosterge === "trend" && (
          <div className="modul-card">
            <TrendAnalyzer />
          </div>
        )}
        {gosterge === "sentiment" && (
          <div className="modul-card">
            <SentimentAI />
          </div>
        )}
        {gosterge === "forecast" && (
          <div className="modul-card">
            <ForecastModule />
          </div>
        )}
        {gosterge === "alert" && (
          <div className="modul-card">
            <AlertSystem />
          </div>
        )}
        {gosterge === "notification" && (
          <div className="modul-card">
            <NotificationCenter />
          </div>
        )}
        {gosterge === "report" && (
          <div className="modul-card">
            <ReportGenerator />
          </div>
        )}
        {gosterge === "schedule" && (
          <div className="modul-card">
            <ScheduleManager />
          </div>
        )}
        {gosterge === "backup" && (
          <div className="modul-card">
            <BackupCenter />
          </div>
        )}
        {gosterge === "restore" && (
          <div className="modul-card">
            <RestoreManager />
          </div>
        )}
        {gosterge === "log" && (
          <div className="modul-card">
            <LogViewer />
          </div>
        )}
        {gosterge === "monitor" && (
          <div className="modul-card">
            <SystemMonitor />
          </div>
        )}
        {gosterge === "debug" && (
          <div className="modul-card">
            <DebugConsole />
          </div>
        )}
        {gosterge === "apikeys" && (
          <div className="modul-card">
            <ApiSettings />
          </div>
        )}
        {gosterge === "exposedkeyhunter" && (
          <div className="modul-card">
            <ExposedKeyHunter />
          </div>
        )}
        {gosterge === "ai_chat" && (
          <div className="modul-card">
            <AiChat />
          </div>
        )}
        {gosterge === "tumblr" && (
          <div className="modul-card">
            <TumblrManager />
          </div>
        )}
        {gosterge === "blogger" && (
          <div className="modul-card">
            <BloggerManager />
          </div>
        )}
        {gosterge === "replicator" && (
          <div className="modul-card">
            <Replicator />
          </div>
        )}
        {gosterge === "category_hub" && (
          <div className="modul-card">
            <CategoryHub
              onNavigateStoryForge={() => { setStoryForgeTab("studio"); setGosterge("storyforge"); setSeciliModul(null); setSonuc(null); setHata(""); }}
              onNavigatePageHub={() => { setGosterge("page_hub"); setSeciliModul(null); setSonuc(null); setHata(""); }}
            />
          </div>
        )}
        {gosterge === "page_hub" && (
          <div className="modul-card">
            <PageHub
              onNavigateSSS={() => { setGosterge("sss_automation"); setSeciliModul(null); setSonuc(null); setHata(""); }}
              onNavigateCategoryHub={() => { setGosterge("category_hub"); setSeciliModul(null); setSonuc(null); setHata(""); }}
            />
          </div>
        )}
        {gosterge === "astro_factory" && (
          <div className="modul-card">
            <LazyAstroFactory
              onNavigateQualityGate={(projectId) => {
                if (projectId) sessionStorage.setItem("seo_qg_project_id", projectId);
                setGosterge("seo_quality_gate");
                setSeciliModul(null);
                setSonuc(null);
                setHata("");
              }}
            />
          </div>
        )}
        {gosterge === "seo_quality_gate" && (
          <div className="modul-card">
            <SEOQualityGate preselectedProjectId={sessionStorage.getItem("seo_qg_project_id") || ""} />
          </div>
        )}
        {gosterge === "rank_index_watcher" && (
          <div className="modul-card">
            <RankIndexWatcher />
          </div>
        )}
        {gosterge === "entity_geo_graph" && (
          <div className="modul-card">
            <LazyEntityGeoGraph />
          </div>
        )}
        {gosterge === "listing_hub" && (
          <div className="modul-card">
            <ListingHub />
          </div>
        )}
        {gosterge === "place_seo_pipeline" && (
          <div className="modul-card">
            <LazyPlaceSEOPipeline />
          </div>
        )}
        {gosterge === "entity_detail_generator" && (
          <div className="modul-card">
            <EntityDetailGenerator />
          </div>
        )}
        {gosterge === "site_replicator" && (
          <div className="modul-card">
            <SiteReplicator />
          </div>
        )}
        {gosterge === "network_replicator" && (
          <div className="modul-card">
            <NetworkReplicator />
          </div>
        )}
        {gosterge === "astro_auto_publisher" && (
          <div className="modul-card">
            <AstroAutoPublisher preselectedProjectId={sessionStorage.getItem("astro_auto_project_id") || ""} />
          </div>
        )}
        {gosterge === "content_refresh_engine" && (
          <div className="modul-card">
            <ContentRefreshEngine preselectedProjectId={sessionStorage.getItem("content_refresh_project_id") || ""} />
          </div>
        )}
        {gosterge === "question_intelligence_engine" && (
          <div className="modul-card">
            <LazyQuestionIntelligenceEngine preselectedProjectId={sessionStorage.getItem("qie_project_id") || ""} />
          </div>
        )}
        {gosterge === "publisher_hub" && (
          <div className="modul-card">
            <PublisherHub onNavigate={navigateTo} />
          </div>
        )}
        {gosterge === "support_network_engine" && (
          <div className="modul-card">
            <SupportNetworkEngine />
          </div>
        )}
        {gosterge === "opportunity_engine" && (
          <div className="modul-card">
            <OpportunityEngine />
          </div>
        )}
        {gosterge === "data_miner_engine" && (
          <div className="modul-card">
            <DataMinerEngine />
          </div>
        )}
        {gosterge === "hive_brain_engine" && (
          <div className="modul-card">
            <HiveBrain onNavigate={navigateTo} />
          </div>
        )}
        {gosterge === "serp_defense_engine" && (
          <div className="modul-card">
            <SerpDefenseEngine />
          </div>
        )}
        {gosterge === "crawl_gap_engine" && (
          <div className="modul-card">
            <LazyCrawlGapEngine />
          </div>
        )}
        {gosterge === "authority_mesh_engine" && (
          <div className="modul-card">
            <LazyAuthorityMeshEngine onNavigate={navigateTo} />
          </div>
        )}
        {gosterge === "authority_factory" && (
          <div className="modul-card">
            <AuthorityFactory />
          </div>
        )}
        {gosterge === "revenue_lead_engine" && (
          <div className="modul-card">
            <RevenueLeadEngine />
          </div>
        )}
        {gosterge === "citation_engine" && (
          <div className="modul-card">
            <CitationEngine />
          </div>
        )}
        {gosterge === "executive_ai" && (
          <div className="modul-card">
            <LazyExecutiveAI />
          </div>
        )}
        {gosterge === "provider_control_center" && (
          <div className="modul-card">
            <ProviderControlCenter />
          </div>
        )}
        {gosterge === "hive_audit_engine" && (
          <div className="modul-card">
            <HiveAuditEngine />
          </div>
        )}
        {gosterge === "campaign_engine" && (
          <div className="modul-card">
            <CampaignEngine />
          </div>
        )}
        {gosterge === "autonomous_seo_agent" && (
          <div className="modul-card">
            <AutonomousSEOAgent />
          </div>
        )}
        {gosterge.startsWith("black:") && (() => {
          const mid = gosterge.slice(6);
          const mod = BLACK_FLAG_MODULES.find((m) => m.id === mid);
          return (
            <div className="modul-card modul-card-black">
              <BlackModulePanel
                moduleId={mid}
                title={mod?.label || mid}
                description={mod?.id}
              />
            </div>
          );
        })()}
        {gosterge === "storyforge" && (
          <div className="modul-card">
            <LazyStoryForge
              initialTab={storyForgeTab}
              onOpenCategoryHub={() => { setGosterge("category_hub"); setSeciliModul(null); setSonuc(null); setHata(""); }}
            />
          </div>
        )}
        {gosterge === "sss_automation" && (
          <div className="modul-card">
            <SSSAutomation importHint={sssImportHint} />
          </div>
        )}
        {gosterge === "domain_manager" && (
          <div className="modul-card">
            <DomainManager onNavigate={navigateTo} />
          </div>
        )}
        {gosterge === "users" && (
          <div className="modul-card">
            <UsersRoles />
          </div>
        )}
        {(gosterge === "projects" || gosterge === "project_wizard" || (typeof gosterge === "string" && gosterge.startsWith("project_detail:"))) && (
          <ProjectsHub setGosterge={setGosterge} />
        )}
        {gosterge === "modul" && seciliModul && modulDetay && (
          <div className="modul-card">
            <ModulUI modul={modulDetay} sonuc={sonuc} setSonuc={setSonuc} yukleniyor={yukleniyor} setYukleniyor={setYukleniyor} hata={hata} setHata={setHata} />
          </div>
        )}
        </Suspense>
        </HivePageFrame>
      </div>
    </div>
  );
}

export default App;
