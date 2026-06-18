import React, { useState } from "react";
import API from "../api";


export default function AlertSystem() {
  const [hedef, setHedef] = useState("");
  const [kosul, setKosul] = useState(">");
  const [esik, setEsik] = useState("");
  const [hata, setHata] = useState("");
  const [loading, setLoading] = useState({});
  const [olusturSonuc, setOlusturSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [kontrolSonuc, setKontrolSonuc] = useState(null);
  const [gecmisSonuc, setGecmisSonuc] = useState(null);

  const handleOlustur = async () => {
    if (!hedef) { setHata("Hedef gerekli"); return; }
    if (!esik) { setHata("Eşik değeri gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, olustur: true }));
    try { const res = await API.post("/api/alert", { hedef, kosul, esik: parseFloat(esik) }); setOlusturSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, olustur: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/alert/liste"); setListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, liste: false }));
  };

  const handleKontrol = async () => {
    setHata(""); setLoading(l => ({ ...l, kontrol: true }));
    try { const res = await API.get("/api/alert/kontrol"); setKontrolSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, kontrol: false }));
  };

  const handleGecmis = async () => {
    setHata(""); setLoading(l => ({ ...l, gecmis: true }));
    try { const res = await API.get("/api/alert/gecmis"); setGecmisSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, gecmis: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">🔔</div>
        <div className="info"><h2>Alert System</h2><p>Koşul tabanlı alarmlar oluştur, tetiklenmeleri kontrol et.</p></div>
      </div>

      <div className="form-row">
        <div className="form-grup">
          <label>Hedef</label>
          <input value={hedef} onChange={e => setHedef(e.target.value)} placeholder="örn: rank.kelime1" />
        </div>
        <div className="form-grup" style={{ flex: 0.5 }}>
          <label>Koşul</label>
          <select value={kosul} onChange={e => setKosul(e.target.value)}>
            <option value=">">Büyüktür</option>
            <option value="<">Küçüktür</option>
            <option value={"="}>Eşittir</option>
            <option value="değişim">Değişim</option>
          </select>
        </div>
        <div className="form-grup" style={{ flex: 0.5 }}>
          <label>Eşik</label>
          <input type="number" value={esik} onChange={e => setEsik(e.target.value)} placeholder="10" />
        </div>
      </div>

      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleOlustur} disabled={loading.olustur}>
          {loading.olustur ? "Oluşturuluyor..." : "🔔 Alert Oluştur"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Alertlerim"}
        </button>
        <button className="btn btn-outline" onClick={handleKontrol} disabled={loading.kontrol}>
          {loading.kontrol ? "⏳" : "🔄 Kontrol Et"}
        </button>
        <button className="btn btn-outline" onClick={handleGecmis} disabled={loading.gecmis}>
          {loading.gecmis ? "⏳" : "📜 Geçmiş"}
        </button>
      </div>

      {hata && <div className="hata">{hata}</div>}

      {olusturSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Alert Oluşturuldu</h4>
          {typeof olusturSonuc === "object" && Object.keys(olusturSonuc).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(olusturSonuc[k])}</span></div>
          ))}
        </div>
      )}

      {listeSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Alertlerim</h4>
          {Array.isArray(listeSonuc) ? listeSonuc.map((a, i) => (
            <div className="item" key={i}>
              <span className="key">Alert #{i + 1}: </span>
              <span className="val">{typeof a === "object" ? JSON.stringify(a) : a}</span>
            </div>
          )) : <div className="item"><span className="val">{JSON.stringify(listeSonuc)}</span></div>}
        </div>
      )}

      {kontrolSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Kontrol Sonucu</h4>
          {typeof kontrolSonuc === "object" && Object.keys(kontrolSonuc).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(kontrolSonuc[k])}</span></div>
          ))}
        </div>
      )}

      {gecmisSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Alert Geçmişi</h4>
          {Array.isArray(gecmisSonuc) ? gecmisSonuc.map((g, i) => (
            <div className="item" key={i}><span className="key">{i + 1}. </span><span className="val">{typeof g === "object" ? JSON.stringify(g) : g}</span></div>
          )) : <div className="item"><span className="val">{JSON.stringify(gecmisSonuc)}</span></div>}
        </div>
      )}
    </div>
  );
}
