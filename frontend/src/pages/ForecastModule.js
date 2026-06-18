import React, { useState } from "react";
import API from "../api";


export default function ForecastModule() {
  const [veriTipi, setVeriTipi] = useState("trend");
  const [hata, setHata] = useState("");
  const [loading, setLoading] = useState({});
  const [tahminSonuc, setTahminSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);

  const handleTahmin = async () => {
    setHata(""); setLoading(l => ({ ...l, tahmin: true }));
    try { const res = await API.post("/api/forecast", { veri_tipi: veriTipi }); setTahminSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, tahmin: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/forecast/liste"); setListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, liste: false }));
  };

  const handleExport = async (format) => {
    setHata(""); setLoading(l => ({ ...l, export_: true }));
    try {
      const res = await API.post("/api/forecast/export", { veri_tipi: veriTipi, format });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/" + (format === "csv" ? "csv" : "json") });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `forecast_${veriTipi}.${format}`; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { setHata("Export hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, export_: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">🔮</div>
        <div className="info"><h2>Forecast Module</h2><p>Veri tahminlemesi yap, projeksiyonları görüntüle ve dışa aktar.</p></div>
      </div>

      <div className="form-grup">
        <label>Veri Tipi</label>
        <select value={veriTipi} onChange={e => setVeriTipi(e.target.value)}>
          <option value="trend">Trend</option>
          <option value="rank">Rank</option>
          <option value="traffic">Traffic</option>
          <option value="conversion">Conversion</option>
        </select>
      </div>

      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleTahmin} disabled={loading.tahmin}>
          {loading.tahmin ? "Tahmin Ediliyor..." : "🔮 Tahmin Et"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Listele"}
        </button>
      </div>

      <div className="btn-group" style={{ marginTop: "0.5rem" }}>
        <button className="btn btn-sm btn-outline" onClick={() => handleExport("csv")} disabled={loading.export_}>
          📥 CSV
        </button>
        <button className="btn btn-sm btn-outline" onClick={() => handleExport("json")} disabled={loading.export_}>
          📥 JSON
        </button>
      </div>

      {hata && <div className="hata">{hata}</div>}

      {tahminSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Tahmin Sonucu ({veriTipi})</h4>
          <div className="item"><span className="key">Veri Tipi: </span><span className="val">{veriTipi}</span></div>
          {tahminSonuc.projeksiyon != null && <div className="item"><span className="key">Projeksiyon: </span><span className="val">{tahminSonuc.projeksiyon}</span></div>}
          {tahminSonuc.guven_araligi != null && <div className="item"><span className="key">Güven Aralığı: </span><span className="val">{tahminSonuc.guven_araligi}</span></div>}
          {tahminSonuc.confidence_interval && <div className="item"><span className="key">Confidence Interval: </span><span className="val">{JSON.stringify(tahminSonuc.confidence_interval)}</span></div>}
          {tahminSonuc.projected_values && <div className="item"><span className="key">Projected Values: </span><span className="val">{JSON.stringify(tahminSonuc.projected_values)}</span></div>}
          {typeof tahminSonuc === "object" && Object.keys(tahminSonuc).filter(k => !["projeksiyon","guven_araligi","confidence_interval","projected_values"].includes(k)).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(tahminSonuc[k])}</span></div>
          ))}
        </div>
      )}

      {listeSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Tahmin Geçmişi</h4>
          {Array.isArray(listeSonuc) ? listeSonuc.map((f, i) => (
            <div className="item" key={i}><span className="key">{i + 1}. </span><span className="val">{typeof f === "object" ? JSON.stringify(f) : f}</span></div>
          )) : <div className="item"><span className="val">{JSON.stringify(listeSonuc)}</span></div>}
        </div>
      )}
    </div>
  );
}
