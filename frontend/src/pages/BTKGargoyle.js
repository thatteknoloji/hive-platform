import React, { useState } from "react";
import API from "../api";


export default function BTKGargoyle() {
  const [domain, setDomain] = useState("");
  const [gerekce, setGerekce] = useState("");
  const [referansNo, setReferansNo] = useState("");
  const [sikayetId, setSikayetId] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [sikayetSonuc, setSikayetSonuc] = useState(null);
  const [sorgulaSonuc, setSorgulaSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [istatistikSonuc, setIstatistikSonuc] = useState(null);

  const handleSikayet = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, sikayet: true }));
    try { const res = await API.post("/api/btk", { domain, gerekce }); setSikayetSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, sikayet: false }));
  };

  const handleSorgula = async () => {
    if (!referansNo) { setHata("Referans no gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, sorgula: true }));
    try { const res = await API.post("/api/btk/sorgula", { referans_no: referansNo }); setSorgulaSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, sorgula: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try { const res = await API.get("/api/btk/listele"); setListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleIptal = async () => {
    if (!sikayetId) { setHata("Şikayet ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, iptal: true }));
    try { const res = await API.post("/api/btk/iptal", { sikayet_id: parseInt(sikayetId) }); setSikayetSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, iptal: false }));
  };

  const handleIstatistik = async () => {
    setHata(""); setLoading(l => ({ ...l, istatistik: true }));
    try { const res = await API.get("/api/btk/istatistik"); setIstatistikSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, istatistik: false }));
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
        <div className="icon">⚖️</div>
        <div className="info">
          <h2>BTK Gargoyle – Domain Şikayet Sistemi</h2>
          <p>BTK'ya domain şikayeti gönder, sorgula, iptal et ve istatistikleri gör.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 2, minWidth: 250 }}>
            <label>Domain</label>
            <input value={domain} onChange={e => setDomain(e.target.value)} placeholder="örn: rakipsitesi.com" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
            <label>Referans No (sorgulama)</label>
            <input value={referansNo} onChange={e => setReferansNo(e.target.value)} placeholder="BTK-001" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 100 }}>
            <label>Şikayet ID (iptal)</label>
            <input type="number" value={sikayetId} onChange={e => setSikayetId(e.target.value)} placeholder="1" />
          </div>
        </div>
        <div className="form-grup" style={{ marginTop: "0.5rem" }}>
          <label>Gerekçe (opsiyonel)</label>
          <textarea rows={3} value={gerekce} onChange={e => setGerekce(e.target.value)}
            placeholder="Şikayet gerekçesi (boş bırakılırsa otomatik oluşturulur)" style={{ width: "100%" }} />
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-danger" onClick={handleSikayet} disabled={loading.sikayet}>
          {loading.sikayet ? "Gönderiliyor..." : "⚖️ Şikayet Gönder"}
        </button>
        <button className="btn btn-outline" onClick={handleSorgula} disabled={loading.sorgula}>
          {loading.sorgula ? "⏳" : "🔍 Sorgula"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Şikayet Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleIptal} disabled={loading.iptal}>
          {loading.iptal ? "⏳" : "❌ Şikayet İptal"}
        </button>
        <button className="btn btn-outline" onClick={handleIstatistik} disabled={loading.istatistik}>
          {loading.istatistik ? "⏳" : "📊 İstatistik"}
        </button>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}
      <SonucKarti data={sikayetSonuc} />
      <SonucKarti data={sorgulaSonuc} />
      <SonucKarti data={listeSonuc} />
      <SonucKarti data={istatistikSonuc} />
    </div>
  );
}
