import React, { useState } from "react";
import API from "../api";


export default function Mystic() {
  const [domain, setDomain] = useState("");
  const [hedef, setHedef] = useState("");
  const [exportFormat, setExportFormat] = useState("csv");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [taraSonuc, setTaraSonuc] = useState(null);
  const [disavowSonuc, setDisavowSonuc] = useState(null);
  const [misillemeSonuc, setMisillemeSonuc] = useState(null);
  const [exportSonuc, setExportSonuc] = useState(null);

  const handleTara = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, tara: true }));
    try { const res = await API.post("/api/mystic/tara", { domain }); setTaraSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, tara: false }));
  };

  const handleDisavow = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, disavow: true }));
    try { const res = await API.post("/api/mystic/disavow", { domain }); setDisavowSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, disavow: false }));
  };

  const handleMisilleme = async () => {
    if (!hedef) { setHata("Hedef gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, misilleme: true }));
    try { const res = await API.post("/api/mystic/misilleme", { hedef }); setMisillemeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, misilleme: false }));
  };

  const handleExport = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, export_: true }));
    try { const res = await API.post("/api/mystic/export", { domain, format: exportFormat }); setExportSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, export_: false }));
  };

  const SonucKarti = ({ data }) => data && (
    <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", marginTop: "1rem" }}>
      <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto" }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">🛡️</div>
        <div className="info">
          <h2>Mystic Return – Spam Backlink Tespit ve Müdahale</h2>
          <p>Spam backlinkleri tespit et, disavow dosyası oluştur ve misilleme yap.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 2, minWidth: 250 }}>
            <label>Domain</label>
            <input value={domain} onChange={e => setDomain(e.target.value)} placeholder="örn: kendi-siteniz.com" />
          </div>
          <div className="form-grup" style={{ flex: 2, minWidth: 250 }}>
            <label>Misilleme Hedefi</label>
            <input value={hedef} onChange={e => setHedef(e.target.value)} placeholder="örn: rakipsitesi.com" />
          </div>
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-primary" onClick={handleTara} disabled={loading.tara}>
          {loading.tara ? "Taranıyor..." : "🔍 Spam Tara"}
        </button>
        <button className="btn btn-outline" onClick={handleDisavow} disabled={loading.disavow}>
          {loading.disavow ? "⏳" : "📄 Disavow Oluştur"}
        </button>
        <button className="btn btn-danger" onClick={handleMisilleme} disabled={loading.misilleme}>
          {loading.misilleme ? "⏳" : "⚔️ Misilleme Yap"}
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
      <SonucKarti data={taraSonuc} />
      <SonucKarti data={disavowSonuc} />
      <SonucKarti data={misillemeSonuc} />
      <SonucKarti data={exportSonuc} />
    </div>
  );
}
