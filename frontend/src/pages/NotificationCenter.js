import React, { useState } from "react";
import API from "../api";


export default function NotificationCenter() {
  const [kanal, setKanal] = useState("email");
  const [baslik, setBaslik] = useState("");
  const [mesaj, setMesaj] = useState("");
  const [hata, setHata] = useState("");
  const [loading, setLoading] = useState({});
  const [gonderSonuc, setGonderSonuc] = useState(null);
  const [bildirimlerSonuc, setBildirimlerSonuc] = useState(null);
  const [ayarlarSonuc, setAyarlarSonuc] = useState(null);

  const handleGonder = async () => {
    if (!baslik) { setHata("Başlık gerekli"); return; }
    if (!mesaj) { setHata("Mesaj gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, gonder: true }));
    try { const res = await API.post("/api/notification", { kanal, baslik, mesaj }); setGonderSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, gonder: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/notification/liste"); setBildirimlerSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, liste: false }));
  };

  const handleAyarlar = async () => {
    setHata(""); setLoading(l => ({ ...l, ayarlar: true }));
    try { const res = await API.get("/api/notification/ayarlar"); setAyarlarSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, ayarlar: false }));
  };

  const handleTemizle = async () => {
    setHata(""); setLoading(l => ({ ...l, temizle: true }));
    try { const res = await API.delete("/api/notification/temizle"); setGonderSonuc(res.data); setBildirimlerSonuc(null); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, temizle: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">📬</div>
        <div className="info"><h2>Notification Center</h2><p>Bildirim gönder, yönet ve kanal ayarlarını yapılandır.</p></div>
      </div>

      <div className="form-row">
        <div className="form-grup" style={{ flex: 0.5 }}>
          <label>Kanal</label>
          <select value={kanal} onChange={e => setKanal(e.target.value)}>
            <option value="email">Email</option>
            <option value="webhook">Webhook</option>
            <option value="sms">SMS</option>
            <option value="panel">Panel</option>
          </select>
        </div>
        <div className="form-grup">
          <label>Başlık</label>
          <input value={baslik} onChange={e => setBaslik(e.target.value)} placeholder="Bildirim başlığı" />
        </div>
      </div>

      <div className="form-grup">
        <label>Mesaj</label>
        <textarea rows={3} value={mesaj} onChange={e => setMesaj(e.target.value)} placeholder="Bildirim mesajı" />
      </div>

      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleGonder} disabled={loading.gonder}>
          {loading.gonder ? "Gönderiliyor..." : "📬 Gönder"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Bildirimler"}
        </button>
        <button className="btn btn-outline" onClick={handleAyarlar} disabled={loading.ayarlar}>
          {loading.ayarlar ? "⏳" : "⚙️ Ayarlar"}
        </button>
        <button className="btn btn-danger" onClick={handleTemizle} disabled={loading.temizle}>
          {loading.temizle ? "⏳" : "🗑️ Temizle"}
        </button>
      </div>

      {hata && <div className="hata">{hata}</div>}

      {gonderSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Gönderim Sonucu</h4>
          {typeof gonderSonuc === "object" && Object.keys(gonderSonuc).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(gonderSonuc[k])}</span></div>
          ))}
        </div>
      )}

      {bildirimlerSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Bildirimler</h4>
          {Array.isArray(bildirimlerSonuc) ? bildirimlerSonuc.map((b, i) => (
            <div className="item" key={i}>
              <span className="key">#{i + 1} </span>
              <span className="val">
                {b.kanal && <span style={{ color: "var(--blue)" }}>[{b.kanal}] </span>}
                {b.baslik || b.title || ""}
                {b.okundu != null && <span style={{ color: b.okundu ? "var(--green)" : "var(--orange)", marginLeft: "0.5rem" }}>({b.okundu ? "✓ Okundu" : "○ Bekliyor"})</span>}
                {b.tarih || b.date || b.created_at ? <span style={{ color: "var(--text2)", marginLeft: "0.5rem", fontSize: "0.75rem" }}>{b.tarih || b.date || b.created_at}</span> : null}
              </span>
            </div>
          )) : <div className="item"><span className="val">{JSON.stringify(bildirimlerSonuc)}</span></div>}
        </div>
      )}

      {ayarlarSonuc && (
        <div className="sonuc">
          <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Bildirim Ayarları</h4>
          {typeof ayarlarSonuc === "object" && Object.keys(ayarlarSonuc).map(k => (
            <div className="item" key={k}><span className="key">{k}: </span><span className="val">{JSON.stringify(ayarlarSonuc[k])}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}
