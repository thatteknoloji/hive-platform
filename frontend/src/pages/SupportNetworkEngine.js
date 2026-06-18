import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveBtn,
  HiveTable,
  HiveCard,
  HiveField,
  HiveInput,
  HiveCheck,
  HiveMissionBoard,
  HiveContextBar,
  HiveSection,
} from "../components/HiveModuleUI";

const API_PREFIX = "/api/support-network";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "domains", label: "Domains" },
  { id: "authority", label: "Authority" },
  { id: "links", label: "Links" },
  { id: "keywords", label: "Keywords" },
  { id: "coverage", label: "Coverage" },
  { id: "publishers", label: "Publishers" },
  { id: "gaps", label: "Gaps" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

const REPORT_TYPES = [
  { id: "overview", label: "Network Overview" },
  { id: "authority", label: "Authority Report" },
  { id: "links", label: "Link Report" },
  { id: "keywords", label: "Keyword Distribution" },
  { id: "publisher", label: "Publisher Report" },
  { id: "geo", label: "GEO Coverage" },
  { id: "entity", label: "Entity Coverage" },
  { id: "risk", label: "Risk Report" },
  { id: "growth", label: "Growth Opportunities" },
  { id: "health", label: "Network Health Report" },
];

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

export default function SupportNetworkEngine() {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [dashData, setDashData] = useState(null);
  const [settings, setSettings] = useState(null);
  const [domains, setDomains] = useState([]);
  const [grouped, setGrouped] = useState({});
  const [authority, setAuthority] = useState(null);
  const [links, setLinks] = useState([]);
  const [keywords, setKeywords] = useState(null);
  const [healthScore, setHealthScore] = useState(null);
  const [publishers, setPublishers] = useState(null);
  const [gaps, setGaps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exportPath, setExportPath] = useState("");
  const [roleDomain, setRoleDomain] = useState("");
  const [roleSuggestion, setRoleSuggestion] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [h, s, dash, domRes, auth, kw, gp, pub] = await Promise.all([
        API.get(`${API_PREFIX}/health`),
        API.get(`${API_PREFIX}/settings`),
        API.get(`${API_PREFIX}/dashboard`).catch(() => ({ data: null })),
        API.get(`${API_PREFIX}/domains`).catch(() => ({ data: { domains: [], grouped: {} } })),
        API.get(`${API_PREFIX}/authority`).catch(() => ({ data: null })),
        API.get(`${API_PREFIX}/keywords`),
        API.get(`${API_PREFIX}/gaps`),
        API.get(`${API_PREFIX}/publishers`).catch(() => ({ data: null })),
      ]);
      setHealth(h.data);
      setSettings(s.data.settings);
      setDashData(dash.data);
      setDomains(domRes.data.domains || []);
      setGrouped(domRes.data.grouped || {});
      setHealthScore({
        overall_network_score: dash.data?.overall_network_score,
        scores: dash.data?.health_scores,
        domain_count: dash.data?.domain_count ?? domRes.data.count,
        roles_present: dash.data?.roles_present,
      });
      setAuthority(auth.data);
      setKeywords(kw.data);
      setGaps(gp.data.gaps || []);
      setPublishers(pub.data);
    } catch (e) {
      setError(apiError(e));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const runSync = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/sync`);
      setMessage(`Sync tamamlandı — ${res.data.results?.domains?.count || 0} domain`);
      if (res.data.results?.links?.plans) setLinks(res.data.results.links.plans);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadLinks = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.get(`${API_PREFIX}/links`);
      setLinks(res.data.plans || []);
      setTab("links");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (reportType) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/report?report_type=${reportType}`);
      setExportPath(res.data.path || "");
      setMessage(`${reportType} raporu oluşturuldu`);
      setTab("reports");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async (patch) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/settings`, patch);
      setSettings(res.data.settings);
      setMessage("Ayarlar kaydedildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const suggestRole = async () => {
    if (!roleDomain.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/suggest-role`, { domain: roleDomain });
      setRoleSuggestion(res.data);
      setMessage(`Önerilen rol: ${res.data.role_label}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const dash = dashData || health?.dashboard || {};
  const integrationErrors = health?.integration_errors || dashData?.integration_errors || [];

  const AUTH_SECTIONS = [
    ["Authority Taşıyan", "carrying_authority"],
    ["Authority Kaybeden", "losing_authority"],
    ["Katkı Sağlamayan", "no_contribution"],
    ["İçerik Üretmiyor", "no_content"],
    ["Fazla Outbound", "high_outbound"],
    ["Link Alamayan", "no_inbound_links"],
    ["Boşa Çalışan", "idle_wasting"],
    ["Money Site Destekleyen", "supporting_money_site"],
  ];

  return (
    <HiveShell title="Support Network Engine" subtitle="Domain ağı orkestrasyonu — discovery, authority, keyword governance, publisher kanalları">
      {message && <HiveAlert type="ok">{message}</HiveAlert>}
      {error && <HiveAlert type="err">{error}</HiveAlert>}
      {integrationErrors.length > 0 && (
        <HiveAlert type="err">
          Entegrasyon uyarıları: {integrationErrors.map((e) => e.module || e).join(", ")}
        </HiveAlert>
      )}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <HivePanel title="Network Overview" description="Support ağı skoru ve gap durumu">
          <HiveMissionBoard
            primary={[
              { label: "Network Score", value: dash.overall_network_score ?? dash.network_score ?? "—", tone: "accent" },
              { label: "Domains", value: dash.domain_count ?? dash.domains ?? "—" },
              { label: "Gaps", value: dash.gap_count ?? "—", tone: (dash.gap_count || 0) > 0 ? "warn" : "ok" },
            ]}
            secondary={[
              { label: "Cannibalization", value: dash.cannibalization_risks ?? "—" },
              { label: "Last Sync", value: (health?.last_sync_at || dash.last_sync_at || "—").toString().slice(0, 16) },
            ]}
          />
          <HiveContextBar>
            <HiveBtn onClick={runSync} disabled={loading}>Tam Sync</HiveBtn>
            <HiveBtn variant="outline" onClick={loadLinks} disabled={loading}>Link Planı Üret</HiveBtn>
            <HiveBtn variant="outline" onClick={refresh} disabled={loading}>Yenile</HiveBtn>
          </HiveContextBar>
          {healthScore?.scores && (
            <HiveSection title="Health Breakdown">
              <HiveStatGrid
                columns={4}
                items={Object.entries(healthScore.scores).map(([k, v]) => ({
                  label: k.replace(/_/g, " "),
                  value: v,
                }))}
              />
            </HiveSection>
          )}
          {(dash.top_domains || []).length > 0 && (
            <HiveSection title="Top Domains">
              <HiveTable
                columns={[
                  { key: "domain", label: "Domain" },
                  { key: "role", label: "Rol" },
                  { key: "traffic_score", label: "Trafik Skoru" },
                ]}
                rows={dash.top_domains}
              />
            </HiveSection>
          )}
        </HivePanel>
      )}

      {tab === "domains" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "domain", label: "Domain" },
              { key: "role_label", label: "Rol" },
              { key: "network_group", label: "Grup" },
              { key: "authority_score", label: "Authority" },
              { key: "quality_score", label: "Quality" },
              { key: "content_count", label: "İçerik" },
              { key: "supports_domain", label: "Desteklediği" },
              { key: "publish_channels", label: "Kanallar", render: (r) => (r.publish_channels || []).join(", ") },
              { key: "quality_gate_status", label: "Gate" },
            ]}
            rows={domains}
            emptyText="Domain bulunamadı — Network Replicator'da ağ oluşturun veya Tam Sync çalıştırın"
          />
        </HivePanel>
      )}

      {tab === "authority" && (
        <HivePanel>
          {!authority?.success ? (
            <HiveAlert type="err">{authority?.error || "Authority analizi için domain gerekli"}</HiveAlert>
          ) : (
            <>
              <HiveStatGrid items={[
                ["Ort. Authority", authority.summary?.avg_authority],
                ["Toplam Domain", authority.summary?.total_domains],
              ]} />
              {AUTH_SECTIONS.map(([title, key]) => (
                <HiveCard key={key} title={title}>
                  <HiveTable
                    columns={[
                      { key: "domain", label: "Domain" },
                      { key: "role", label: "Rol" },
                      { key: "authority_score", label: "Skor" },
                      { key: "supports", label: "Destek" },
                    ]}
                    rows={authority[key] || []}
                    emptyText="Kayıt yok"
                  />
                </HiveCard>
              ))}
            </>
          )}
        </HivePanel>
      )}

      {tab === "links" && (
        <HivePanel>
          <HiveBtn onClick={loadLinks} disabled={loading} style={{ marginBottom: 12 }}>Plan Üret</HiveBtn>
          <HiveTable
            columns={[
              { key: "from_domain", label: "Kaynak" },
              { key: "to_domain", label: "Hedef" },
              { key: "suggested_page", label: "Sayfa" },
              { key: "anchor_text", label: "Anchor" },
              { key: "reason", label: "Sebep" },
              { key: "action", label: "Aksiyon" },
            ]}
            rows={links}
            emptyText="Link planı yok — sadece öneri, gerçek link eklenmez"
          />
        </HivePanel>
      )}

      {tab === "keywords" && (
        <HivePanel>
          {keywords && (
            <>
              <HiveStatGrid items={[
                ["Benzersiz Keyword", keywords.unique_keywords],
                ["Risk Sayısı", keywords.risk_count],
                ["Ort. Risk Skoru", keywords.avg_risk_score],
              ]} />
              <HiveCard title="Cannibalization (network / cluster / city)">
                <HiveTable
                  columns={[
                    { key: "keyword", label: "Keyword" },
                    { key: "risk_score", label: "Risk" },
                    { key: "risk", label: "Seviye" },
                    { key: "scope", label: "Kapsam", render: (r) => (r.scope || []).join(", ") },
                    { key: "domains", label: "Domainler", render: (r) => (r.domains || []).join(", ") },
                  ]}
                  rows={keywords.cannibalization_risks || []}
                  emptyText="Cannibalization riski yok"
                />
              </HiveCard>
            </>
          )}
        </HivePanel>
      )}

      {tab === "coverage" && (
        <HivePanel>
          {healthScore?.scores ? (
            <>
              <HiveStatGrid items={[
                ["Network Skoru", healthScore.overall_network_score],
                ["Domain", healthScore.domain_count],
              ]} />
              <HiveCard title="Skor Bileşenleri">
                <HiveStatGrid
                  items={Object.entries(healthScore.scores).map(([k, v]) => [k.replace(/_/g, " "), v])}
                />
              </HiveCard>
            </>
          ) : (
            <HiveAlert type="err">Coverage için domain gerekli</HiveAlert>
          )}
        </HivePanel>
      )}

      {tab === "publishers" && (
        <HivePanel>
          {publishers ? (
            <>
              <HiveCard title="Kanal Bazlı">
                <HiveTable
                  columns={[
                    { key: "channel", label: "Kanal" },
                    { key: "domain_count", label: "Domain" },
                    { key: "domains", label: "Liste", render: (r) => (r.domains || []).join(", ") },
                  ]}
                  rows={publishers.by_channel || []}
                  emptyText="Yayın kanalı verisi yok"
                />
              </HiveCard>
              <HiveCard title="Domain × Kanal">
                <HiveTable
                  columns={[
                    { key: "domain", label: "Domain" },
                    { key: "role", label: "Rol" },
                    { key: "channels", label: "Kanallar", render: (r) => (r.channels || []).join(", ") },
                    { key: "publisher_queue", label: "Kuyruk" },
                  ]}
                  rows={publishers.by_domain || []}
                />
              </HiveCard>
            </>
          ) : (
            <HiveAlert type="err">Publisher verisi yüklenemedi</HiveAlert>
          )}
        </HivePanel>
      )}

      {tab === "gaps" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "type", label: "Tip" },
              { key: "label", label: "Etiket" },
              { key: "item", label: "Öğe" },
              { key: "domain", label: "Domain" },
              { key: "count", label: "Sayı" },
            ]}
            rows={gaps}
            emptyText="Gap bulunamadı"
          />
        </HivePanel>
      )}

      {tab === "reports" && (
        <HivePanel>
          <p className="hm-meta-line">Raporlar backend/reports altına JSON olarak yazılır.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            {REPORT_TYPES.map((r) => (
              <HiveBtn key={r.id} variant="outline" onClick={() => exportReport(r.id)} disabled={loading}>
                {r.label}
              </HiveBtn>
            ))}
          </div>
          {exportPath && <HiveCard title="Son Rapor">{exportPath}</HiveCard>}
        </HivePanel>
      )}

      {tab === "settings" && settings && (
        <HivePanel>
          <HiveCheck
            label="Engine aktif"
            checked={!!settings.enabled}
            onChange={(e) => saveSettings({ enabled: e.target.checked })}
          />
          <HiveField label="Cannibalization eşiği (0-1)">
            <HiveInput
              type="number"
              step="0.05"
              value={settings.keyword_cannibalization_threshold}
              onChange={(e) => setSettings({ ...settings, keyword_cannibalization_threshold: parseFloat(e.target.value) || 0.85 })}
            />
          </HiveField>
          <HiveBtn onClick={() => saveSettings(settings)} disabled={loading} style={{ marginTop: 12 }}>
            Kaydet
          </HiveBtn>
          <HiveCard title="Rol Önerisi (Network Replicator)">
            <HiveField label="Domain">
              <HiveInput value={roleDomain} onChange={(e) => setRoleDomain(e.target.value)} placeholder="ornek.info" />
            </HiveField>
            <HiveBtn onClick={suggestRole} disabled={loading || !roleDomain.trim()} style={{ marginTop: 8 }}>
              Rol Öner
            </HiveBtn>
            {roleSuggestion && (
              <p style={{ marginTop: 8 }}>
                {roleSuggestion.domain} → <strong>{roleSuggestion.role_label}</strong> ({roleSuggestion.network_group})
              </p>
            )}
          </HiveCard>
        </HivePanel>
      )}
    </HiveShell>
  );
}
