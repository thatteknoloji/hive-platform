import React, { useState } from "react";
import API from "../api";


export default function FunnelAnalyzer() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [analizSonuc, setAnalizSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);

  const handleAnaliz = async () => {
    if (!url) { setHata("URL gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, analiz: true }));
    try { const res = await API.post("/api/funnel", { url }); setAnalizSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, analiz: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/funnel/liste"); setListeSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, liste: false }));
  };

  const renderAsamaBars = (asamalar) => {
    if (!asamalar || !Array.isArray(asamalar)) return null;
    const maxVal = Math.max(...asamalar.map(a => a.ziyaretci ?? a.visitors ?? a.adet ?? 1));
    return (
      <div style={{ marginTop: "1rem" }}>
        {asamalar.map((a, i) => {
          const val = a.ziyaretci ?? a.visitors ?? a.adet ?? 0;
          const pct = (val / maxVal) * 100;
          const onceki = i > 0 ? (asamalar[i - 1].ziyaretci ?? asamalar[i - 1].visitors ?? asamalar[i - 1].adet ?? 1) : null;
          const drop = onceki ? ((1 - val / onceki) * 100).toFixed(1) : "0";
          return (
            <div key={i} style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "0.25rem" }}>
                <span style={{ color: "var(--honey)", fontWeight: 500 }}>{a.asama || a.stage || a.ad || `Aşama ${i + 1}`}</span>
                <span style={{ color: "var(--text2)" }}>{val} ziyaretçi — düşüş: %{drop}</span>
              </div>
              <div style={{ background: "var(--bg)", borderRadius: 4, height: 24, overflow: "hidden" }}>
                <div style={{ width: `${pct}%`, height: "100%", background: "linear-gradient(90deg, var(--olive), var(--olive2))", borderRadius: 4, transition: "width 0.5s" }} />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div>
      <div className="header">
        <div className="icon">🔻</div>
        <div className="info"><h2>Funnel Analyzer</h2><p>Dönüşüm hunisi analizi ve aşama bazlı düşüş oranları</p></div>
      </div>
      <div className="form-grup">
        <label>Site URL</label>
        <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://ornek.com" />
      </div>
      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleAnaliz} disabled={loading.analiz}>
          {loading.analiz ? "⏳" : "🔻 Analiz Et"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Listele"}
        </button>
      </div>
      {hata && <div className="hata">{hata}</div>}
      {analizSonuc && (
        <div className="sonuc">
          {analizSonuc.asamalar ? renderAsamaBars(analizSonuc.asamalar) : (
            analizSonuc.asama ? renderAsamaBars(analizSonuc.asama) :
            Object.entries(analizSonuc).map(([k, v]) => (
              <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
            ))
          )}
          {analizSonuc.genel_donusum && (
            <div className="item" style={{ marginTop: "1rem" }}>
              <span className="key">Genel Dönüşüm Oranı: </span>
              <span className="val" style={{ color: "var(--green)", fontSize: "1.1rem" }}>{analizSonuc.genel_donusum}</span>
            </div>
          )}
        </div>
      )}
      {listeSonuc && (
        <div className="sonuc">
          {Array.isArray(listeSonuc) ? listeSonuc.map((h, i) => (
            <div key={i} className="item">
              <span className="key">{h.url || h.sayfa || `Huni #${i + 1}`}: </span>
              <span className="val">{(h.asama_sayisi ?? h.stage_count ?? h.durum) || JSON.stringify(h)}</span>
            </div>
          )) : Object.entries(listeSonuc).map(([k, v]) => (
            <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}
