import React, { useState, useEffect, useCallback } from "react";
import API from "../api";


export default function RedditManager() {
  const [query, setQuery] = useState("kusadasi escort");
  const [subreddit, setSubreddit] = useState("Turkey");
  const [searchResults, setSearchResults] = useState([]);
  const [subResults, setSubResults] = useState([]);
  const [session, setSession] = useState(null);
  const [commentData, setCommentData] = useState({ postUrl: "", text: "" });
  const [postData, setPostData] = useState({ subreddit: "", title: "", text: "" });
  const [postUrl, setPostUrl] = useState("");
  const [postDetail, setPostDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refreshStatus = useCallback(async () => {
    try {
      const res = await API.get("/api/reddit/mcp/status");
      setSession(res.data);
    } catch {
      setSession({ success: false });
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const handleAuthorize = async () => {
    setError("");
    setMessage("Tarayıcı açılıyor — Reddit'e giriş yapın...");
    try {
      const res = await API.post("/api/reddit/authorize");
      setMessage(res.data.message || "Yetkilendirme başlatıldı");
      refreshStatus();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setMessage("");
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.get("/api/reddit/search", {
        params: { query: query.trim(), limit: 20 },
      });
      setSearchResults(res.data.results || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const handleSubreddit = async () => {
    if (!subreddit.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.get("/api/reddit/subreddit", {
        params: { subreddit: subreddit.trim(), limit: 20, sort: "hot" },
      });
      setSubResults(res.data.posts || res.data.results || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const handleGetPost = async () => {
    if (!postUrl.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.get("/api/reddit/post", { params: { post_url: postUrl.trim() } });
      setPostDetail(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const handleComment = async () => {
    if (!commentData.postUrl || !commentData.text) {
      setError("Post URL ve yorum metni gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await API.post("/api/reddit/comment", {
        post_url: commentData.postUrl,
        text: commentData.text,
      });
      setMessage("Yorum gönderildi!");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const handlePost = async () => {
    if (!postData.subreddit || !postData.title) {
      setError("Subreddit ve başlık gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/reddit/mcp/post", postData);
      setMessage(res.data.result?.permalink ? `Post yayınlandı: ${res.data.result.permalink}` : "Post gönderildi!");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const renderPosts = (posts) => {
    if (!posts?.length) return <p className="sf-dim">Sonuç yok</p>;
    return (
      <ul className="storyforge-photo-list">
        {posts.map((post, idx) => (
          <li key={post.id || idx}>
            <a href={post.permalink || post.url} target="_blank" rel="noreferrer">
              <strong>{post.title}</strong>
            </a>
            <span className="sf-dim"> — r/{post.subreddit || "?"} · 👍 {post.score ?? post.ups ?? 0}</span>
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="storyforge-panel">
      <header className="storyforge-header">
        <h2>Reddit Yöneticisi (Reddirect MCP)</h2>
        <p className="storyforge-sub">
          API key gerektirmez — okuma anonim, yazma için bir kez tarayıcıdan yetkilendir
        </p>
      </header>

      {session && (
        <div className="storyforge-stats">
          <span className={session.success ? "sf-ok" : "sf-warn"}>
            Motor: reddirect MCP
          </span>
          {session.session?.username && <span>Kullanıcı: u/{session.session.username}</span>}
          {session.tools_count && <span>{session.tools_count} araç</span>}
        </div>
      )}

      <div className="storyforge-btn-row">
        <button type="button" className="btn btn-primary" onClick={handleAuthorize}>
          Yetkilendir (bir kez — yazma için)
        </button>
        <button type="button" className="btn btn-outline" onClick={refreshStatus}>
          Durumu Yenile
        </button>
      </div>

      {message && <p className="storyforge-ok">{message}</p>}
      {error && <p className="storyforge-error">{error}</p>}

      <section className="storyforge-auto">
        <h3>Arama</h3>
        <div className="storyforge-url-row">
          <input
            className="storyforge-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Kuşadası escort"
          />
          <button type="button" className="btn btn-primary" onClick={handleSearch} disabled={loading}>
            {loading ? "..." : "Ara"}
          </button>
        </div>
        {renderPosts(searchResults)}
      </section>

      <section className="storyforge-auto">
        <h3>Subreddit Gez</h3>
        <div className="storyforge-url-row">
          <input
            className="storyforge-input"
            value={subreddit}
            onChange={(e) => setSubreddit(e.target.value)}
            placeholder="Turkey"
          />
          <button type="button" className="btn btn-secondary" onClick={handleSubreddit} disabled={loading}>
            Getir
          </button>
        </div>
        {renderPosts(subResults)}
      </section>

      <section className="storyforge-auto">
        <h3>Post Detayı + Yorumlar</h3>
        <div className="storyforge-url-row">
          <input
            className="storyforge-input"
            value={postUrl}
            onChange={(e) => setPostUrl(e.target.value)}
            placeholder="https://reddit.com/r/.../comments/..."
          />
          <button type="button" className="btn btn-secondary" onClick={handleGetPost} disabled={loading}>
            Getir
          </button>
        </div>
        {postDetail && (
          <pre style={{ fontSize: "0.75rem", maxHeight: 200, overflow: "auto", background: "var(--bg3)", padding: "0.75rem", borderRadius: 8 }}>
            {JSON.stringify(postDetail, null, 2).slice(0, 3000)}
          </pre>
        )}
      </section>

      <section className="storyforge-auto">
        <h3>Yorum Yap</h3>
        <input
          className="storyforge-input"
          placeholder="Post URL"
          value={commentData.postUrl}
          onChange={(e) => setCommentData({ ...commentData, postUrl: e.target.value })}
        />
        <textarea
          className="storyforge-textarea"
          rows={4}
          placeholder="Yorumunuz"
          value={commentData.text}
          onChange={(e) => setCommentData({ ...commentData, text: e.target.value })}
        />
        <button type="button" className="btn btn-primary" onClick={handleComment} disabled={loading}>
          Yorum Gönder
        </button>
      </section>

      <section className="storyforge-auto">
        <h3>Yeni Post Aç</h3>
        <input
          className="storyforge-input"
          placeholder="Subreddit (ör: Turkey)"
          value={postData.subreddit}
          onChange={(e) => setPostData({ ...postData, subreddit: e.target.value })}
        />
        <input
          className="storyforge-input"
          placeholder="Başlık"
          value={postData.title}
          onChange={(e) => setPostData({ ...postData, title: e.target.value })}
        />
        <textarea
          className="storyforge-textarea"
          rows={5}
          placeholder="İçerik"
          value={postData.text}
          onChange={(e) => setPostData({ ...postData, text: e.target.value })}
        />
        <button type="button" className="btn btn-primary" onClick={handlePost} disabled={loading}>
          Post Gönder
        </button>
      </section>
    </div>
  );
}
