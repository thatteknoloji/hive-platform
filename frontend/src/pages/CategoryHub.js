import React, { useState, useEffect, useCallback, useMemo } from "react";
import API from "../api";


const KINDS = [
  { id: "ilan", label: "İlan Kategorileri", icon: "👤" },
  { id: "hikaye", label: "Hikaye Kategorileri", icon: "📖" },
];

function TreeNode({ node, selectedId, onSelect, depth = 0 }) {
  const active = selectedId === node.id;
  return (
    <div className="ch-tree-node" style={{ paddingLeft: depth * 12 }}>
      <button
        type="button"
        className={`ch-tree-btn ${active ? "active" : ""}`}
        onClick={() => onSelect(node)}
      >
        <span className="ch-tree-name">{depth > 0 ? "↳ " : "📁 "}{node.name}</span>
        <span className="ch-tree-meta">({node.count || 0})</span>
      </button>
      {(node.children || []).map((c) => (
        <TreeNode key={c.id} node={c} selectedId={selectedId} onSelect={onSelect} depth={depth + 1} />
      ))}
    </div>
  );
}

export default function CategoryHub({ onNavigateStoryForge, onNavigatePageHub }) {
  const [kind, setKind] = useState("ilan");
  const [tree, setTree] = useState([]);
  const [terms, setTerms] = useState([]);
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

  const [createName, setCreateName] = useState("");
  const [createSlug, setCreateSlug] = useState("");
  const [createParent, setCreateParent] = useState(0);
  const [bulkKeywords, setBulkKeywords] = useState("");
  const [parentName, setParentName] = useState("Kuşadası Escort");
  const [parentSlug, setParentSlug] = useState("kusadasi-escort");
  const [dupCheck, setDupCheck] = useState(null);

  const [termContent, setTermContent] = useState([]);
  const [queue, setQueue] = useState([]);
  const [talonKw, setTalonKw] = useState([]);
  const [verify, setVerify] = useState(null);

  const [newProfileTitle, setNewProfileTitle] = useState("");
  const [newProfileContent, setNewProfileContent] = useState("");
  const [storyText, setStoryText] = useState("");
  const [storyTitle, setStoryTitle] = useState("");
  const [selectedPosts, setSelectedPosts] = useState([]);
  const [mergeSource, setMergeSource] = useState("");
  const [seoDesc, setSeoDesc] = useState("");
  const [seoName, setSeoName] = useState("");
  const [lastCreated, setLastCreated] = useState([]);

  const parentOptions = useMemo(
    () => terms.filter((t) => !t.parent),
    [terms]
  );

  const connectWp = useCallback(async () => {
    setConnecting(true);
    setError("");
    try {
      const res = await API.post("/api/category-hub/connect");
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
      const tr = await API.get(`/api/category-hub/tree?kind=${kind}&search=${encodeURIComponent(search)}`, { timeout: 120000 });
      setWpConnected(!!tr.data.wp_connected);
      if (tr.data.error && !tr.data.wp_connected) {
        setError(tr.data.error);
      } else if (tr.data.wp_connected) {
        setError("");
      }
      setTree(tr.data.tree || []);
      setTerms(tr.data.terms || []);
      setWpTotal(tr.data.wp_total || tr.data.total || 0);
    } catch (e) {
      const status = e.response?.status;
      const msg = e.response?.data?.detail || e.hiveMessage || e.message;
      if (status === 404) {
        setError("API bulunamadı — backend yeniden başlat: npm run stop && npm start");
      } else {
        setError(typeof msg === "string" ? msg : "Kategori ağacı yüklenemedi");
      }
    } finally {
      setTreeLoading(false);
    }
  }, [kind, search]);

  const refreshExtras = useCallback(async () => {
    try {
      const [q, tk] = await Promise.all([
        API.get(`/api/category-hub/queue?kind=${kind}&limit=40`),
        API.get("/api/category-hub/talon-keywords?limit=25"),
      ]);
      setQueue(q.data.items || []);
      setTalonKw(tk.data.keywords || []);
    } catch { /* sessiz */ }
  }, [kind]);

  const loadTermDetail = useCallback(async (term) => {
    if (!term?.id) return;
    setSeoName(term.name || "");
    setSeoDesc(term.description || "");
    try {
      const [c, v] = await Promise.all([
        API.get(`/api/category-hub/content?kind=${kind}&term_id=${term.id}`),
        API.get(`/api/category-hub/verify?kind=${kind}&term_id=${term.id}`),
      ]);
      setTermContent(c.data.items || []);
      setVerify(v.data);
    } catch { /* sessiz */ }
  }, [kind]);

  useEffect(() => {
    (async () => {
      try {
        const st = await API.get("/api/category-hub/status");
        setWpConnected(!!st.data.wp_connected);
        setWpUrl(st.data.wp_url || "");
        if (!st.data.wp_connected) await connectWp();
      } catch (e) {
        if (e.response?.status === 404) {
          setError("Kategori Merkezi API yok — terminalde: npm run stop && npm start");
        }
      }
    })();
  }, [connectWp]);

  useEffect(() => {
    refreshTree();
    refreshExtras();
  }, [refreshTree, refreshExtras]);

  useEffect(() => {
    if (selected) loadTermDetail(selected);
  }, [selected, loadTermDetail]);

  const runDupCheck = async (name, slug, parentId) => {
    if (!name.trim()) { setDupCheck(null); return; }
    try {
      const res = await API.get(
        `/api/category-hub/check-duplicate?kind=${kind}&name=${encodeURIComponent(name)}&slug=${encodeURIComponent(slug)}&parent_id=${parentId}`
      );
      setDupCheck(res.data);
    } catch { setDupCheck(null); }
  };

  useEffect(() => {
    const t = setTimeout(() => runDupCheck(createName, createSlug, createParent), 500);
    return () => clearTimeout(t);
  }, [createName, createSlug, createParent, kind]);

  const handleCreate = async (force = false) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/category-hub/create", {
        kind, name: createName, slug: createSlug, parent_id: createParent, force,
      });
      const term = res.data.term;
      setMessage(`Kategori oluşturuldu: ${term?.name} (#${term?.id})`);
      if (term) setLastCreated([{ ...term, link: term.link || "" }]);
      setCreateName("");
      setCreateSlug("");
      setDupCheck(null);
      await refreshTree();
      if (term) setSelected(term);
    } catch (e) {
      const d = e.response?.data?.detail;
      if (e.response?.status === 409 && !force) {
        setError(typeof d === "string" ? d : "Çift kategori — yine de oluşturmak için onayla");
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
      const res = await API.post("/api/category-hub/bulk-keywords", {
        kind, keywords: bulkKeywords, parent_name: parentName, parent_slug: parentSlug, force,
      });
      const items = res.data.items || [];
      setMessage(`${res.data.created || 0} yeni kategori oluşturuldu — sol ağaçta görünür`);
      setLastCreated(items);
      setBulkKeywords("");
      await refreshTree();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAssignQueue = async (postIds) => {
    if (!selected?.id || !postIds.length) return;
    setLoading(true);
    try {
      const res = await API.post("/api/category-hub/assign", {
        kind, post_ids: postIds, term_ids: [selected.id], mode: "add",
      });
      setMessage(`${res.data.updated} içerik kategoriye atandı`);
      setSelectedPosts([]);
      await refreshExtras();
      await loadTermDetail(selected);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePublishProfile = async () => {
    if (!newProfileTitle.trim() || !selected?.id) return;
    setLoading(true);
    try {
      const res = await API.post("/api/category-hub/publish-profile", {
        title: newProfileTitle,
        content: newProfileContent,
        term_ids: [selected.id],
        status: "publish",
      });
      setMessage(`İlan yayınlandı: ${res.data.link || res.data.post_id}`);
      setNewProfileTitle("");
      setNewProfileContent("");
      await loadTermDetail(selected);
      await refreshTree();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePublishStory = async () => {
    if (!storyText.trim() || storyText.trim().length < 80) {
      setError("Hikaye en az 80 karakter");
      return;
    }
    setLoading(true);
    try {
      const res = await API.post("/api/category-hub/publish-story", {
        text: storyText,
        title: storyTitle,
        term_slug: selected?.slug || "auto",
        auto_publish: true,
      });
      const link = res.data.link || res.data.display_url;
      setMessage(link ? `Hikaye yayınlandı: ${link}` : "Hikaye işlendi");
      setStoryText("");
      setStoryTitle("");
      await loadTermDetail(selected);
      await refreshTree();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMerge = async () => {
    const src = parseInt(mergeSource, 10);
    if (!src || !selected?.id || src === selected.id) return;
    if (!window.confirm(`#${src} kategorisini "${selected.name}" altına birleştir?`)) return;
    setLoading(true);
    try {
      const res = await API.post("/api/category-hub/merge", {
        kind, source_id: src, target_id: selected.id,
      });
      setMessage(`${res.data.moved_posts} içerik taşındı, kaynak silindi`);
      setMergeSource("");
      await refreshTree();
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
      await API.put("/api/category-hub/term", {
        kind, term_id: selected.id, name: seoName, description: seoDesc,
      });
      setMessage("Kategori SEO güncellendi");
      await refreshTree();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const addTalonKeyword = (kw) => {
    setBulkKeywords((prev) => (prev ? `${prev}\n${kw}` : kw));
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
      <h4>{compact ? "Yeni kategori oluştur" : "Tek kategori"}</h4>
      {!compact && <p className="sf-dim">Ana veya alt kategori — WP&apos;de anında açılır.</p>}
      <div className="storyforge-meta-row">
        <div>
          <label className="storyforge-label">Kategori adı *</label>
          <input className="storyforge-input" placeholder="Örn: Marina Escort" value={createName} onChange={(e) => setCreateName(e.target.value)} />
        </div>
        <div>
          <label className="storyforge-label">Üst kategori</label>
          <select className="storyforge-input" value={createParent} onChange={(e) => setCreateParent(Number(e.target.value))}>
            <option value={0}>— Ana kategori —</option>
            {parentOptions.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
      </div>
      <label className="storyforge-label">Slug (opsiyonel)</label>
      <input className="storyforge-input" placeholder="marina-escort" value={createSlug} onChange={(e) => setCreateSlug(e.target.value)} />
      {dupCheck && (dupCheck.warnings?.length > 0 || dupCheck.blocked) && (
        <div className={`ch-dup ${dupCheck.blocked ? "blocked" : "warn"}`}>
          {dupCheck.warnings?.map((w, i) => <p key={i}>{w}</p>)}
        </div>
      )}
      <div className="ch-create-actions">
        <button type="button" className="btn btn-primary ch-btn-create" onClick={() => handleCreate(false)} disabled={loading || !createName.trim()}>
          {loading ? "Oluşturuluyor…" : "✅ Oluştur"}
        </button>
        {dupCheck?.has_warnings && (
          <button type="button" className="btn btn-outline" onClick={() => handleCreate(true)} disabled={loading}>
            Yine de oluştur
          </button>
        )}
      </div>

      <h4 className="ch-h4">Toplu kelime → alt kategori</h4>
      <div className="storyforge-meta-row">
        <input className="storyforge-input" placeholder="Ana kategori adı" value={parentName} onChange={(e) => setParentName(e.target.value)} />
        <input className="storyforge-input" placeholder="Ana slug" value={parentSlug} onChange={(e) => setParentSlug(e.target.value)} />
      </div>
      <textarea className="storyforge-textarea" rows={compact ? 5 : 6} placeholder={"kuşadası marina\notel gecesi\nvip yat"} value={bulkKeywords} onChange={(e) => setBulkKeywords(e.target.value)} />
      <div className="ch-create-actions">
        <button type="button" className="btn btn-secondary ch-btn-create" onClick={() => handleBulk(false)} disabled={loading || !bulkKeywords.trim()}>
          {loading ? "…" : "📋 Toplu Oluştur"}
        </button>
      </div>

      {!compact && talonKw.length > 0 && (
        <div className="ch-talon">
          <strong>Talon kelimeleri → kategori</strong>
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
    <div className="category-hub">
      <header className="ch-header">
        <h2>📂 Kategori Merkezi</h2>
        <p className="ch-sub">
          İlan ve hikaye kategorileri — oluştur, canlıya al, içerik gönder
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
        {onNavigatePageHub && (
          <div className="ch-hub-links">
            <button type="button" className="btn btn-outline btn-small" onClick={onNavigatePageHub}>
              📄 Sayfa Merkezi →
            </button>
          </div>
        )}
      </header>

      <div className="ch-layout">
        <aside className="ch-sidebar">
          <div className="ch-kind-tabs">
            {KINDS.map((k) => (
              <button
                key={k.id}
                type="button"
                className={`ch-kind-tab ${kind === k.id ? "active" : ""}`}
                onClick={() => { setKind(k.id); setSelected(null); }}
              >
                {k.icon} {k.label}
              </button>
            ))}
          </div>
          <input
            className="storyforge-input ch-search"
            placeholder="🔍 Kategori ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {wpTotal > 0 && (
            <p className="sf-dim ch-total-hint">WP&apos;de {wpTotal} kategori — arama ile daralt</p>
          )}
          <div className="ch-tree">
            {treeLoading && <p className="sf-dim">Kategoriler yükleniyor…</p>}
            {!treeLoading && tree.length === 0 && <p className="sf-dim">Kategori yok — sağdan oluştur</p>}
            {tree.map((n) => (
              <TreeNode key={n.id} node={n} selectedId={selected?.id} onSelect={setSelected} />
            ))}
          </div>
          {kind === "hikaye" && (
            <button type="button" className="btn btn-outline btn-small ch-sync" onClick={async () => {
              setLoading(true);
              try {
                const res = await API.post(`/api/category-hub/sync-default?kind=hikaye`);
                setMessage(`Senkron: ${res.data.created} yeni terim`);
                await refreshTree();
              } catch (e) { setError(e.response?.data?.detail || e.message); }
              finally { setLoading(false); }
            }}>
              Varsayılan ağacı senkron et
            </button>
          )}
        </aside>

        <main className="ch-main">
          {selected && (
            <div className="ch-selected-head">
              <h3>📍 {selected.name}</h3>
              <span className="sf-dim">/{selected.slug} · #{selected.id} · {selected.count || 0} içerik</span>
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
                title={t.needsSelection && !selected ? "Önce sol taraftan kategori seç" : ""}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "create" && renderCreatePanel(!selected)}

          {tab === "send" && selected && (
                <div className="ch-panel">
                  {kind === "ilan" ? (
                    <>
                      <h4>Yeni ilan gönder</h4>
                      <input className="storyforge-input" placeholder="İlan başlığı" value={newProfileTitle} onChange={(e) => setNewProfileTitle(e.target.value)} />
                      <textarea className="storyforge-textarea" rows={4} placeholder="Açıklama" value={newProfileContent} onChange={(e) => setNewProfileContent(e.target.value)} />
                      <button type="button" className="btn btn-primary" onClick={handlePublishProfile} disabled={loading}>
                        Bu kategoriye ilan yayınla
                      </button>
                      <h4 className="ch-h4">Mevcut ilanları ata</h4>
                      <ul className="ch-queue-list">
                        {queue.slice(0, 15).map((p) => (
                          <li key={p.id}>
                            <label>
                              <input
                                type="checkbox"
                                checked={selectedPosts.includes(p.id)}
                                onChange={(e) => setSelectedPosts((prev) => e.target.checked ? [...prev, p.id] : prev.filter((x) => x !== p.id))}
                              />
                              {p.title} <span className="sf-dim">#{p.id}</span>
                            </label>
                          </li>
                        ))}
                      </ul>
                      {selectedPosts.length > 0 && (
                        <button type="button" className="btn btn-secondary" onClick={() => handleAssignQueue(selectedPosts)} disabled={loading}>
                          {selectedPosts.length} ilanı bu kategoriye taşı
                        </button>
                      )}
                    </>
                  ) : (
                    <>
                      <h4>Hikaye gönder</h4>
                      <input className="storyforge-input" placeholder="Başlık (opsiyonel)" value={storyTitle} onChange={(e) => setStoryTitle(e.target.value)} />
                      <textarea className="storyforge-textarea" rows={10} placeholder="Hikaye metni…" value={storyText} onChange={(e) => setStoryText(e.target.value)} />
                      <button type="button" className="btn btn-primary" onClick={handlePublishStory} disabled={loading}>
                        Bu kategoriye hikaye yayınla
                      </button>
                      {onNavigateStoryForge && (
                        <button type="button" className="btn btn-outline btn-small" onClick={onNavigateStoryForge}>
                          StoryForge&apos;da toplu işle →
                        </button>
                      )}
                      <h4 className="ch-h4">Kategorisiz hikayeler</h4>
                      <ul className="ch-queue-list">
                        {queue.slice(0, 10).map((p) => (
                          <li key={p.id}>
                            <button type="button" className="ch-link-btn" onClick={() => handleAssignQueue([p.id])}>
                              + {p.title}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              )}

          {tab === "send" && !selected && (
            <p className="ch-hint-box">İlan veya hikaye göndermek için sol ağaçtan bir kategori seç.</p>
          )}

          {tab === "detail" && selected && (
                <div className="ch-panel">
                  <h4>SEO & düzenle</h4>
                  <input className="storyforge-input" value={seoName} onChange={(e) => setSeoName(e.target.value)} />
                  <textarea className="storyforge-textarea" rows={3} placeholder="Kategori açıklaması (SEO)" value={seoDesc} onChange={(e) => setSeoDesc(e.target.value)} />
                  <button type="button" className="btn btn-secondary" onClick={handleSeoSave} disabled={loading}>Kaydet</button>

                  <h4 className="ch-h4">Canlı doğrulama</h4>
                  {verify && (
                    <p className={verify.live ? "sf-ok" : "sf-warn"}>
                      HTTP {verify.status_code || "?"} — {verify.link || "Link yok"}
                    </p>
                  )}
                  <button type="button" className="btn btn-outline btn-small" onClick={() => selected && loadTermDetail(selected)}>
                    Yeniden kontrol et
                  </button>

                  <h4 className="ch-h4">Kategori birleştir</h4>
                  <p className="sf-dim">Kaynak kategori ID&apos;sini gir — tüm içerik bu kategoriye taşınır, kaynak silinir.</p>
                  <div className="storyforge-url-row">
                    <input className="storyforge-input" placeholder="Birleştirilecek kategori ID" value={mergeSource} onChange={(e) => setMergeSource(e.target.value)} />
                    <button type="button" className="btn btn-outline" onClick={handleMerge} disabled={loading}>Birleştir</button>
                  </div>

                  <h4 className="ch-h4">Bu kategorideki içerik ({termContent.length})</h4>
                  <ul className="ch-content-list">
                    {termContent.map((p) => (
                      <li key={p.id}>
                        <a href={p.link} target="_blank" rel="noopener noreferrer">{p.title || `#${p.id}`}</a>
                        <span className="sf-dim"> {p.status}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

          {tab === "detail" && !selected && (
            <p className="ch-hint-box">Detay ve SEO için sol taraftan kategori seç.</p>
          )}

          {tab === "queue" && (
                <div className="ch-panel">
                  <h4>Kategorisiz kuyruk ({queue.length})</h4>
                  <p className="sf-dim">
                    {selected ? `Seçili kategoriye ata: ${selected.name}` : "Atamak için sol taraftan kategori seç, sonra işaretle."}
                  </p>
                  <ul className="ch-queue-list">
                    {queue.map((p) => (
                      <li key={p.id}>
                        <label>
                          <input
                            type="checkbox"
                            checked={selectedPosts.includes(p.id)}
                            onChange={(e) => setSelectedPosts((prev) => e.target.checked ? [...prev, p.id] : prev.filter((x) => x !== p.id))}
                          />
                          {p.title} <span className="sf-dim">#{p.id}</span>
                        </label>
                      </li>
                    ))}
                  </ul>
                  {queue.length > 0 && selected && (
                    <button type="button" className="btn btn-primary" onClick={() => handleAssignQueue(selectedPosts.length ? selectedPosts : queue.map((p) => p.id))} disabled={loading}>
                      Seçilenleri / tümünü ata
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
                <strong>{item.name || item.title}</strong>
                <span className="sf-dim"> #{item.id} /{item.slug}</span>
                {item.link ? (
                  <a href={item.link} target="_blank" rel="noopener noreferrer" className="ch-live-link"> — sitede aç</a>
                ) : (
                  <span className="sf-dim"> — sol ağaçtan seç, Detay sekmesinde canlı link</span>
                )}
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
