import React, { useState, useEffect, useRef } from "react";
import API from "../api";


const PLACEHOLDER = `balkutusu.com.tr
balkutusu.net
balkutusu.org
balkutusu.xyz
balkutusu.site`;

function statusLabel(result) {
  if (result.status === "completed") return "✅ Yönlendirildi";
  if (result.status === "failed") return `❌ Hata: ${result.error || "bilinmiyor"}`;
  if (result.status === "processing") {
    const steps = { dns: "DNS", dns_done: "DNS tamam", ssl: "SSL", nginx: "Nginx", test: "Test" };
    return `⏳ ${steps[result.step] || "İşleniyor"}…`;
  }
  return "⏳ Bekliyor…";
}

export default function Replicator() {
  const [domains, setDomains] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [statusMessage, setStatusMessage] = useState("");
  const [target, setTarget] = useState("balkutusu.com");
  const pollRef = useRef(null);

  const fetchStatus = async () => {
    try {
      const res = await API.get("/api/replicator/status");
      setResults(res.data.results || []);
      if (res.data.target) setTarget(res.data.target);
      if (res.data.completed) {
        setLoading(false);
        setStatusMessage("Tüm yönlendirmeler tamamlandı!");
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } else if (res.data.is_running) {
        setLoading(true);
      }
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    fetchStatus();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const startRedirect = async () => {
    const domainList = domains.split("\n").map((d) => d.trim()).filter(Boolean);
    if (domainList.length === 0) {
      setStatusMessage("Lütfen en az bir domain girin.");
      return;
    }

    setLoading(true);
    setResults([]);
    setStatusMessage("Yönlendirmeler başlatılıyor…");

    try {
      const res = await API.post("/api/replicator/redirect", { domains: domainList });
      setStatusMessage(res.data.message || "Başlatıldı");
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(fetchStatus, 2000);
      await fetchStatus();
    } catch (err) {
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message;
      setStatusMessage(`Hata: ${msg}`);
      setLoading(false);
    }
  };

  const completed = results.filter((r) => r.status === "completed").length;
  const failed = results.filter((r) => r.status === "failed").length;

  return (
    <div className="replicator-panel">
      <header className="replicator-header">
        <h2>The Replicator V3</h2>
        <p className="replicator-sub">301 Redirect Yönlendirici — tüm otorite ve backlink değeri ana siteye aktarılır.</p>
      </header>

      <div className="replicator-info">
        <div><strong>Hedef:</strong> https://{target}</div>
        <div><strong>Yöntem:</strong> DNS (Cloudflare) → SSL (Let&apos;s Encrypt) → Nginx 301</div>
      </div>

      <label className="replicator-label" htmlFor="replicator-domains">
        Yönlendirilecek domainler (her satıra bir tane)
      </label>
      <textarea
        id="replicator-domains"
        className="replicator-textarea"
        rows={10}
        placeholder={PLACEHOLDER}
        value={domains}
        onChange={(e) => setDomains(e.target.value)}
        disabled={loading}
      />

      <button type="button" className="btn btn-primary replicator-btn" onClick={startRedirect} disabled={loading}>
        {loading ? "Yönlendiriliyor…" : "301 Redirect Başlat"}
      </button>

      {statusMessage && <p className="replicator-status">{statusMessage}</p>}

      {results.length > 0 && (
        <div className="replicator-results">
          <h3>
            Durumlar ({completed} tamam{failed ? `, ${failed} hata` : ""})
          </h3>
          <table className="replicator-table">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Durum</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr key={result.domain}>
                  <td>{result.domain}</td>
                  <td>{statusLabel(result)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
