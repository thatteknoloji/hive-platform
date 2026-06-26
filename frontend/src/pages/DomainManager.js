import React, { useState, useEffect } from "react";
import API from "../api";


export default function DomainManager() {
  const [connection, setConnection] = useState({
    url: "",
    username: "",
    password: "",
  });
  const [connected, setConnected] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState(null);
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [newSite, setNewSite] = useState({
    domain: "",
    title: "",
    email: "",
    path: "/",
  });

  const [bulkSites, setBulkSites] = useState("");
  const [showBulk, setShowBulk] = useState(false);

  useEffect(() => {
    checkConnection();
  }, []);

  const checkConnection = async () => {
    try {
      const res = await API.get("/api/wp/status");
      if (res.data.connected) {
        setConnected(true);
        setConnectionInfo(res.data);
        loadSites();
      }
    } catch (err) {
      // Not connected
    }
  };

  const loadSites = async () => {
    setLoading(true);
    try {
      const res = await API.get("/api/wp/sites");
      if (res.data.success) {
        setSites(res.data.sites || []);
      } else {
        setError(res.data.error || "Site listesi yüklenemedi");
      }
    } catch (err) {
      setError("Bağlantı hatası: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const res = await API.post("/api/wp/connect", connection);
      if (res.data.success) {
        setConnected(true);
        setConnectionInfo(res.data);
        setSuccess("Bağlantı başarılı!");
        loadSites();
      } else {
        setError(res.data.error || "Bağlantı hatası");
      }
    } catch (err) {
      setError("Bağlantı hatası: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await API.post("/api/wp/disconnect", {});
      setConnected(false);
      setConnectionInfo(null);
      setSites([]);
      setSuccess("Bağlantı kesildi");
    } catch (err) {
      setError("Bağlantı kesilemedi: " + err.message);
    }
  };

  const handleCreateSite = async () => {
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const res = await API.post("/api/wp/sites", newSite);
      if (res.data.success) {
        setSuccess(`Site oluşturuldu: ${res.data.domain}`);
        setNewSite({ domain: "", title: "", email: "", path: "/" });
        loadSites();
      } else {
        setError(res.data.error || "Site oluşturulamadı");
      }
    } catch (err) {
      setError("Hata: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSite = async (blogId, domain) => {
    if (!window.confirm(`${domain} silinecek. Emin misiniz?`)) return;

    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const res = await API.delete(`/api/wp/sites/${blogId}`);
      if (res.data.success) {
        setSuccess(`Site silindi: ${domain}`);
        loadSites();
      } else {
        setError(res.data.error || "Site silinemedi");
      }
    } catch (err) {
      setError("Hata: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkCreate = async () => {
    setError("");
    setSuccess("");
    setLoading(true);

    const lines = bulkSites.split("\n").filter((l) => l.trim());
    const sitesList = lines.map((line) => {
      const parts = line.split(",").map((p) => p.trim());
      return {
        domain: parts[0] || "",
        title: parts[1] || parts[0] || "",
        email: parts[2] || `admin@${parts[0]}`,
        path: "/",
      };
    });

    try {
      const res = await API.post("/api/wp/sites/bulk", { sites: sitesList });
      if (res.data.success) {
        setSuccess(
          `${res.data.success_count} site oluşturuldu, ${res.data.error_count} hata`
        );
        setBulkSites("");
        setShowBulk(false);
        loadSites();
      } else {
        setError(res.data.error || "Toplu oluşturma hatası");
      }
    } catch (err) {
      setError("Hata: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!connected) {
    return (
      <div className="domain-manager">
        <h2>🌐 Domain & Subdomain Yöneticisi</h2>
        <div className="connection-form">
          <h3>WordPress Multisite Bağlantısı</h3>
          <div className="form-group">
            <label>WordPress URL</label>
            <input
              type="text"
              value={connection.url}
              onChange={(e) =>
                setConnection({ ...connection, url: e.target.value })
              }
              placeholder="https://example.com"
            />
          </div>
          <div className="form-group">
            <label>Kullanıcı Adı</label>
            <input
              type="text"
              value={connection.username}
              onChange={(e) =>
                setConnection({ ...connection, username: e.target.value })
              }
              placeholder="admin"
            />
          </div>
          <div className="form-group">
            <label>Application Password</label>
            <input
              type="password"
              value={connection.password}
              onChange={(e) =>
                setConnection({ ...connection, password: e.target.value })
              }
              placeholder="xxxx xxxx xxxx xxxx"
            />
          </div>
          <button onClick={handleConnect} disabled={loading}>
            {loading ? "Bağlanıyor..." : "Bağlan"}
          </button>
          {error && <div className="error">{error}</div>}
          <div className="info-box">
            <p>
              <strong>Not:</strong> WordPress'e{" "}
              <strong>HIVE Multisite Bridge</strong> plugin'ini kurun ve aktif
              edin. Ardından Users → Profile → Application Passwords bölümünden
              yeni bir password oluşturun.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="domain-manager">
      <h2>🌐 Domain & Subdomain Yöneticisi</h2>

      <div className="connection-status">
        <div className="status-info">
          <span className="status-dot connected"></span>
          <strong>Bağlı:</strong> {connectionInfo?.url}
          {connectionInfo?.is_multisite && (
            <span className="badge">Multisite</span>
          )}
          <span className="site-count">{sites.length} site</span>
        </div>
        <button onClick={handleDisconnect} className="btn-disconnect">
          Bağlantıyı Kes
        </button>
      </div>

      <div className="sites-section">
        <div className="section-header">
          <h3>Mevcut Siteler ({sites.length})</h3>
          <div className="actions">
            <button onClick={loadSites} disabled={loading}>
              🔄 Yenile
            </button>
            <button onClick={() => setShowBulk(!showBulk)}>
              {showBulk ? "Tekli Ekle" : "Toplu Ekle"}
            </button>
          </div>
        </div>

        {loading && sites.length === 0 && <div className="loading">Yükleniyor...</div>}

        {sites.length > 0 && (
          <table className="sites-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Domain</th>
                <th>Başlık</th>
                <th>Yazı</th>
                <th>Durum</th>
                <th>İşlem</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((site) => (
                <tr key={site.id}>
                  <td>{site.id}</td>
                  <td>
                    <a
                      href={`https://${site.domain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {site.domain}
                    </a>
                  </td>
                  <td>{site.title}</td>
                  <td>{site.post_count}</td>
                  <td>
                    <span
                      className={`status-badge ${site.public ? "public" : "private"}`}
                    >
                      {site.public ? "Açık" : "Gizli"}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => handleDeleteSite(site.id, site.domain)}
                      className="btn-delete"
                    >
                      🗑️ Sil
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {sites.length === 0 && !loading && (
          <div className="empty-state">Henüz site yok. Yeni site ekleyin.</div>
        )}
      </div>

      {showBulk ? (
        <div className="bulk-create-section">
          <h3>Toplu Site Oluştur</h3>
          <p>Her satıra bir site: domain, başlık, email (opsiyonel)</p>
          <textarea
            value={bulkSites}
            onChange={(e) => setBulkSites(e.target.value)}
            placeholder={`sub.example.com, Site Adı, admin@example.com\nsub2.example.com, İkinci Site`}
            rows={8}
          />
          <button onClick={handleBulkCreate} disabled={loading || !bulkSites.trim()}>
            {loading ? "Oluşturuluyor..." : "Toplu Oluştur"}
          </button>
        </div>
      ) : (
        <div className="create-site-section">
          <h3>Yeni Site Oluştur</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Subdomain</label>
              <input
                type="text"
                value={newSite.domain}
                onChange={(e) =>
                  setNewSite({ ...newSite, domain: e.target.value })
                }
                placeholder="sub.example.com"
              />
            </div>
            <div className="form-group">
              <label>Başlık</label>
              <input
                type="text"
                value={newSite.title}
                onChange={(e) =>
                  setNewSite({ ...newSite, title: e.target.value })
                }
                placeholder="VIP Model Escort"
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={newSite.email}
                onChange={(e) =>
                  setNewSite({ ...newSite, email: e.target.value })
                }
                placeholder="admin@example.com"
              />
            </div>
            <div className="form-group">
              <label>Path</label>
              <input
                type="text"
                value={newSite.path}
                onChange={(e) =>
                  setNewSite({ ...newSite, path: e.target.value })
                }
                placeholder="/"
              />
            </div>
          </div>
          <button
            onClick={handleCreateSite}
            disabled={loading || !newSite.domain || !newSite.title}
          >
            {loading ? "Oluşturuluyor..." : "Site Oluştur"}
          </button>
        </div>
      )}

      {success && <div className="success">{success}</div>}
      {error && <div className="error">{error}</div>}
    </div>
  );
}
