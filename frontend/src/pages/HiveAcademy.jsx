import React, { useCallback, useEffect, useState } from "react";
import API from "../api";
import HiveApiErrorCard from "../components/HiveApiErrorCard";
import { formatHiveApiError } from "../utils/hiveApiErrors";
import AcademyDashboard from "../components/academy/dashboard/AcademyDashboard";
import AcademyLayout from "../components/academy/dashboard/AcademyLayout";
import AcademyDocReader from "../components/academy/AcademyDocReader";
import AcademyCommandPalette from "../components/academy/AcademyCommandPalette";
import AcademyAIAssistant from "../components/academy/AcademyAIAssistant";
import AcademyHealth from "../components/academy/AcademyHealth";
import AcademyChangelog from "../components/academy/AcademyChangelog";
import { AcademyToast } from "../components/academy/AcademyUI";
import { useAcademyTheme, useReadingMode } from "../components/academy/academyTheme";
import { FALLBACK_DASHBOARD, normalizeDashboard, isDashboardApiError } from "../components/academy/dashboard/academyFallbackDashboard";
import "../components/academy/styles/academy.css";
import "./HiveAcademy.css";

const API_PREFIX = "/api/academy";

export default function HiveAcademy({ onNavigate }) {
  const [view, setView] = useState("dashboard");
  const [activeSlug, setActiveSlug] = useState("");
  const [index, setIndex] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [doc, setDoc] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [showPalette, setShowPalette] = useState(false);
  const [favorites, setFavorites] = useState([]);
  const [note, setNote] = useState("");
  const [scrollProgress, setScrollProgress] = useState(0);
  const [readStart, setReadStart] = useState(null);
  const [showAI, setShowAI] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [toast, setToast] = useState("");
  const { theme, setTheme } = useAcademyTheme();
  const { mode: readingMode, setMode: setReadingMode } = useReadingMode();

  const loadDashboard = useCallback(async () => {
    let dashData = normalizeDashboard(FALLBACK_DASHBOARD);
    try {
      try {
        const dash = await API.get(`${API_PREFIX}/dashboard`);
        dashData = normalizeDashboard(dash.data);
      } catch (e) {
        if (isDashboardApiError(e)) {
          dashData = normalizeDashboard({ ...FALLBACK_DASHBOARD, fallback: true });
        } else {
          dashData = normalizeDashboard(FALLBACK_DASHBOARD);
        }
      }
      setDashboard(dashData);
      setError("");
      try {
        const [idx, fav, prog] = await Promise.all([
          API.get(`${API_PREFIX}/index`),
          API.get(`${API_PREFIX}/favorites`),
          API.get(`${API_PREFIX}/progress`),
        ]);
        setIndex(idx.data);
        setFavorites(fav.data.favorites || []);
        setProgress(prog.data);
      } catch {
        /* index/favorites optional — dashboard still renders */
      }
    } catch {
      setDashboard(normalizeDashboard(FALLBACK_DASHBOARD));
    }
  }, []);

  const openDoc = useCallback(async (slug) => {
    if (!slug) return;
    setView("reader");
    setActiveSlug(slug);
    setLoading(true);
    setError("");
    setReadStart(Date.now());
    try {
      const [docRes, noteRes] = await Promise.all([
        API.get(`${API_PREFIX}/doc/${encodeURIComponent(slug)}`),
        API.get(`${API_PREFIX}/notes`, { params: { slug } }),
      ]);
      setDoc(docRes.data);
      setNote(noteRes.data.note?.content || "");
      await API.post(`${API_PREFIX}/progress`, { slug, read_seconds: 0, completed: false });
    } catch (e) {
      setError(formatHiveApiError(e, `${API_PREFIX}/doc/${slug}`));
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshDoc = useCallback(async () => {
    if (!activeSlug) return;
    try {
      const docRes = await API.get(`${API_PREFIX}/doc/${encodeURIComponent(activeSlug)}`);
      setDoc(docRes.data);
      loadDashboard();
    } catch { /* */ }
  }, [activeSlug, loadDashboard]);

  const markComplete = useCallback(async (slug) => {
    const sec = readStart ? Math.round((Date.now() - readStart) / 1000) : 30;
    try {
      await API.post(`${API_PREFIX}/progress`, { slug, read_seconds: sec, completed: true });
      loadDashboard();
    } catch { /* ignore */ }
  }, [readStart, loadDashboard]);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  useEffect(() => {
    const onScroll = () => {
      const el = document.querySelector(".ha-reader-main");
      if (!el) return;
      const max = el.scrollHeight - el.clientHeight;
      setScrollProgress(max > 0 ? Math.min(100, (el.scrollTop / max) * 100) : 0);
      if (max > 0 && el.scrollTop / max > 0.85 && activeSlug) markComplete(activeSlug);
    };
    const el = document.querySelector(".ha-reader-main");
    el?.addEventListener("scroll", onScroll);
    return () => el?.removeEventListener("scroll", onScroll);
  }, [activeSlug, markComplete, view]);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setShowPalette((v) => !v);
      }
      if (e.key === "Escape") {
        setShowPalette(false);
        setSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!searchQ.trim()) {
        setSearchResults([]);
        return;
      }
      try {
        const res = await API.get(`${API_PREFIX}/search`, { params: { q: searchQ, semantic: true } });
        setSearchResults(res.data.results || []);
      } catch {
        setSearchResults([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [searchQ]);

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const toggleFavorite = async () => {
    try {
      const res = await API.post(`${API_PREFIX}/favorite`, { slug: activeSlug });
      setFavorites(res.data.favorites || []);
    } catch (e) {
      setError(formatHiveApiError(e, `${API_PREFIX}/favorite`));
    }
  };

  const saveNote = async (content) => {
    try {
      await API.post(`${API_PREFIX}/notes`, { slug: activeSlug, content });
      setNote(content);
    } catch (e) {
      setError(formatHiveApiError(e, `${API_PREFIX}/notes`));
    }
  };

  const sendFeedback = async (feedbackType, helpful) => {
    try {
      await API.post(`${API_PREFIX}/feedback`, {
        slug: activeSlug,
        helpful,
        feedback_type: feedbackType,
        version: doc?.meta?.version,
      });
      setToast("Geri bildiriminiz kaydedildi. Teşekkürler.");
    } catch (e) {
      setError(formatHiveApiError(e, `${API_PREFIX}/feedback`));
    }
  };

  const docStatus = (slug) => (progress?.statuses || {})[slug] || "not_started";

  const goDashboard = () => {
    setView("dashboard");
    loadDashboard();
  };

  return (
    <>
      {error && (
        <div style={{ padding: "8px 16px" }}>
          <HiveApiErrorCard errorInfo={error} />
        </div>
      )}
      <AcademyToast message={toast} onClose={() => setToast("")} />

      <AcademyCommandPalette
        open={showPalette}
        onClose={() => setShowPalette(false)}
        onOpenDoc={(slug) => { openDoc(slug); setShowPalette(false); }}
        onNavigateModule={onNavigate}
      />

      <AcademyLayout
        view={view}
        index={index}
        favorites={favorites}
        docStatus={docStatus}
        activeSlug={activeSlug}
        searchQ={searchQ}
        onSearchChange={setSearchQ}
        onSearchSubmit={() => searchResults[0] && openDoc(searchResults[0].slug)}
        searchResults={searchResults}
        onOpenDoc={openDoc}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onCloseSidebar={() => setSidebarOpen(false)}
        theme={theme}
        onThemeChange={setTheme}
        onOpenPalette={() => setShowPalette(true)}
        onOpenHealth={() => setView("health")}
        onOpenChangelog={() => setView("changelog")}
        onNavigate={onNavigate}
        onGoDashboard={goDashboard}
        showReaderAI={view === "reader" && showAI}
        aiPanel={view === "reader" && showAI ? (
          <AcademyAIAssistant slug={activeSlug} collapsed={false} onToggle={() => setShowAI(false)} />
        ) : null}
        aiCollapsed={view === "reader" && !showAI ? (
          <AcademyAIAssistant slug={activeSlug} collapsed onToggle={() => setShowAI(true)} />
        ) : null}
      >
        {view === "dashboard" && (
          <AcademyDashboard
            data={dashboard}
            progress={progress}
            index={index}
            onContinue={openDoc}
            onOpenDoc={openDoc}
            onNavigate={onNavigate}
            learningPath={dashboard?.learning_path}
            currentStep={dashboard?.current_learning_step}
            onViewAllDocs={() => openDoc(index?.sections?.[0]?.items?.[0]?.slug)}
          />
        )}
        {view === "health" && (
          <div className="academy-subpage">
            <button type="button" className="academy-link" onClick={goDashboard}>← Dashboard</button>
            <AcademyHealth onOpenDoc={(slug) => { openDoc(slug); setSidebarOpen(false); }} />
          </div>
        )}
        {view === "changelog" && (
          <div className="academy-subpage">
            <AcademyChangelog onBack={goDashboard} />
          </div>
        )}
        {view === "reader" && (
          <div className="ha-reader-wrap">
            {readingMode !== "normal" && (
              <div className="academy-reader-toolbar">
                <select value={readingMode} onChange={(e) => setReadingMode(e.target.value)}>
                  <option value="normal">Normal</option>
                  <option value="focus">Focus</option>
                  <option value="print">Print</option>
                </select>
                {readingMode === "print" && (
                  <button type="button" className="academy-btn" onClick={() => window.print()}>Yazdır</button>
                )}
              </div>
            )}
            <AcademyDocReader
              doc={doc}
              loading={loading}
              slug={activeSlug}
              favorited={favorites.includes(activeSlug)}
              note={note}
              scrollProgress={scrollProgress}
              readingMode={readingMode}
              currentLearningStep={dashboard?.current_learning_step}
              onToggleFavorite={toggleFavorite}
              onSaveNote={saveNote}
              onNavigateModule={onNavigate}
              onOpenSlug={openDoc}
              onBack={goDashboard}
              onFeedback={sendFeedback}
              onDocRefresh={refreshDoc}
            />
          </div>
        )}
      </AcademyLayout>
    </>
  );
}
