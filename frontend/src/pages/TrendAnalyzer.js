import React, { useState } from "react";
import API from "../api";


export default function TrendAnalyzer() {
  const [konu, setKonu] = useState("");
  const [hata, setHata] = useState("");
  const [loading, setLoading] = useState({});
  const [analizSonuc, setAnalizSonuc] = useState(null);
  const [populerSonuc, setPopulerSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);

  const handleAnaliz = async () => {
    if (!konu) { setHata("Konu gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, analiz: true }));
    try { const res = await API.post("/api/trend", { konu }); setAnalizSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, analiz: false }));
  };

  const handlePopuler = async () => {
    setHata(""); setLoading(l => ({ ...l, populer: true }));
    try { const res = await API.get("/api/trend/populer"); setPopulerSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, populer: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/trend/liste"); setListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, liste: false }));
  };

  const renderItem = (label, val) => (
    <div className="item"><span className="key">{label}: </span><span className="val">{val}</span></div>
  );

  return (
    <div>
      <div className="header">
        <div className="icon">📈</div>
        <div className="info"><h2>Trend Analyzer</h2><p>Güncel trendleri analiz et, popüler konuları keşfet.</p></div>
      </div>

      <div className="form-row">
        <div className="form-grup">
          <label>Konu</label>
          <input value={konu} onChange={e => setKonu(e.target.value)} placeholder="örn: yapay zeka 2026" />
        </div>
      </div>

      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleAnaliz} disabled={loading.analiz}>
          {loading.analiz ? "Analiz Ediliyor..." : "📈 Trend Analiz Et"}
        </button>
        <button className="btn btn-outline" onClick={handlePopuler} disabled={loading.populer}>
          {loading.populer ? "⏳" : "🔥 Popüler"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Listele"}
        </button>
      </div>

      {hata && <div className="hata">{hata}</div>}

      {analizSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Trend Analizi</h4>
          {renderItem("Konu", konu)}
          {renderItem("Momentum", analizSonuc.momentum != null ? analizSonuc.momentum : "—")}
          {renderItem("Hacim", analizSonuc.hacim != null ? analizSonuc.hacim : "—")}
          {renderItem("Yön", analizSonuc.yon || "—")}
          {typeof analizSonuc === "object" && Object.keys(analizSonuc).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(analizSonuc[k])}</span></div>
          ))}
        </div>
      )}

      {populerSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Popüler Trendler</h4>
          {Array.isArray(populerSonuc) ? populerSonuc.map((t, i) => (
            <div className="item" key={i}>
              <span className="key">#{i + 1} </span>
              <span className="val">{typeof t === "object" ? JSON.stringify(t) : t}</span>
            </div>
          )) : <div className="item"><span className="val">{JSON.stringify(populerSonuc)}</span></div>}
        </div>
      )}

      {listeSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Trend Listesi</h4>
          {Array.isArray(listeSonuc) ? listeSonuc.map((t, i) => (
            <div className="item" key={i}>
              <span className="key">{i + 1}. </span>
              <span className="val">{typeof t === "object" ? JSON.stringify(t) : t}</span>
            </div>
          )) : <div className="item"><span className="val">{JSON.stringify(listeSonuc)}</span></div>}
        </div>
      )}
    </div>
  );
}
