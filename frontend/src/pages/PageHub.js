import React, { useState, useEffect, useCallback, useMemo } from "react";
import API from "../api";

const KINDS = [
  { id: "page", label: "WP Sayfalar", icon: "📄" },
  { id: "gece", label: "Gece Hayatı", icon: "🌙" },
  { id: "sss", label: "SSS Sayfası", icon: "❓" },
  { id: "landing", label: "SEO Landing", icon: "🎯" },
];

function TreeNode({ node, selectedId, onSelect, depth = 0 }) {
  const active = selectedId === node.id;
  const statusIcon = node.status === "publish" ? "✓" : "○";
  return (
    <div className="ch-tree-node" style={{ paddingLeft: depth * 12 }}>
      <button
        type="button"
        className={`ch-tree-btn ${active ? "active" : ""}`}
        onClick={() => onSelect(node)}
      >
        <span className="ch-tree-name">{depth > 0 ? "↳ " : `${statusIcon} `}{node.title}</span>
        <span className="ch-tree-meta">{node.status}</span>
      </button>
      {(node.children || []).map((c) => (
        <TreeNode key={c.id} node={c} selectedId={selectedId} onSelect={onSelect} depth={depth + 1} />
      ))}
    </div>
  );
}

export default function PageHub({ onNavigateSSS, onNavigateCategoryHub }) {
  const [kind, setKind] = useState("page");
  const [tree, setTree] = useState([]);
  const [pages, setPages] = useState([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState("create");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [wpConnected, setWpConnected] = useState(false);
  const [wpUrl, setWpUrl] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [treeLoading, setTreeLoading] = useState(false);
  const [wpTotal, setWpTotal] = useState(0);

  const [createTitle, setCreateTitle] = useState("");
  const [createSlug, setCreateSlug] = useState("");
  const [createContent, setCreateContent] = useState("");
  const [createParent, setCreateParent] = useState(0);
  const [createStatus, setCreateStatus] = useState("draft");
  const [bulkKeywords, setBulkKeywords] = useState("");
  const [dupCheck, setDupCheck] = useState(null);
  const [keyword, setKeyword] = useState("");
  const [city, setCity] = useState("Aydın");
  const [district, setDistrict] = useState("Kuşadası");
  const [notifyIndex, setNotifyIndex] = useState(true);

  const [pageDetail, setPageDetail] = useState(null);
  const [queue, setQueue] = useState([]);
  const [talonKw, setTalonKw] = useState([]);
  const [verify, setVerify] = useState(null);
  const [preview, setPreview] = useState(null);

  const [seoTitle, setSeoTitle] = useState("");
  const [seoSlug, setSeoSlug] = useState("");
  const [seoExcerpt, setSeoExcerpt] = useState("");
  const [seoContent, setSeoContent] = useState("");
  const [selectedQueue, setSelectedQueue] = useState([]);
  const [lastCreated, setLastCreated] = useState([]);

  const parentOptions = useMemo(
    () => pages.filter((p) => !p.parent && p.status === "publish"),
    [pages]
  );

  const isAiKind = kind === "sss" || kind === "landing";

  const connectWp = useCallback(async () => {
    setConnecting(true);
    setError("");
    try {
      const res = await API.post("/api/page-hub/connect");
      setWpConnected(!!res.data.wp_connected);
      setWpUrl(res.data.wp_url || "");
      if (res.data.wp_connected) {
        setMessage(res.data.message || `WordPress bağlandı: ${res.data.wp_url || ""}`);
      } else {
        setError(res.data.message || "WordPress bağlanamadı — backend/.env kontrol et");
      }
      return res.data.wp_connected;
    } catch (e) {
      const msg = e.response?.data?.detail || e.hiveMessage || e.message;
      setError(typeof msg === "string" ? msg : "WordPress bağlantı hatası");
      setWpConnected(false);
      return false;
    } finally {
      setConnecting(false);
    }
  }, []);

  const refreshTree = useCallback(async () => {
    setTreeLoading(true);
    try {
      const tr = await API.get(`/api/page-hub/tree?kind=${kind}&search=${encodeURIComponent(search)}`, { timeout: 120000 });
      setWpConnected(!!tr.data.wp_connected);
      if (tr.data.error && !tr.data.wp_connected) {
        setError(tr.data.error);
      } else if (tr.data.wp_connected) {
        setError("");
      }
      setTree(tr.data.tree || []);
      setPages(tr.data.pages || []);
      setWpTotal(tr.data.wp_total || tr.data.total || 0);
    } catch (e) {
      const status = e.response?.status;
      const msg = e.response?.data?.detail || e.hiveMessage || e.message;
      if (status === 404) {
        setError("API bulunamadı — backend yeniden başlat: npm run stop && npm start");
      } else {
        setError(typeof msg === "string" ? msg : "Sayfa ağacı yüklenemedi");
      }
    } finally {
      setTreeLoading(false);
    }
  }, [kind, search]);

  const refreshExtras = useCallback(async () => {
    try {
      const [q, tk] = await Promise.all([
        API.get(`/api/page-hub/queue?kind=${kind}&limit=40`),
        API.get("/api/page-hub/talon-keywords?limit=25"),
      ]);
      setQueue(q.data.items || []);
      setTalonKw(tk.data.keywords || []);
    } catch { /* sessiz */ }
  }, [kind]);

  const loadPageDetail = useCallback(async (page) => {
    if (!page?.id) return;
    setSeoTitle(page.title || "");
    setSeoSlug(page.slug || "");
    try {
      const [d, v] = await Promise.all([
        API.get(`/api/page-hub/detail?kind=${kind}&page_id=${page.id}`),
        API.get(`/api/page-hub/verify?kind=${kind}&page_id=${page.id}`),
      ]);
      const pg = d.data.page || {};
      setPageDetail(pg);
      setSeoTitle(pg.title || page.title || "");
      setSeoSlug(pg.slug || page.slug || "");
      setSeoExcerpt((pg.excerpt || "").replace(/<[^>]+>/g, ""));
      setSeoContent(pg.content || "");
      setVerify(v.data);
    } catch { /* sessiz */ }
  }, [kind]);

  useEffect(() => {
    (async () => {
      try {
        const st = await API.get("/api/page-hub/status");
        setWpConnected(!!st.data.wp_connected);
        setWpUrl(st.data.wp_url || "");
        if (!st.data.wp_connected) await connectWp();
      } catch (e) {
        if (e.response?.status === 404) {
          setError("Sayfa Merkezi API yok — terminalde: npm run stop && npm start");
        }
      }
    })();
  }, [connectWp]);

  useEffect(() => {
    refreshTree();
    refreshExtras();
  }, [refreshTree, refreshExtras]);

  useEffect(() => {
    if (selected) loadPageDetail(selected);
  }, [selected, loadPageDetail]);

  const runDupCheck = async (title, slug, parentId) => {
    if (!title.trim()) { setDupCheck(null); return; }
    try {
      const res = await API.get(
        `/api/page-hub/check-duplicate?kind=${kind}&title=${encodeURIComponent(title)}&slug=${encodeURIComponent(slug)}&parent_id=${parentId}`
      );
      setDupCheck(res.data);
    } catch { setDupCheck(null); }
  };

  useEffect(() => {
    const t = setTimeout(() => runDupCheck(createTitle || keyword, createSlug, createParent), 500);
    return () => clearTimeout(t);
  }, [createTitle, createSlug, createParent, keyword, kind]);

  const handleCreate = async (force = false) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/page-hub/create", {
        kind,
        title: createTitle,
        slug: createSlug,
        content: createContent,
        parent_id: createParent,
        status: createStatus,
        force,
        keyword: keyword || createTitle,
        city,
        district,
        notify_index: notifyIndex && createStatus === "publish",
      });
      const pg = res.data.page;
      const link = pg?.link;
      const idx = res.data.indexnow?.durum;
      const statusNote = pg?.status === "publish" ? "canlı" : "taslak (Gönder sekmesinden yayınla)";
      setMessage(
        link
          ? `Sayfa oluşturuldu (${statusNote}): ${link}${idx ? ` · IndexNow: ${idx}` : ""}`
          : `Sayfa oluşturuldu (${statusNote}): ${pg?.title} #${pg?.id}`
      );
      if (pg) setLastCreated([pg]);
      setCreateTitle("");
      setCreateSlug("");
      setCreateContent("");
      setKeyword("");
      setDupCheck(null);
      setPreview(null);
      await refreshTree();
      await refreshExtras();
      if (res.data.page) setSelected(res.data.page);
    } catch (e) {
      const d = e.response?.data?.detail;
      if (e.response?.status === 409 && !force) {
        setError(typeof d === "string" ? d : "Çift sayfa — yine de oluşturmak için onayla");
      } else {
        setError(typeof d === "string" ? d : e.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBulk = async (force = false) => {
    if (!bulkKeywords.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/page-hub/bulk-keywords", {
        kind,
        keywords: bulkKeywords,
        parent_id: createParent,
        status: createStatus,
        force,
        city,
        district,
        notify_index: notifyIndex && createStatus === "publish",
      });
      const items = res.data.pages || [];
      setMessage(`${res.data.created || 0} sayfa oluşturuldu (${res.data.total} kelime) — ${createStatus === "publish" ? "canlı" : "taslak"}`);
      setLastCreated(items);
      setBulkKeywords("");
      await refreshTree();
      await refreshExtras();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    const kw = (keyword || createTitle).trim();
    if (!kw) return;
    setLoading(true);
    try {
      const res = await API.post("/api/page-hub/preview", {
        kind: isAiKind ? kind : "landing",
        keyword: kw,
        city,
        district,
      });
      setPreview(res.data);
      if (!createTitle) setCreateTitle(res.data.title || "");
      if (!createSlug) setCreateSlug(res.data.slug || "");
      if (!createContent) setCreateContent(res.data.content || "");
      setMessage(res.data.ai_used ? "AI önizleme hazır" : "Şablon önizleme hazır");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async (pageId, status = "publish") => {
    if (!pageId) return;
    setLoading(true);
    try {
      const res = await API.post("/api/page-hub/publish", {
        kind, page_id: pageId, status, notify_index: notifyIndex,
      });
      const idx = res.data.indexnow?.durum;
      setMessage(`Yayınlandı: ${res.data.link || pageId}${idx ? ` · IndexNow: ${idx}` : ""}`);
      await refreshTree();
      await refreshExtras();
      if (selected?.id === pageId) await loadPageDetail({ ...selected, id: pageId });
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkPublish = async (ids) => {
    if (!ids.length) return;
    setLoading(true);
    try {
      const res = await API.post("/api/page-hub/bulk-publish", {
        kind, page_ids: ids, notify_index: notifyIndex,
      });
      setMessage(`${res.data.published} sayfa canlıya alındı`);
      setSelectedQueue([]);
      await refreshTree();
      await refreshExtras();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSeoSave = async () => {
    if (!selected?.id) return;
    setLoading(true);
    try {
      await API.put("/api/page-hub/page", {
        kind,
        page_id: selected.id,
        title: seoTitle,
        slug: seoSlug,
        content: seoContent,
        excerpt: seoExcerpt,
      });
      setMessage("Sayfa güncellendi");
      await refreshTree();
      await loadPageDetail(selected);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleIndexNow = async (url) => {
    if (!url) return;
    setLoading(true);
    try {
      const res = await API.post("/api/page-hub/indexnow", { url });
      setMessage(res.data.durum || "IndexNow gönderildi");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const addTalonKeyword = (kw) => {
    setBulkKeywords((prev) => (prev ? `${prev}\n${kw}` : kw));
    setKeyword(kw);
    setCreateTitle(kw);
    setTab("create");
  };

  const TABS = [
    { id: "create", label: "➕ Oluştur" },
    { id: "send", label: "Gönder", needsSelection: true },
    { id: "detail", label: "Detay", needsSelection: true },
    { id: "queue", label: `Kuyruk (${queue.length})` },
  ];

  const renderCreatePanel = (compact = false) => (
    <div className="ch-panel ch-create-panel">
      <h4>{compact ? "Yeni sayfa oluştur" : "Tek sayfa"}</h4>
      {!compact && (
        <p className="sf-dim">
          {isAiKind
            ? "AI ile SSS veya SEO landing — Groq zinciri otomatik devreye girer."
            : "Klasik WP sayfası veya gece_hayati CPT — taslak veya canlı."}
        </p>
      )}

      {isAiKind && (
        <div className="storyforge-meta-row">
          <div>
            <label className="storyforge-label">Anahtar kelime *</label>
            <input className="storyforge-input" placeholder="kuşadası gece hayatı" value={keyword} onChange={(e) => { setKeyword(e.target.value); setCreateTitle(e.target.value); }} />
          </div>
          <div>
            <label className="storyforge-label">İlçe</label>
            <input className="storyforge-input" value={district} onChange={(e) => setDistrict(e.target.value)} />
          </div>
        </div>
      )}

      <div className="storyforge-meta-row">
        <div>
          <label className="storyforge-label">{isAiKind ? "Başlık (AI doldurur)" : "Sayfa başlığı *"}</label>
          <input className="storyforge-input" placeholder="Örn: Kuşadası Rehberi" value={createTitle} onChange={(e) => setCreateTitle(e.target.value)} />
        </div>
        <div>
          <label className="storyforge-label">Üst sayfa</label>
          <select className="storyforge-input" value={createParent} onChange={(e) => setCreateParent(Number(e.target.value))}>
            <option value={0}>— Ana sayfa —</option>
            {parentOptions.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
        </div>
      </div>

      <div className="storyforge-meta-row">
        <div>
          <label className="storyforge-label">Slug (opsiyonel)</label>
          <input className="storyforge-input" placeholder="kusadasi-rehberi" value={createSlug} onChange={(e) => setCreateSlug(e.target.value)} />
        </div>
        <div>
          <label className="storyforge-label">Durum</label>
          <select className="storyforge-input" value={createStatus} onChange={(e) => setCreateStatus(e.target.value)}>
            <option value="draft">Taslak</option>
            <option value="publish">Canlı yayın</option>
            <option value="pending">İnceleme</option>
          </select>
        </div>
      </div>

      {!isAiKind && (
        <>
          <label className="storyforge-label">İçerik (HTML)</label>
          <textarea className="storyforge-textarea" rows={compact ? 4 : 6} placeholder="<p>Sayfa içeriği…</p>" value={createContent} onChange={(e) => setCreateContent(e.target.value)} />
        </>
      )}

      <label className="ch-check-label">
        <input type="checkbox" checked={notifyIndex} onChange={(e) => setNotifyIndex(e.target.checked)} />
        Yayın sonrası IndexNow bildir
      </label>

      {dupCheck && (dupCheck.warnings?.length > 0 || dupCheck.blocked) && (
        <div className={`ch-dup ${dupCheck.blocked ? "blocked" : "warn"}`}>
          {dupCheck.warnings?.map((w, i) => <p key={i}>{w}</p>)}
        </div>
      )}

      <div className="ch-create-actions">
        {isAiKind && (
          <button type="button" className="btn btn-outline" onClick={handlePreview} disabled={loading || !(keyword || createTitle).trim()}>
            👁 AI Önizle
          </button>
        )}
        <button type="button" className="btn btn-primary ch-btn-create" onClick={() => handleCreate(false)} disabled={loading || !(createTitle || keyword).trim()}>
          {loading ? "Oluşturuluyor…" : isAiKind ? "🤖 AI ile Oluştur" : "✅ Oluştur"}
        </button>
        {dupCheck?.has_warnings && (
          <button type="button" className="btn btn-outline" onClick={() => handleCreate(true)} disabled={loading}>
            Yine de oluştur
          </button>
        )}
      </div>

      {preview && (
        <div className="ch-preview-box">
          <strong>Önizleme:</strong> {preview.title}
          <div className="ch-preview-snippet" dangerouslySetInnerHTML={{ __html: (preview.content || "").slice(0, 400) + "…" }} />
        </div>
      )}

      <h4 className="ch-h4">Toplu kelime → sayfa</h4>
      <textarea className="storyforge-textarea" rows={compact ? 5 : 6} placeholder={"kuşadası marina rehberi\notel gecesi rehberi\nvip yat turu"} value={bulkKeywords} onChange={(e) => setBulkKeywords(e.target.value)} />
      <div className="ch-create-actions">
        <button type="button" className="btn btn-secondary ch-btn-create" onClick={() => handleBulk(false)} disabled={loading || !bulkKeywords.trim()}>
          {loading ? "…" : "📋 Toplu Oluştur"}
        </button>
      </div>

      {!compact && talonKw.length > 0 && (
        <div className="ch-talon">
          <strong>Talon kelimeleri → sayfa</strong>
          <div className="ch-talon-chips">
            {talonKw.map((kw) => (
              <button key={kw} type="button" className="ch-chip" onClick={() => addTalonKeyword(kw)}>+ {kw}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="category-hub page-hub">
      <header className="ch-header">
        <h2>📄 Sayfa Merkezi</h2>
        <p className="ch-sub">
          WP sayfa, gece hayatı, SSS ve SEO landing — oluştur, canlıya al, indeksle
          {wpConnected ? (
            <span className="sf-ok"> · WP: {wpUrl || "bağlı"}</span>
          ) : (
            <span className="ch-warn"> · WP bağlı değil</span>
          )}
        </p>
        {!wpConnected && (
          <div className="ch-connect-bar">
            <button type="button" className="btn btn-primary btn-small" onClick={connectWp} disabled={connecting}>
              {connecting ? "Bağlanıyor…" : "🔗 WordPress'e Bağlan (.env)"}
            </button>
            <span className="sf-dim">WP_URL, WP_USERNAME, WP_APP_PASSWORD — backend/.env</span>
          </div>
        )}
        <div className="ch-hub-links">
          {onNavigateCategoryHub && (
            <button type="button" className="btn btn-outline btn-small" onClick={onNavigateCategoryHub}>
              📂 Kategori Merkezi →
            </button>
          )}
          {onNavigateSSS && (
            <button type="button" className="btn btn-outline btn-small" onClick={onNavigateSSS}>
              ❓ SSS Otomatik Zincir →
            </button>
          )}
        </div>
      </header>

      <div className="ch-layout">
        <aside className="ch-sidebar">
          <div className="ch-kind-tabs">
            {KINDS.map((k) => (
              <button
                key={k.id}
                type="button"
                className={`ch-kind-tab ${kind === k.id ? "active" : ""}`}
                onClick={() => { setKind(k.id); setSelected(null); setPreview(null); }}
              >
                {k.icon} {k.label}
              </button>
            ))}
          </div>
          <input
            className="storyforge-input ch-search"
            placeholder="🔍 Sayfa ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {wpTotal > 0 && (
            <p className="sf-dim ch-total-hint">WP&apos;de {wpTotal} kayıt — arama ile daralt</p>
          )}
          <div className="ch-tree">
            {treeLoading && <p className="sf-dim">Sayfalar yükleniyor…</p>}
            {!treeLoading && tree.length === 0 && <p className="sf-dim">Sayfa yok — sağdan oluştur</p>}
            {tree.map((n) => (
              <TreeNode key={n.id} node={n} selectedId={selected?.id} onSelect={setSelected} />
            ))}
          </div>
        </aside>

        <main className="ch-main">
          {selected && (
            <div className="ch-selected-head">
              <h3>📍 {selected.title}</h3>
              <span className="sf-dim">/{selected.slug} · #{selected.id} · {selected.status}</span>
              {verify?.link && (
                <a href={verify.link} target="_blank" rel="noopener noreferrer" className="ch-live-link">
                  {verify.live ? "✓ Canlı" : "○ Kontrol et"} — sitede aç
                </a>
              )}
            </div>
          )}

          <div className="ch-tabs">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`ch-tab ${tab === t.id ? "active" : ""}`}
                onClick={() => setTab(t.id)}
                disabled={t.needsSelection && !selected}
                title={t.needsSelection && !selected ? "Önce sol taraftan sayfa seç" : ""}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "create" && renderCreatePanel(!selected)}

          {tab === "send" && selected && (
            <div className="ch-panel">
              <h4>Canlıya al</h4>
              <p className="sf-dim">Durum: <strong>{selected.status}</strong></p>
              {selected.status !== "publish" ? (
                <button type="button" className="btn btn-primary" onClick={() => handlePublish(selected.id)} disabled={loading}>
                  🚀 Yayınla (publish)
                </button>
              ) : (
                <p className="sf-ok">Bu sayfa zaten canlıda.</p>
              )}
              {verify?.link && (
                <button type="button" className="btn btn-outline btn-small" onClick={() => handleIndexNow(verify.link)} disabled={loading}>
                  📡 IndexNow bildir
                </button>
              )}

              <h4 className="ch-h4">Alt sayfa oluştur</h4>
              <p className="sf-dim">Yeni sayfa bu sayfanın altına eklenir (parent: #{selected.id})</p>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => { setCreateParent(selected.id); setTab("create"); }}
              >
                ➕ Alt sayfa oluştur
              </button>
            </div>
          )}

          {tab === "send" && !selected && (
            <p className="ch-hint-box">Yayınlamak için sol ağaçtan bir sayfa seç.</p>
          )}

          {tab === "detail" && selected && (
            <div className="ch-panel">
              <h4>SEO & düzenle</h4>
              <input className="storyforge-input" value={seoTitle} onChange={(e) => setSeoTitle(e.target.value)} />
              <input className="storyforge-input" placeholder="slug" value={seoSlug} onChange={(e) => setSeoSlug(e.target.value)} />
              <textarea className="storyforge-textarea" rows={2} placeholder="Meta açıklama / excerpt" value={seoExcerpt} onChange={(e) => setSeoExcerpt(e.target.value)} />
              <textarea className="storyforge-textarea" rows={8} placeholder="HTML içerik" value={seoContent} onChange={(e) => setSeoContent(e.target.value)} />
              <button type="button" className="btn btn-secondary" onClick={handleSeoSave} disabled={loading}>Kaydet</button>

              <h4 className="ch-h4">Canlı doğrulama</h4>
              {verify && (
                <p className={verify.live ? "sf-ok" : "sf-warn"}>
                  HTTP {verify.status_code || "?"} — {verify.link || "Link yok"}
                </p>
              )}
              <button type="button" className="btn btn-outline btn-small" onClick={() => selected && loadPageDetail(selected)}>
                Yeniden kontrol et
              </button>

              {pageDetail && (
                <>
                  <h4 className="ch-h4">İçerik önizleme</h4>
                  <div className="ch-preview-snippet" dangerouslySetInnerHTML={{ __html: (pageDetail.content || "").slice(0, 800) }} />
                </>
              )}
            </div>
          )}

          {tab === "detail" && !selected && (
            <p className="ch-hint-box">Detay ve SEO için sol taraftan sayfa seç.</p>
          )}

          {tab === "queue" && (
            <div className="ch-panel">
              <h4>Taslak kuyruk ({queue.length})</h4>
              <p className="sf-dim">Taslak veya içeriksiz sayfalar — toplu yayınla veya seçili sayfaya bağla.</p>
              <ul className="ch-queue-list">
                {queue.map((p) => (
                  <li key={p.id}>
                    <label>
                      <input
                        type="checkbox"
                        checked={selectedQueue.includes(p.id)}
                        onChange={(e) => setSelectedQueue((prev) => e.target.checked ? [...prev, p.id] : prev.filter((x) => x !== p.id))}
                      />
                      {p.title} <span className="sf-dim">#{p.id} · {p.status}</span>
                      <button type="button" className="ch-link-btn" onClick={() => handlePublish(p.id)} disabled={loading}>
                        yayınla
                      </button>
                    </label>
                  </li>
                ))}
              </ul>
              {queue.length > 0 && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => handleBulkPublish(selectedQueue.length ? selectedQueue : queue.map((p) => p.id))}
                  disabled={loading}
                >
                  {selectedQueue.length ? `${selectedQueue.length} sayfayı` : "Tümünü"} canlıya al
                </button>
              )}
            </div>
          )}
        </main>
      </div>

      {lastCreated.length > 0 && (
        <div className="ch-created-log">
          <h4>✅ Son oluşturulanlar ({lastCreated.length}) — gerçek WP kayıtları</h4>
          <ul className="ch-content-list">
            {lastCreated.map((item) => (
              <li key={item.id}>
                <strong>{item.title}</strong>
                <span className="sf-dim"> #{item.id} /{item.slug} · {item.status}</span>
                {item.link && item.status === "publish" ? (
                  <a href={item.link} target="_blank" rel="noopener noreferrer" className="ch-live-link"> — sitede aç</a>
                ) : item.status === "draft" ? (
                  <span className="sf-dim"> — taslak, Gönder sekmesinden canlıya al</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="storyforge-error">{error}</p>}
      {message && <p className="storyforge-ok">{message}</p>}
    </div>
  );
}
