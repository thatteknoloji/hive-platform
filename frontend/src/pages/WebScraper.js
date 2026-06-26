import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { useProjectSiteField, useProjectDomainField, useProjectIdField } from "../hooks/useProjectSiteField";

import {
  HiveShell,
  HiveAlert,
  HiveToolbar,
  HivePanel,
  HiveStatGrid,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveTable,
  HiveCard,
} from "../components/HiveModuleUI";

function apiError(e) {
  return e?.response?.data?.detail || e?.hiveMessage || e?.message || "API hatası";
}

export default function WebScraper() {
  const [url, setUrl] = useProjectSiteField();
  const [derinlik, setDerinlik] = useState(1);
  const [maxPages, setMaxPages] = useState(8);
  const [health, setHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    try {
      const res = await API.get("/api/webscraper/health");
      setHealth(res.data);
    } catch {
      setHealth(null);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const runCrawl = async () => {
    if (!url.trim()) { setError("URL gerekli"); return; }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/webscraper/crawl", {
        url: url.trim(),
        derinlik: Number(derinlik),
        max_pages: Number(maxPages),
      });
      if (res.data.status === "hata" || res.data.hata) {
        setError(res.data.mesaj || res.data.hata);
        setResult(null);
      } else {
        setResult(res.data);
        setMessage(`${res.data.taranan_sayfa} sayfa kazındı`);
      }
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const exportData = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/webscraper/export", {
        url: url.trim(),
        derinlik: Number(derinlik),
        format: "csv",
      });
      setMessage(`Export: ${res.data.rows || 0} satır — ${res.data.path || "hazır"}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const pages = result?.sayfalar || [];

  return (
    <HiveShell title="🕷️ Web Scraper" subtitle="Hedef siteden gerçek HTTP/HTML kazıma — başlık, meta, link, görsel, içerik">
      <HiveToolbar>
        <span className="hm-badge hm-badge-low">{health?.engine || "requests+bs4"}</span>
        <HiveBtn variant="ghost" onClick={refresh}>Yenile</HiveBtn>
      </HiveToolbar>

      {message && <HiveAlert type="ok">{message}</HiveAlert>}
      {error && <HiveAlert type="err">{error}</HiveAlert>}

      <HivePanel>
        <div className="hm-form-row">
          <HiveField label="Hedef URL">
            <HiveInput value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com" />
          </HiveField>
          <HiveField label="Derinlik (1-3)">
            <HiveInput type="number" min={1} max={3} value={derinlik} onChange={(e) => setDerinlik(e.target.value)} />
          </HiveField>
          <HiveField label="Max sayfa">
            <HiveInput type="number" min={1} max={25} value={maxPages} onChange={(e) => setMaxPages(e.target.value)} />
          </HiveField>
        </div>
        <HiveToolbar>
          <HiveBtn onClick={runCrawl} disabled={loading}>Kazımayı Başlat</HiveBtn>
          <HiveBtn variant="secondary" onClick={exportData} disabled={loading || !result}>CSV Export</HiveBtn>
        </HiveToolbar>
      </HivePanel>

      {result && (
        <>
          <HiveStatGrid items={[
            ["Sayfa", result.taranan_sayfa],
            ["Link", result.toplam_link],
            ["Görsel", result.toplam_gorsel],
            ["Veri noktası", result.toplam_veri_noktasi],
          ]} />
          <HiveTable
            columns={[
              { key: "url", label: "URL" },
              { key: "title", label: "Başlık" },
              { key: "words", label: "Kelime" },
              { key: "links", label: "Link" },
              { key: "types", label: "Tipler" },
            ]}
            rows={pages.map((p) => ({
              id: p.url,
              url: p.url,
              title: (p.title || "—").slice(0, 60),
              words: p.word_count ?? "—",
              links: (p.links || []).length,
              types: (p.tipler || []).join(", "),
            }))}
            emptyText="Sonuç yok"
          />
          {pages[0] && (
            <HiveCard title="İlk sayfa özeti" meta={pages[0].url}>
              <p className="hm-empty">{pages[0].meta_description || "Meta yok"}</p>
              <pre className="hm-code" style={{ maxHeight: 160, overflow: "auto" }}>
                {(pages[0].text_excerpt || "").slice(0, 800)}
              </pre>
            </HiveCard>
          )}
        </>
      )}
    </HiveShell>
  );
}
