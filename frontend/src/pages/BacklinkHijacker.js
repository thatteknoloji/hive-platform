import React, { useState } from "react";
import API from "../api";


export default function BacklinkHijacker() {
  const [domain, setDomain] = useState("");
  const [exportFormat, setExportFormat] = useState("csv");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [calSonuc, setCalSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [analizSonuc, setAnalizSonuc] = useState(null);
  const [exportSonuc, setExportSonuc] = useState(null);

  const handleCal = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, cal: true }));
    try { const res = await API.post("/api/backlinkhijacker", { domain }); setCalSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, cal: false }));
  };

  const handleTara = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, tara: true }));
    try { const res = await API.post("/api/backlinkhijacker/tara", { domain }); setCalSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, tara: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try { const res = await API.get("/api/backlinkhijacker/listele"); setListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleAnaliz = async () => {
    setHata(""); setLoading(l => ({ ...l, analiz: true }));
    try { const res = await API.get("/api/backlinkhijacker/analiz"); setAnalizSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, analiz: false }));
  };

  const handleExport = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, export_: true }));
    try { const res = await API.post("/api/backlinkhijacker/export", { domain, format: exportFormat }); setExportSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, export_: false }));
  };

  const SonucKarti = ({ data, borderColor }) => data && (
    <div style={{ background: "var(--bg3)", border: `1px solid ${borderColor || "var(--border)"}`, borderRadius: 8, padding: "1rem", marginTop: "1rem" }}>
      <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto" }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">🕷️</div>
        <div className="info">
          <h2>Backlink Hijacker – Kırık Backlink Çalma</h2>
          <p>Rakiplerin kırık backlinklerini tespit et, çal ve kendi sitene yönlendir.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 2, minWidth: 250 }}>
            <label>Rakip Domain</label>
            <input value={domain} onChange={e => setDomain(e.target.value)} placeholder="örn: rakipsitesi.com" />
          </div>
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-danger" onClick={handleCal} disabled={loading.cal}>
          {loading.cal ? "Çalınıyor..." : "🕷️ Backlink Çal"}
        </button>
        <button className="btn btn-outline" onClick={handleTara} disabled={loading.tara}>
          {loading.tara ? "Taranıyor..." : "🔍 Hedef Tara"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Çalınan Backlinkler"}
        </button>
        <button className="btn btn-outline" onClick={handleAnaliz} disabled={loading.analiz}>
          {loading.analiz ? "⏳" : "📊 Analiz Et"}
        </button>
        <div style={{ display: "flex", gap: "0.3rem", alignItems: "center" }}>
          <select value={exportFormat} onChange={e => setExportFormat(e.target.value)}
            style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.25rem", fontSize: "0.8rem" }}>
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
            <option value="txt">TXT</option>
          </select>
          <button className="btn btn-outline" onClick={handleExport} disabled={loading.export_}>
            {loading.export_ ? "⏳" : "📤 Dışa Aktar"}
          </button>
        </div>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}
      <SonucKarti data={calSonuc} />
      <SonucKarti data={listeSonuc} />
      <SonucKarti data={analizSonuc} />
      <SonucKarti data={exportSonuc} />
    </div>
  );
}
