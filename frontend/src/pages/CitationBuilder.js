import React, { useState } from "react";
import API from "../api";


export default function CitationBuilder() {
  const [isletme, setIsletme] = useState("");
  const [exportFormat, setExportFormat] = useState("csv");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [citationSonuc, setCitationSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [dogrulaSonuc, setDogrulaSonuc] = useState(null);
  const [exportSonuc, setExportSonuc] = useState(null);

  const handleCitation = async () => {
    if (!isletme) { setHata("İşletme adı gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, citation: true }));
    try { const res = await API.post("/api/citation", { isletme }); setCitationSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, citation: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/citation/liste"); setListeSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, liste: false }));
  };

  const handleDogrula = async () => {
    if (!isletme) { setHata("İşletme adı gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, dogrula: true }));
    try { const res = await API.post("/api/citation/dogrula", { isletme }); setDogrulaSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, dogrula: false }));
  };

  const handleExport = async () => {
    if (!isletme) { setHata("İşletme adı gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, export_: true }));
    try { const res = await API.post("/api/citation/export", { isletme, format: exportFormat }); setExportSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, export_: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">📑</div>
        <div className="info"><h2>Citation Builder</h2><p>İşletme alıntıları oluştur, doğrula ve dışa aktar</p></div>
      </div>
      <div className="form-grup">
        <label>İşletme Adı</label>
        <input value={isletme} onChange={e => setIsletme(e.target.value)} placeholder="örn: Cafe Vienna Kuşadası" />
      </div>
      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleCitation} disabled={loading.citation}>
          {loading.citation ? "⏳" : "📑 Citation Oluştur"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleDogrula} disabled={loading.dogrula}>
          {loading.dogrula ? "⏳" : "✅ Doğrula"}
        </button>
        <div style={{ display: "flex", gap: "0.3rem", alignItems: "center" }}>
          <select value={exportFormat} onChange={e => setExportFormat(e.target.value)}
            style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.25rem", fontSize: "0.8rem" }}>
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
          </select>
          <button className="btn btn-outline" onClick={handleExport} disabled={loading.export_}>
            {loading.export_ ? "⏳" : "📤 Dışa Aktar"}
          </button>
        </div>
      </div>
      {hata && <div className="hata">{hata}</div>}
      {(citationSonuc || listeSonuc) && (
        <div className="sonuc">
          <table className="table">
            <thead>
              <tr>
                <th>Dizin</th>
                <th>URL</th>
                <th>NAP Durumu</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(citationSonuc || listeSonuc) ? citationSonuc || listeSonuc : [citationSonuc || listeSonuc]).map((r, i) => (
                <tr key={i}>
                  <td>{r.dizin || r.directory || r.platform || r.site || "-"}</td>
                  <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.url || r.link || "-"}</td>
                  <td>
                    <span style={{ color: (r.nap_durumu || r.nap_status || r.durum) === "uyumlu" || (r.nap_durumu || r.nap_status || r.durum) === "ok" ? "var(--green)" : "var(--orange)" }}>
                      {r.nap_durumu || r.nap_status || r.durum || "-"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {dogrulaSonuc && (
        <div className="sonuc">
          {Object.entries(dogrulaSonuc).map(([k, v]) => (
            <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
          ))}
        </div>
      )}
      {exportSonuc && (
        <div className="sonuc">
          {Object.entries(exportSonuc).map(([k, v]) => (
            <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}
