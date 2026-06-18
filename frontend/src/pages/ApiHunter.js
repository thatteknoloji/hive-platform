import React, { useState, useEffect } from "react";
import API from "../api";
import { MODULE_API_MAP } from "../apiConfig";

const RISK_RENK = {
  kritik: "#ff4444",
  yuksek: "#ff8800",
  orta: "#ffcc00",
  dusuk: "#66bb6a",
};

export default function ApiHunter() {
  const [kelime, setKelime] = useState("");
  const [domain, setDomain] = useState("");
  const [kaynaklar, setKaynaklar] = useState(["dork", "github", "crawl"]);
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [sonuc, setSonuc] = useState(null);
  const [liste, setListe] = useState([]);
  const [rapor, setRapor] = useState(null);
  const [exportFormat, setExportFormat] = useState("csv");
  const [exportData, setExportData] = useState(null);
  const [hedefler, setHedefler] = useState([]);
  const [yeniHedef, setYeniHedef] = useState("");
  const [serpApiQuery, setSerpApiQuery] = useState("");
  const [serpSonuc, setSerpSonuc] = useState(null);
  const [githubRepos, setGithubRepos] = useState(null);

  useEffect(() => {
    listele();
    hedefListele();
  }, []);

  const handleError = (err) => setHata(err?.response?.data?.detail || err?.message || "İstek başarısız");

  const tara = async () => {
    setHata(""); setSonuc(null); setRapor(null);
    setLoading(l => ({ ...l, tara: true }));
    try {
      const res = await API.post("/api/apihunter/tara", { kelime, domain, kaynaklar });
      setSonuc(res.data);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, tara: false }));
  };

  const listele = async () => {
    try {
      const res = await API.get("/api/apihunter/listele");
      setListe(res.data?.sonuc?.sonuclar || res.data?.sonuclar || []);
    } catch {}
  };

  const dogrula = async () => {
    setHata(""); setLoading(l => ({ ...l, dogrula: true }));
    try {
      const res = await API.post("/api/apihunter/dogrula", {});
      setSonuc(prev => ({ ...prev, dogrulama: res.data }));
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, dogrula: false }));
  };

  const raporAl = async () => {
    setHata(""); setRapor(null);
    setLoading(l => ({ ...l, rapor: true }));
    try {
      const res = await API.get("/api/apihunter/rapor");
      setRapor(res.data?.sonuc || res.data);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, rapor: false }));
  };

  const exportYap = async (format) => {
    setHata(""); setExportData(null);
    setExportFormat(format);
    setLoading(l => ({ ...l, export: true }));
    try {
      const res = await API.post("/api/apihunter/export", { format });
      const icerik = res.data?.sonuc?.icerik || res.data?.icerik || "";
      setExportData(icerik);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, export: false }));
  };

  const temizle = async () => {
    if (!window.confirm("Tüm API key kayıtlarını silmek istediğinize emin misiniz?")) return;
    try {
      await API.delete("/api/apihunter/temizle");
      setListe([]);
      setSonuc(null);
    } catch {}
  };

  const hedefEkle = async () => {
    if (!yeniHedef) return;
    setHata("");
    try {
      await API.post("/api/apihunter/hedef", { domain: yeniHedef, aciklama: "Frontend'den eklendi" });
      setYeniHedef("");
      hedefListele();
    } catch (err) { handleError(err); }
  };

  const hedefSil = async (domain) => {
    try {
      await API.delete(`/api/apihunter/hedef/${encodeURIComponent(domain)}`);
      hedefListele();
    } catch {}
  };

  const serpAra = async () => {
    if (!serpApiQuery) return;
    setHata(""); setSerpSonuc(null);
    setLoading(l => ({ ...l, serp: true }));
    try {
      const res = await API.post("/api/search", { query: serpApiQuery, num: 10 });
      setSerpSonuc(res.data);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, serp: false }));
  };

  const githubListele = async () => {
    setHata(""); setGithubRepos(null);
    setLoading(l => ({ ...l, github: true }));
    try {
      const res = await API.get("/api/github/repos");
      setGithubRepos(res.data);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, github: false }));
  };

  const hedefListele = async () => {
    try {
      const res = await API.get("/api/apihunter/hedefler");
      setHedefler(res.data?.sonuc?.hedefler || res.data?.hedefler || []);
    } catch {}
  };

  const toggleKaynak = (k) => {
    setKaynaklar(prev => prev.includes(k) ? prev.filter(x => x !== k) : [...prev, k]);
  };

  const indir = (icerik, uzanti) => {
    const blob = new Blob([icerik], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `apihunter_export.${uzanti}`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="header">
        <div className="icon">🔑</div>
        <div className="info">
          <h2>API Hunter Ultra</h2>
          <p>Sızdırılmış API anahtarlarını tara, doğrula ve raporla</p>
        </div>
      </div>

      <div className="uyari" style={{ fontSize: "0.85rem", marginBottom: "1rem" }}>
        Dork, GitHub kodu ve URL crawl yöntemleriyle açıkta kalmış API key'leri bulur.
        Gerçek tarama için SERPAPI_KEY ve GITHUB_TOKEN gerekir. Keysiz simülasyon modunda çalışır.
      </div>

      <div className="tarama-formu" style={{ background: "var(--bg2)", padding: "1rem", borderRadius: 8, marginBottom: "1rem" }}>
        <div className="form-row">
          <div className="form-grup" style={{ flex: 1 }}>
            <label>Anahtar Kelime</label>
            <input placeholder="örn: api key, OPENAI_API_KEY" value={kelime} onChange={e => setKelime(e.target.value)} />
          </div>
          <div className="form-grup" style={{ flex: 1 }}>
            <label>Hedef Domain</label>
            <input placeholder="örn: ornek-site.com" value={domain} onChange={e => setDomain(e.target.value)} />
          </div>
        </div>

        <div style={{ margin: "0.75rem 0" }}>
          <label style={{ display: "block", marginBottom: 4, fontSize: "0.85rem", color: "var(--text2)" }}>Tarama Kaynakları</label>
          <div style={{ display: "flex", gap: 8 }}>
            {["dork", "github", "crawl"].map(k => (
              <label key={k} className="checkbox-label" style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
                <input type="checkbox" checked={kaynaklar.includes(k)} onChange={() => toggleKaynak(k)} />
                {k === "dork" ? "🌐 Dork" : k === "github" ? "🐙 GitHub" : "🕷️ Crawl"}
              </label>
            ))}
          </div>
        </div>

        <div className="btn-group">
          <button className="btn btn-primary" onClick={tara} disabled={loading.tara}>
            {loading.tara ? "⏳ Taranıyor..." : "🔍 Tarama Başlat"}
          </button>
          <button className="btn btn-outline" onClick={dogrula} disabled={loading.dogrula}>
            {loading.dogrula ? "⏳ Doğrulanıyor..." : "✅ Sonuçları Doğrula"}
          </button>
          <button className="btn btn-outline" onClick={raporAl} disabled={loading.rapor}>
            {loading.rapor ? "⏳ Rapor hazırlanıyor..." : "📊 Rapor Al"}
          </button>
          <button className="btn btn-sm btn-danger" onClick={temizle}>🗑️ Temizle</button>
        </div>
      </div>

      {hata && <div className="hata">{hata}</div>}

      {sonuc && (
        <div className="sonuc" style={{ marginBottom: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📋 Tarama Sonucu</h3>
          {sonuc.tarama && (
            <div className="item"><span className="key">Kaynak: </span><span className="val">{sonuc.tarama.kaynak || "simulasyon"}</span></div>
          )}
          {sonuc.tarama && (
            <div className="item"><span className="key">Ham Buluntu: </span><span className="val">{sonuc.tarama.ham_buluntu || 0}</span></div>
          )}
          {sonuc.tarama?.bulunanlar && sonuc.tarama.bulunanlar.length > 0 && (
            <div style={{ marginTop: "0.5rem" }}>
              <div className="key" style={{ marginBottom: 4 }}>Bulunan Anahtarlar</div>
              <div className="table-container" style={{ overflowX: "auto" }}>
                <table className="table">
                  <thead><tr><th>Servis</th><th>Anahtar</th><th>Kaynak</th><th>Tip</th><th>Risk</th><th>Entropi</th></tr></thead>
                  <tbody>
                    {sonuc.tarama.bulunanlar.slice(0, 20).map((b, i) => (
                      <tr key={i}>
                        <td>{b.servis}</td>
                        <td style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>{b.key?.substring(0, 24)}...</td>
                        <td style={{ fontSize: "0.8rem", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{b.kaynak_url}</td>
                        <td>{b.buluntu_tipi}</td>
                        <td><span style={{ color: RISK_RENK[b.risk] || "var(--text2)", fontWeight: 600 }}>{b.risk}</span></td>
                        <td>{b.entropi}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {sonuc.tarama.bulunanlar.length > 20 && (
                <p style={{ fontSize: "0.8rem", color: "var(--text2)", marginTop: 4 }}>+{sonuc.tarama.bulunanlar.length - 20} daha fazla sonuç</p>
              )}
            </div>
          )}
          {sonuc.dogrulama && (
            <div style={{ marginTop: "0.5rem" }}>
              <div className="item"><span className="key">Doğrulanan: </span><span className="val">{sonuc.dogrulama.dogrulanan || 0}</span></div>
              <div className="item"><span className="key">Geçerli: </span><span className="val" style={{ color: "var(--green)" }}>{sonuc.dogrulama.gecerli || 0}</span></div>
              <div className="item"><span className="key">Geçersiz: </span><span className="val" style={{ color: "var(--red)" }}>{sonuc.dogrulama.gecersiz || 0}</span></div>
            </div>
          )}
        </div>
      )}

      {rapor && (
        <div className="sonuc" style={{ marginBottom: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📊 Rapor</h3>
          <div className="item"><span className="key">Toplam Key: </span><span className="val">{rapor.toplam_key || 0}</span></div>
          <div className="item"><span className="key">Rapora Giren: </span><span className="val">{rapor.rapora_giren || 0}</span></div>
          {rapor.servis_dagilimi && (
            <div style={{ marginTop: "0.5rem" }}>
              <div className="key" style={{ marginBottom: 4 }}>Servis Dağılımı</div>
              {Object.entries(rapor.servis_dagilimi).map(([s, a]) => (
                <div key={s} className="item"><span className="key">{s}: </span><span className="val">{a}</span></div>
              ))}
            </div>
          )}
          {rapor.risk_dagilimi && (
            <div style={{ marginTop: "0.5rem" }}>
              <div className="key" style={{ marginBottom: 4 }}>Risk Dağılımı</div>
              {Object.entries(rapor.risk_dagilimi).map(([r, a]) => (
                <div key={r} className="item"><span className="key" style={{ color: RISK_RENK[r] }}>{r}: </span><span className="val">{a}</span></div>
              ))}
            </div>
          )}
          {rapor.en_cok_etkilenen && (
            <div className="item" style={{ marginTop: 4 }}><span className="key">En Çok Etkilenen: </span><span className="val" style={{ color: "var(--red)", fontWeight: 600 }}>{rapor.en_cok_etkilenen}</span></div>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <div style={{ flex: 1, background: "var(--bg2)", padding: "1rem", borderRadius: 8 }}>
          <h3 style={{ fontSize: "0.95rem", marginBottom: "0.5rem" }}>📤 Export</h3>
          <div className="btn-group">
            {["csv", "json", "txt"].map(f => (
              <button key={f} className={`btn btn-sm ${exportFormat === f ? "btn-primary" : "btn-outline"}`} onClick={() => exportYap(f)} disabled={loading.export}>
                {f.toUpperCase()}
              </button>
            ))}
          </div>
          {exportData && (
            <div style={{ marginTop: "0.5rem" }}>
              <button className="btn btn-sm btn-primary" onClick={() => indir(exportData, exportFormat)}>⬇️ İndir</button>
              <details style={{ marginTop: 4 }}>
                <summary style={{ fontSize: "0.8rem", cursor: "pointer", color: "var(--text2)" }}>Önizle</summary>
                <pre style={{ fontSize: "0.7rem", maxHeight: 200, overflow: "auto", background: "var(--bg)", padding: 8, borderRadius: 4, marginTop: 4 }}>{exportData?.slice(0, 2000)}</pre>
              </details>
            </div>
          )}
        </div>

        <div style={{ flex: 1, background: "var(--bg2)", padding: "1rem", borderRadius: 8 }}>
          <h3 style={{ fontSize: "0.95rem", marginBottom: "0.5rem" }}>🎯 Hedef Ekle</h3>
          <div className="form-row">
            <input placeholder="Domain girin..." value={yeniHedef} onChange={e => setYeniHedef(e.target.value)}
              onKeyDown={e => e.key === "Enter" && hedefEkle()} style={{ flex: 1 }} />
            <button className="btn btn-sm btn-primary" onClick={hedefEkle}>➕ Ekle</button>
          </div>
          {hedefler.length > 0 && (
            <div style={{ marginTop: "0.5rem", maxHeight: 150, overflow: "auto" }}>
              {hedefler.map((h, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.25rem 0", borderBottom: "1px solid var(--border)", fontSize: "0.85rem" }}>
                  <span>{h.domain}</span>
                  <button className="btn btn-sm" style={{ color: "var(--red)", background: "none", border: "none", cursor: "pointer" }} onClick={() => hedefSil(h.domain)}>✕</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="sonuc">
        <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>🗂️ Kayıtlı API Key'ler ({liste.length})</h3>
        {liste.length === 0 ? (
          <p style={{ color: "var(--text2)", fontSize: "0.85rem" }}>Henüz kayıtlı API key bulunmuyor.</p>
        ) : (
          <div className="table-container" style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Servis</th><th>Key Hash</th><th>URL</th><th>Tip</th><th>Risk</th><th>Envi</th>
                </tr>
              </thead>
              <tbody>
                {liste.map((b, i) => (
                  <tr key={i}>
                    <td>{b.servis}</td>
                    <td style={{ fontSize: "0.75rem", fontFamily: "monospace" }}>{b.key_hash || b.key?.substring(0, 16)}</td>
                    <td style={{ fontSize: "0.75rem", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{b.kaynak_url}</td>
                    <td>{b.buluntu_tipi}</td>
                    <td><span style={{ color: RISK_RENK[b.risk] || "var(--text2)", fontWeight: 600 }}>{b.risk}</span></td>
                    <td>{b.env_adi || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <div style={{ flex: 1, background: "var(--bg2)", padding: "1rem", borderRadius: 8 }}>
          <h3 style={{ fontSize: "0.95rem", marginBottom: "0.5rem" }}>🔍 SERPAPI Test — Google'da Ara</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text2)", marginBottom: "0.5rem" }}>
            Kullanılan API: <strong style={{ color: "var(--honey)" }}>{MODULE_API_MAP.search}</strong>
          </p>
          <div className="form-row">
            <input
              placeholder="Arama sorgusu girin..."
              value={serpApiQuery}
              onChange={e => setSerpApiQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && serpAra()}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={serpAra} disabled={loading.serp}>
              {loading.serp ? "⏳" : "🔍 Google'da Ara"}
            </button>
          </div>
          {serpSonuc && (
            <div style={{ marginTop: "0.5rem", maxHeight: 300, overflow: "auto" }}>
              {serpSonuc.sonuclar?.map((s, i) => (
                <div key={i} style={{ padding: "0.5rem", borderBottom: "1px solid var(--border)", fontSize: "0.85rem" }}>
                  <div style={{ fontWeight: 600, color: "var(--blue)" }}>{s.baslik}</div>
                  <div style={{ color: "var(--green)", fontSize: "0.75rem" }}>{s.link}</div>
                  <div style={{ color: "var(--text2)", fontSize: "0.8rem", marginTop: 2 }}>{s.aciklama}</div>
                </div>
              ))}
              {serpSonuc.hata && <div className="hata">{serpSonuc.hata}</div>}
            </div>
          )}
        </div>

        <div style={{ flex: 1, background: "var(--bg2)", padding: "1rem", borderRadius: 8 }}>
          <h3 style={{ fontSize: "0.95rem", marginBottom: "0.5rem" }}>🐙 GitHub Test</h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text2)", marginBottom: "0.5rem" }}>
            Kullanılan API: <strong style={{ color: "var(--honey)" }}>{MODULE_API_MAP.github_integration}</strong>
          </p>
          <button className="btn btn-primary" onClick={githubListele} disabled={loading.github}>
            {loading.github ? "⏳ Yükleniyor..." : "📂 Repolarımı Listele"}
          </button>
          {githubRepos && (
            <div style={{ marginTop: "0.5rem", maxHeight: 350, overflow: "auto" }}>
              {githubRepos.repolar?.map((r, i) => (
                <div key={i} style={{ padding: "0.4rem", borderBottom: "1px solid var(--border)", fontSize: "0.85rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <a href={r.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--blue)", fontWeight: 600, textDecoration: "none" }}>{r.isim}</a>
                    <div style={{ color: "var(--text2)", fontSize: "0.75rem" }}>{r.aciklama || "Açıklama yok"}</div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text2)" }}>⭐ {r.yildiz} | 🍴 {r.fork_sayisi} | {r.dil}</div>
                  </div>
                  <span style={{ fontSize: "0.7rem", color: r.ozel ? "var(--red)" : "var(--green)" }}>{r.ozel ? "🔒 Özel" : "🌐 Açık"}</span>
                </div>
              ))}
              {githubRepos.hata && <div className="hata">{githubRepos.hata}</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
