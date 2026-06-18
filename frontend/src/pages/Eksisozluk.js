import React, { useState } from "react";
import API from "../api";


export default function Eksisozluk() {
  const [baslik, setBaslik] = useState("");
  const [entry, setEntry] = useState("");
  const [entryId, setEntryId] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [gonderSonuc, setGonderSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [analizSonuc, setAnalizSonuc] = useState(null);

  const handleGonder = async () => {
    if (!baslik) { setHata("Başlık gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, gonder: true }));
    try { const res = await API.post("/api/eksisozluk", { baslik, entry }); setGonderSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, gonder: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try { const res = await API.get("/api/eksisozluk/listele"); setListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleSil = async () => {
    if (!entryId) { setHata("Entry ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, sil: true }));
    try { const res = await API.delete(`/api/eksisozluk/sil/${entryId}`); setGonderSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, sil: false }));
  };

  const handleAnaliz = async () => {
    setHata(""); setLoading(l => ({ ...l, analiz: true }));
    try { const res = await API.get("/api/eksisozluk/analiz"); setAnalizSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, analiz: false }));
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
        <div className="icon">📝</div>
        <div className="info">
          <h2>Ekşisözlük Fury – Entry Gönderme</h2>
          <p>Ekşi Sözlük'e entry gönder, geçmiş entry'leri listele ve analiz et.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
            <label>Başlık</label>
            <input value={baslik} onChange={e => setBaslik(e.target.value)} placeholder="örn: kuşadası escort" />
          </div>
        </div>
        <div className="form-grup" style={{ marginTop: "0.5rem" }}>
          <label>Entry</label>
          <textarea rows={4} value={entry} onChange={e => setEntry(e.target.value)}
            placeholder="Entry içeriği (boş bırakılırsa otomatik oluşturulur)"
            style={{ width: "100%" }} />
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-primary" onClick={handleGonder} disabled={loading.gonder}>
          {loading.gonder ? "Gönderiliyor..." : "📝 Entry Gönder"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Entry Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleAnaliz} disabled={loading.analiz}>
          {loading.analiz ? "⏳" : "📊 Entry Analiz"}
        </button>
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
            <label>Entry ID (silme için)</label>
            <input type="number" value={entryId} onChange={e => setEntryId(e.target.value)} placeholder="1" />
          </div>
          <button className="btn btn-danger" onClick={handleSil} disabled={loading.sil}>
            {loading.sil ? "⏳" : "🗑️ Entry Sil"}
          </button>
        </div>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}
      <SonucKarti data={gonderSonuc} />
      <SonucKarti data={listeSonuc} />
      <SonucKarti data={analizSonuc} />
    </div>
  );
}
