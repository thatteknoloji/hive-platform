import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";

import {
  HiveShell,
  HiveAlert,
  HiveToolbar,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveTable,
  HiveCard,
  HiveSelect,
  HiveFormRow,
} from "../components/HiveModuleUI";

const TABS = [
  { id: "track", label: "Sıra Kontrol" },
  { id: "keywords", label: "Kayıtlı Kelimeler" },
  { id: "bulk", label: "Toplu Kontrol" },
];

function apiError(e) {
  return e?.response?.data?.detail || e?.hiveMessage || e?.message || "API hatası";
}

export default function RankTracker() {
  const [tab, setTab] = useState("track");
  const [kelime, setKelime] = useState("");
  const [domain, setDomain] = useProjectDomainField();
  const [sehir, setSehir] = useState("kuşadası");
  const [kelimeList, setKelimeList] = useState("");
  const [exportFormat, setExportFormat] = useState("csv");
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hata, setHata] = useState("");
  const [mesaj, setMesaj] = useState("");
  const [takipSonuc, setTakipSonuc] = useState(null);
  const [keywords, setKeywords] = useState([]);
  const [topluSonuc, setTopluSonuc] = useState(null);
  const [exportSonuc, setExportSonuc] = useState(null);

  const loadHealth = useCallback(async () => {
    try {
      const res = await API.get("/api/ranktracker/health");
      setHealth(res.data);
    } catch {
      setHealth(null);
    }
  }, []);

  const loadKeywords = useCallback(async () => {
    try {
      const res = await API.get("/api/ranktracker/keywordlar");
      setKeywords(res.data.keywords || []);
    } catch {
      setKeywords([]);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    loadKeywords();
  }, [loadHealth, loadKeywords]);

  const handleTakip = async () => {
    if (!kelime.trim()) { setHata("Kelime gerekli"); return; }
    setHata(""); setMesaj(""); setLoading(true);
    try {
      const res = await API.post("/api/ranktracker", { kelime: kelime.trim(), domain, sehir });
      const data = res.data;
      if (data.status === "hata" || data.hata) {
        setHata(data.mesaj || data.hata);
        setTakipSonuc(null);
      } else {
        setTakipSonuc(data);
        setMesaj(`Sıra: ${data.guncel_pozisyon ?? "—"} (${data.kaynak})`);
        await loadKeywords();
      }
    } catch (e) {
      setHata(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleKaydet = async () => {
    if (!kelime.trim()) { setHata("Kelime gerekli"); return; }
    setLoading(true);
    try {
      const res = await API.post("/api/ranktracker/keyword", { kelime: kelime.trim(), domain });
      setMesaj(res.data.durum === "zaten_var" ? "Zaten kayıtlı" : "Keyword kaydedildi");
      await loadKeywords();
    } catch (e) {
      setHata(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleToplu = async () => {
    const lines = kelimeList.split("\n").map((s) => s.trim()).filter(Boolean);
    if (!lines.length) { setHata("Kelimeler gerekli"); return; }
    setLoading(true);
    setHata("");
    try {
      const kelimeler = lines.map((k) => ({ kelime: k, domain, sehir }));
      const res = await API.post("/api/ranktracker/toplu", { kelimeler });
      setTopluSonuc(res.data);
      setMesaj(`${res.data.toplam} keyword kontrol edildi`);
      await loadKeywords();
    } catch (e) {
      setHata(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!kelime.trim()) { setHata("Kelime gerekli"); return; }
    setLoading(true);
    try {
      const res = await API.post("/api/ranktracker/export", { kelime: kelime.trim(), format: exportFormat });
      setExportSonuc(res.data);
      setMesaj("Export hazır");
    } catch (e) {
      setHata(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSil = async (k) => {
    setLoading(true);
    try {
      await API.delete(`/api/ranktracker/keyword/${encodeURIComponent(k)}`);
      setMesaj("Silindi");
      await loadKeywords();
    } catch (e) {
      setHata(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const gscOk = health?.search_console;
  const dfsOk = health?.dataforseo;

  return (
    <HiveShell
      title="📊 Rank Tracker"
      subtitle="Günlük keyword sıralama — DataForSEO SERP + Google Search Console"
    >
      <HiveToolbar>
        <span className={`hm-badge hm-badge-${gscOk ? "low" : "medium"}`}>
          GSC: {gscOk ? "✓ bağlı" : "eksik"}
        </span>
        <span className={`hm-badge hm-badge-${dfsOk ? "low" : "medium"}`}>
          DataForSEO: {dfsOk ? "✓ bağlı" : "eksik"}
        </span>
        <HiveBtn variant="ghost" onClick={loadHealth}>Yenile</HiveBtn>
      </HiveToolbar>

      {!health?.ready && (
        <HiveAlert type="warn">
          Provider eksik — `.env` içine DATAFORSEO_LOGIN/PASSWORD veya GOOGLE_CLIENT_* + GOOGLE_REFRESH_TOKEN + GSC_SITE_URL ekleyin.
        </HiveAlert>
      )}
      {mesaj && <HiveAlert type="ok">{mesaj}</HiveAlert>}
      {hata && <HiveAlert type="err">{hata}</HiveAlert>}

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "track" && (
        <HivePanel>
          <HiveFormRow>
            <HiveField label="Anahtar Kelime">
              <HiveInput value={kelime} onChange={(e) => setKelime(e.target.value)} placeholder="kuşadası gece hayatı" />
            </HiveField>
            <HiveField label="Domain (DataForSEO için)">
              <HiveInput value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="example.com" />
            </HiveField>
            <HiveField label="Şehir">
              <HiveInput value={sehir} onChange={(e) => setSehir(e.target.value)} placeholder="kuşadası" />
            </HiveField>
          </HiveFormRow>
          <HiveToolbar>
            <HiveBtn onClick={handleTakip} disabled={loading}>Sıra Kontrol Et</HiveBtn>
            <HiveBtn variant="secondary" onClick={handleKaydet} disabled={loading}>Keyword Kaydet</HiveBtn>
            <HiveField label="Export">
              <HiveSelect value={exportFormat} onChange={(e) => setExportFormat(e.target.value)}>
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
                <option value="txt">TXT</option>
              </HiveSelect>
            </HiveField>
            <HiveBtn variant="ghost" onClick={handleExport} disabled={loading}>Dışa Aktar</HiveBtn>
          </HiveToolbar>

          {takipSonuc && (
            <HiveCard title={takipSonuc.kelime} meta={`Kaynak: ${takipSonuc.kaynak}`}>
              <HiveStatGrid items={[
                ["Güncel Sıra", takipSonuc.guncel_pozisyon ?? "—"],
                ["Önceki", takipSonuc.onceki_pozisyon ?? "—"],
                ["Değişim", takipSonuc.degisim ?? "—"],
                ["Trend", takipSonuc.trend ?? "—"],
                ["GSC Tıklama", takipSonuc.search_console?.clicks ?? "—"],
                ["GSC Gösterim", takipSonuc.search_console?.impressions ?? "—"],
              ]} />
              {takipSonuc.dataforseo?.first_url && (
                <p className="hm-empty">
                  URL: <a href={takipSonuc.dataforseo.first_url} target="_blank" rel="noreferrer">{takipSonuc.dataforseo.first_url}</a>
                </p>
              )}
              <HiveTable
                columns={[
                  { key: "tarih", label: "Tarih" },
                  { key: "pozisyon", label: "Pozisyon" },
                  { key: "kaynak", label: "Kaynak" },
                ]}
                rows={(takipSonuc.gecmis || []).map((g, i) => ({
                  id: i,
                  tarih: g.tarih || g.gun || "—",
                  pozisyon: g.pozisyon ?? "—",
                  kaynak: g.kaynak || takipSonuc.kaynak,
                }))}
                emptyText="Geçmiş yok — kontrol sonrası dolacak"
              />
            </HiveCard>
          )}
        </HivePanel>
      )}

      {tab === "keywords" && (
        <HivePanel>
          <HiveTable
            columns={[
              { key: "kelime", label: "Keyword" },
              { key: "domain", label: "Domain" },
              { key: "pozisyon", label: "Son Sıra" },
              { key: "kaynak", label: "Kaynak" },
              {
                key: "actions",
                label: "",
                render: (row) => (
                  <HiveBtn size="sm" variant="ghost" onClick={() => handleSil(row.kelime)}>Sil</HiveBtn>
                ),
              },
            ]}
            rows={keywords.map((k) => ({
              id: k.kelime,
              kelime: k.kelime,
              domain: k.domain || "—",
              pozisyon: k.pozisyon ?? "—",
              kaynak: k.kaynak || "—",
            }))}
            emptyText="Kayıtlı keyword yok"
          />
        </HivePanel>
      )}

      {tab === "bulk" && (
        <HivePanel>
          <HiveField label="Kelimeler (her satır bir keyword)">
            <textarea
              className="hm-input"
              rows={6}
              value={kelimeList}
              onChange={(e) => setKelimeList(e.target.value)}
              placeholder={"kuşadası gece hayatı\nkuşadası escort"}
            />
          </HiveField>
          <HiveBtn onClick={handleToplu} disabled={loading} style={{ marginTop: 8 }}>
            Toplu Kontrol Et
          </HiveBtn>
          {topluSonuc?.sonuclar?.length > 0 && (
            <HiveTable
              columns={[
                { key: "kelime", label: "Keyword" },
                { key: "guncel_pozisyon", label: "Sıra" },
                { key: "kaynak", label: "Kaynak" },
                { key: "trend", label: "Trend" },
              ]}
              rows={topluSonuc.sonuclar.map((s) => ({
                id: s.kelime,
                kelime: s.kelime,
                guncel_pozisyon: s.guncel_pozisyon ?? "—",
                kaynak: s.kaynak,
                trend: s.trend,
              }))}
            />
          )}
        </HivePanel>
      )}

      {exportSonuc?.icerik && (
        <HiveCard title="Export">
          <pre className="hm-code" style={{ maxHeight: 200, overflow: "auto" }}>{exportSonuc.icerik.slice(0, 3000)}</pre>
        </HiveCard>
      )}
    </HiveShell>
  );
}
