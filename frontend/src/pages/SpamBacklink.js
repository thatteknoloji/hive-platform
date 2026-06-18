import React, { useState } from "react";
import API from "../api";


export default function SpamBacklink() {
  const [domain, setDomain] = useState("");
  const [adet, setAdet] = useState(1000);
  const [aciklama, setAciklama] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [zehirSonuc, setZehirSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [hedefListeSonuc, setHedefListeSonuc] = useState(null);
  const [raporSonuc, setRaporSonuc] = useState(null);

  const handleZehirle = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, zehir: true }));
    try { const res = await API.post("/api/spambacklink", { domain, adet }); setZehirSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, zehir: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try { const res = await API.get("/api/spambacklink/listele"); setListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleHedefEkle = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, hedefEkle: true }));
    try { const res = await API.post("/api/spambacklink/hedef", { domain, aciklama }); setZehirSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, hedefEkle: false }));
  };

  const handleHedefListele = async () => {
    setHata(""); setLoading(l => ({ ...l, hedefListe: true }));
    try { const res = await API.get("/api/spambacklink/hedefler"); setHedefListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, hedefListe: false }));
  };

  const handleRapor = async () => {
    setHata(""); setLoading(l => ({ ...l, rapor: true }));
    try { const res = await API.get("/api/spambacklink/rapor"); setRaporSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, rapor: false }));
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
        <div className="icon">💀</div>
        <div className="info">
          <h2>Spam Backlink Zehirleyici</h2>
          <p>Hedef domainlere spam backlink gönder, zehirleme kayıtlarını listele ve raporla.</p>
        </div>
      </div>

      <div className="uyari danger" style={{ marginBottom: "1rem" }}>
        {`⚠️ Google cezasına yol açabilir! Sadece eğitim ve test amaçlı kullanın.`}
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
            <label>Hedef Domain</label>
            <input value={domain} onChange={e => setDomain(e.target.value)} placeholder="örn: rakipsitesi.com" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 100 }}>
            <label>Adet</label>
            <input type="number" value={adet} onChange={e => setAdet(parseInt(e.target.value) || 1000)} min={10} max={50000} />
          </div>
          <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
            <label>Açıklama (hedef ekleme için)</label>
            <input value={aciklama} onChange={e => setAciklama(e.target.value)} placeholder="Hedef açıklaması" />
          </div>
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-danger" onClick={handleZehirle} disabled={loading.zehir}>
          {loading.zehir ? "Zehirleniyor..." : "💀 Zehirle"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Zehirleme Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleHedefEkle} disabled={loading.hedefEkle}>
          {loading.hedefEkle ? "⏳" : "🎯 Hedef Ekle"}
        </button>
        <button className="btn btn-outline" onClick={handleHedefListele} disabled={loading.hedefListe}>
          {loading.hedefListe ? "⏳" : "📋 Hedef Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleRapor} disabled={loading.rapor}>
          {loading.rapor ? "⏳" : "📊 Rapor"}
        </button>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}
      <SonucKarti data={zehirSonuc} borderColor="var(--red)" />
      <SonucKarti data={listeSonuc} />
      <SonucKarti data={hedefListeSonuc} />
      <SonucKarti data={raporSonuc} borderColor="var(--honey)" />
    </div>
  );
}
