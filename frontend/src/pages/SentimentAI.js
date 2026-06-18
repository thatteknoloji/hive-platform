import React, { useState } from "react";
import API from "../api";


export default function SentimentAI() {
  const [metin, setMetin] = useState("");
  const [hata, setHata] = useState("");
  const [loading, setLoading] = useState({});
  const [analizSonuc, setAnalizSonuc] = useState(null);
  const [istatistikSonuc, setIstatistikSonuc] = useState(null);
  const [gecmisSonuc, setGecmisSonuc] = useState(null);

  const handleAnaliz = async () => {
    if (!metin) { setHata("Metin gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, analiz: true }));
    try { const res = await API.post("/api/sentiment", { metin }); setAnalizSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, analiz: false }));
  };

  const handleIstatistik = async () => {
    setHata(""); setLoading(l => ({ ...l, istatistik: true }));
    try { const res = await API.get("/api/sentiment/istatistik"); setIstatistikSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, istatistik: false }));
  };

  const handleGecmis = async () => {
    setHata(""); setLoading(l => ({ ...l, gecmis: true }));
    try { const res = await API.get("/api/sentiment/gecmis"); setGecmisSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, gecmis: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">💭</div>
        <div className="info"><h2>Sentiment AI</h2><p>Metinlerin duygu analizini yap, istatistikleri görüntüle.</p></div>
      </div>

      <div className="form-grup">
        <label>Metin</label>
        <textarea rows={4} value={metin} onChange={e => setMetin(e.target.value)} placeholder="Analiz edilecek metni girin..." />
      </div>

      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleAnaliz} disabled={loading.analiz}>
          {loading.analiz ? "Analiz Ediliyor..." : "💭 Analiz Et"}
        </button>
        <button className="btn btn-outline" onClick={handleIstatistik} disabled={loading.istatistik}>
          {loading.istatistik ? "⏳" : "📊 İstatistik"}
        </button>
        <button className="btn btn-outline" onClick={handleGecmis} disabled={loading.gecmis}>
          {loading.gecmis ? "⏳" : "📋 Geçmiş"}
        </button>
      </div>

      {hata && <div className="hata">{hata}</div>}

      {analizSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Analiz Sonucu</h4>
          <div className="item">
            <span className="key">Duygu: </span>
            <span className="val" style={{ color: analizSonuc.duygu === "positive" ? "var(--green)" : analizSonuc.duygu === "negative" ? "var(--red)" : "var(--orange)" }}>
              {analizSonuc.duygu || "—"}
            </span>
          </div>
          <div className="item"><span className="key">Güven: </span><span className="val">{analizSonuc.confidence != null ? analizSonuc.confidence + "%" : "—"}</span></div>
          <div className="item"><span className="key">Anahtar Kelimeler: </span><span className="val">{analizSonuc.keywords ? (Array.isArray(analizSonuc.keywords) ? analizSonuc.keywords.join(", ") : analizSonuc.keywords) : "—"}</span></div>
          {typeof analizSonuc === "object" && Object.keys(analizSonuc).filter(k => !["duygu","confidence","keywords"].includes(k)).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(analizSonuc[k])}</span></div>
          ))}
        </div>
      )}

      {istatistikSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>İstatistikler</h4>
          {typeof istatistikSonuc === "object" && Object.keys(istatistikSonuc).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(istatistikSonuc[k])}</span></div>
          ))}
        </div>
      )}

      {gecmisSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Geçmiş Analizler</h4>
          {Array.isArray(gecmisSonuc) ? gecmisSonuc.map((g, i) => (
            <div className="item" key={i}><span className="val">{typeof g === "object" ? JSON.stringify(g) : g}</span></div>
          )) : <div className="item"><span className="val">{JSON.stringify(gecmisSonuc)}</span></div>}
        </div>
      )}
    </div>
  );
}
