import React, { useState } from "react";
import API from "../api";


export default function ReportGenerator() {
  const [modulId, setModulId] = useState("");
  const [format, setFormat] = useState("csv");
  const [hata, setHata] = useState("");
  const [loading, setLoading] = useState({});
  const [olusturSonuc, setOlusturSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);

  const moduller = [
    { id: "ranktracker", ad: "Rank Tracker" },
    { id: "trend", ad: "Trend Analyzer" },
    { id: "sentiment", ad: "Sentiment AI" },
    { id: "forecast", ad: "Forecast Module" },
    { id: "alert", ad: "Alert System" },
    { id: "notification", ad: "Notification Center" },
    { id: "backlink", ad: "Backlink" },
    { id: "expired", ad: "Expired Domain" },
  ];

  const handleOlustur = async () => {
    if (!modulId) { setHata("Modül seçin"); return; }
    setHata(""); setLoading(l => ({ ...l, olustur: true }));
    try { const res = await API.post("/api/report", { modul_id: modulId, format }); setOlusturSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, olustur: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/report/liste"); setListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, liste: false }));
  };

  const handleIndir = async (reportId) => {
    setHata(""); setLoading(l => ({ ...l, indir: true }));
    try {
      const res = await API.post("/api/report/indir", { report_id: reportId || modulId }, { responseType: "blob" });
      const ext = format === "json" ? "json" : format === "txt" ? "txt" : "csv";
      const blob = new Blob([res.data], { type: res.headers["content-type"] || "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `report_${reportId || modulId}.${ext}`; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { setHata("İndirme hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, indir: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">📄</div>
        <div className="info"><h2>Report Generator</h2><p>Modül bazlı raporlar oluştur, listele ve indir.</p></div>
      </div>

      <div className="form-row">
        <div className="form-grup">
          <label>Modül</label>
          <select value={modulId} onChange={e => setModulId(e.target.value)}>
            <option value="">— Seçin —</option>
            {moduller.map(m => <option key={m.id} value={m.id}>{m.ad}</option>)}
          </select>
        </div>
        <div className="form-grup" style={{ flex: 0.5 }}>
          <label>Format</label>
          <select value={format} onChange={e => setFormat(e.target.value)}>
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
            <option value="txt">TXT</option>
          </select>
        </div>
      </div>

      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleOlustur} disabled={loading.olustur}>
          {loading.olustur ? "Oluşturuluyor..." : "📄 Rapor Oluştur"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Raporlarım"}
        </button>
        <button className="btn btn-outline" onClick={() => handleIndir(modulId)} disabled={loading.indir || !modulId}>
          {loading.indir ? "⏳" : "⬇️ İndir"}
        </button>
      </div>

      {hata && <div className="hata">{hata}</div>}

      {olusturSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Rapor Oluşturuldu</h4>
          {typeof olusturSonuc === "object" && Object.keys(olusturSonuc).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(olusturSonuc[k])}</span></div>
          ))}
        </div>
      )}

      {listeSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Raporlarım</h4>
          {Array.isArray(listeSonuc) ? (
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Modül</th>
                  <th>Format</th>
                  <th>Tarih</th>
                  <th>İndir</th>
                </tr>
              </thead>
              <tbody>
                {listeSonuc.map((r, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>{r.modul || r.modul_id || r.module || "—"}</td>
                    <td><span style={{ color: "var(--honey)" }}>{r.format || format}</span></td>
                    <td style={{ color: "var(--text2)", fontSize: "0.8rem" }}>{r.tarih || r.date || r.created_at || "—"}</td>
                    <td>
                      <button className="btn btn-sm btn-outline" onClick={() => handleIndir(r.id || r.report_id || modulId)} disabled={loading.indir}>
                        ⬇️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <div className="item"><span className="val">{JSON.stringify(listeSonuc)}</span></div>}
        </div>
      )}
    </div>
  );
}
