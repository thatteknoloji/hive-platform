import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
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
} from "../components/HiveModuleUI";

function apiError(e) {
  return e?.response?.data?.detail || e?.hiveMessage || e?.message || "API hatası";
}

export default function LeadScraper() {
  const [kelime, setKelime] = useState("");
  const [url, setUrl] = useState("");
  const [adet, setAdet] = useState(25);
  const [health, setHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    try {
      const res = await API.get("/api/leadscraper/health");
      setHealth(res.data);
    } catch {
      setHealth(null);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const collect = async () => {
    if (!kelime.trim() && !url.trim()) {
      setError("Keyword veya URL gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/leadscraper/collect", {
        kelime: kelime.trim(),
        url: url.trim(),
        adet: Number(adet),
      });
      if (res.data.status === "hata" || res.data.hata) {
        setError(res.data.mesaj || res.data.hata);
        setResult(null);
      } else {
        setResult(res.data);
        setMessage(res.data.durum || `${res.data.bulunan_lead} lead`);
      }
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const leads = result?.leads || [];

  return (
    <HiveShell
      title="📋 Lead Scraper"
      subtitle="E-posta ve telefon toplama — doğrudan URL veya SearXNG/Tavily arama"
    >
      <HiveToolbar>
        <span className={`hm-badge hm-badge-${health?.searxng ? "low" : "medium"}`}>
          SearXNG: {health?.searxng ? "✓" : "—"}
        </span>
        <span className={`hm-badge hm-badge-${health?.tavily ? "low" : "medium"}`}>
          Tavily: {health?.tavily ? "✓" : "—"}
        </span>
        <HiveBtn variant="ghost" onClick={refresh}>Yenile</HiveBtn>
      </HiveToolbar>

      {!url && !health?.searxng && !health?.tavily && (
        <HiveAlert type="warn">
          Keyword araması için SearXNG veya Tavily gerekir. Doğrudan hedef URL ile de çalışır.
        </HiveAlert>
      )}
      {message && <HiveAlert type="ok">{message}</HiveAlert>}
      {error && <HiveAlert type="err">{error}</HiveAlert>}

      <HivePanel>
        <div className="hm-form-row">
          <HiveField label="Anahtar Kelime (arama)">
            <HiveInput value={kelime} onChange={(e) => setKelime(e.target.value)} placeholder="kuşadası otel" />
          </HiveField>
          <HiveField label="veya Hedef URL">
            <HiveInput value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/iletisim" />
          </HiveField>
          <HiveField label="Max lead">
            <HiveInput type="number" min={1} max={50} value={adet} onChange={(e) => setAdet(e.target.value)} />
          </HiveField>
        </div>
        <HiveBtn onClick={collect} disabled={loading}>Lead Topla</HiveBtn>
      </HivePanel>

      {result && (
        <>
          <HiveStatGrid items={[
            ["Lead", result.bulunan_lead],
            ["Kaynak", result.kaynak],
            ["Taranan sayfa", result.scraped_pages],
          ]} />
          <HiveTable
            columns={[
              { key: "type", label: "Tip" },
              { key: "value", label: "Değer" },
              { key: "source_url", label: "Kaynak" },
              { key: "page_title", label: "Sayfa" },
            ]}
            rows={leads.map((l, i) => ({
              id: i,
              type: l.type,
              value: l.value,
              source_url: l.source_url,
              page_title: (l.page_title || "—").slice(0, 50),
            }))}
            emptyText="Lead bulunamadı"
          />
        </>
      )}
    </HiveShell>
  );
}
