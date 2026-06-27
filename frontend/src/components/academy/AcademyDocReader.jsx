import React, { useEffect, useMemo, useState } from "react";
import API from "../../api";
import MarkdownBody from "./MarkdownBody";
import { AcademySkeleton } from "./AcademyUI";
import { LEARNING_PATH, resolveModuleNavId } from "./academyConfig";

const API_PREFIX = "/api/academy";

const CHECKLIST_KEYS = [
  { key: "read", label: "Okudum" },
  { key: "applied", label: "Uyguladım" },
  { key: "tested", label: "Test ettim" },
  { key: "completed", label: "Tamamladım" },
];

function LearningPathBar({ currentSection, currentStep }) {
  const idx = LEARNING_PATH.findIndex((s) => s.id === currentStep);
  return (
    <div className="ha-learning-path">
      {LEARNING_PATH.map((step, i) => (
        <React.Fragment key={step.id}>
          <span className={`ha-path-step ${currentSection && step.sectionSlugs?.includes(currentSection) ? "active" : ""} ${idx > i ? "done" : ""}`}>
            {step.label}
          </span>
          {i < LEARNING_PATH.length - 1 && <span className="ha-path-arrow">↓</span>}
        </React.Fragment>
      ))}
    </div>
  );
}

function DocMetaCards({ meta, readingTime, badgeReward, status, quality }) {
  const learn = meta.learn_items || meta.related || [];
  const prereq = meta.prerequisites || [];
  const statusLabel = { completed: "Tamamlandı", in_progress: "Devam ediyor", not_started: "Başlanmadı" };
  return (
    <div className="ha-learning-card">
      <div className="ha-doc-meta-grid">
        <div className="ha-meta-card">📚 <strong>{readingTime || meta.reading_time_minutes || "?"}</strong> dk</div>
        <div className="ha-meta-card">🎯 <strong>{meta.difficulty || meta.level || "—"}</strong></div>
        <div className="ha-meta-card">⭐ <span>{Array.isArray(learn) ? learn.slice(0, 2).join(", ") : learn || "—"}</span></div>
        <div className="ha-meta-card">📍 <span>{Array.isArray(prereq) ? prereq.join(", ") || "Yok" : prereq || "Yok"}</span></div>
        <div className="ha-meta-card">📦 v{meta.version || "1.0"}</div>
        <div className="ha-meta-card">📅 {meta.last_updated || "—"}</div>
        <div className="ha-meta-card">👤 {meta.last_editor || meta.owner || "HIVE Team"}</div>
        <div className="ha-meta-card">🏆 {badgeReward || meta.badge_reward || "—"}</div>
        <div className="ha-meta-card ha-status-pill" data-status={status}>{statusLabel[status] || status}</div>
      </div>
      {quality?.total != null && (
        <div className="ha-quality-bar">
          <span>Quality: {quality.total}/100</span>
          <div className="ha-quality-dims">
            {Object.entries(quality.scores || {}).filter(([k]) => !["published"].includes(k)).slice(0, 7).map(([k, v]) => (
              <span key={k} title={k}>{k.slice(0, 4)}:{v}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function InteractiveChecklist({ slug, initial, onChange }) {
  const [items, setItems] = useState(initial || {});

  useEffect(() => {
    setItems(initial || {});
  }, [slug, initial]);

  const toggle = async (key) => {
    const next = { ...items, [key]: !items[key] };
    setItems(next);
    onChange?.(next);
    try {
      await API.post(`${API_PREFIX}/checklist`, { slug, checklist: next });
    } catch { /* ignore */ }
  };

  return (
    <div className="ha-checklist">
      <h3>Interactive Checklist</h3>
      {CHECKLIST_KEYS.map(({ key, label }) => (
        <label key={key} className="ha-checklist-item">
          <input type="checkbox" checked={!!items[key]} onChange={() => toggle(key)} />
          {label}
        </label>
      ))}
    </div>
  );
}

function AcademyMissions({ missions, slug, onNavigateModule, onComplete }) {
  if (!missions?.length) return null;
  return (
    <div className="ha-missions">
      <h3>🎯 Görevler — Gerçek iş yap</h3>
      {missions.map((m) => (
        <div key={m.id} className={`ha-mission-row ${m.completed ? "done" : ""}`}>
          <span>{m.completed ? "✓" : "○"}</span>
          <div>
            <strong>{m.title}</strong>
            {m.description && <p className="ha-muted">{m.description}</p>}
          </div>
          <div className="ha-mission-actions">
            {m.navigate_to && !m.completed && (
              <button
                type="button"
                className="ha-launch-btn"
                onClick={() => {
                  const navId = resolveModuleNavId(m.navigate_to);
                  if (navId) onNavigateModule?.(navId);
                }}
              >
                Aç
              </button>
            )}
            {!m.completed && (
              <button
                type="button"
                className="ha-btn"
                onClick={async () => {
                  try {
                    await API.post(`${API_PREFIX}/mission/complete`, { slug, mission_id: m.id });
                    onComplete?.();
                  } catch { /* */ }
                }}
              >
                Tamamlandı
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function AcademyQuiz({ quiz, slug, onComplete }) {
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  if (!quiz?.questions?.length) return null;
  const questions = quiz.questions;

  const submit = async () => {
    let score = 0;
    questions.forEach((q, i) => {
      if (answers[i] === q.correct) score += 1;
    });
    setSubmitted(true);
    try {
      await API.post(`${API_PREFIX}/quiz`, { slug, score, total: questions.length });
    } catch { /* ignore */ }
    onComplete?.(score, questions.length);
  };

  return (
    <div className="ha-quiz">
      <h3>📝 Quiz — {quiz.title || slug}</h3>
      {questions.map((q, i) => (
        <div key={i} className="ha-quiz-q">
          <p><strong>{i + 1}.</strong> {q.q}</p>
          {q.options.map((opt, j) => (
            <label key={j} className="ha-quiz-opt">
              <input
                type="radio"
                name={`q-${i}`}
                disabled={submitted}
                checked={answers[i] === j}
                onChange={() => setAnswers((a) => ({ ...a, [i]: j }))}
              />
              {opt}
            </label>
          ))}
          {submitted && (
            <p className={answers[i] === q.correct ? "ha-quiz-ok" : "ha-quiz-fail"}>
              {answers[i] === q.correct ? "✓ Doğru" : "✗ Yanlış"} — {q.explain}
            </p>
          )}
        </div>
      ))}
      {!submitted && <button type="button" className="ha-btn primary" onClick={submit}>Quiz'i Bitir</button>}
    </div>
  );
}

function ScreenshotGallery({ shots }) {
  const [zoom, setZoom] = useState(null);
  const [compare, setCompare] = useState(false);
  if (!shots?.length) return null;
  return (
    <div className="ha-screenshots">
      <div className="ha-screenshot-toolbar">
        <h3>Ekran Görüntüleri</h3>
        {shots.length >= 2 && (
          <button type="button" className="ha-btn" onClick={() => setCompare((v) => !v)}>
            {compare ? "Galeri" : "Önce / Sonra"}
          </button>
        )}
      </div>
      {compare && shots.length >= 2 ? (
        <div className="ha-before-after">
          <figure><img src={shots[0].src} alt={shots[0].title} /><figcaption>Önce</figcaption></figure>
          <figure><img src={shots[1].src} alt={shots[1].title} /><figcaption>Sonra</figcaption></figure>
        </div>
      ) : (
        <div className="ha-screenshot-grid">
          {shots.map((s, i) => (
            <figure key={i} className="ha-screenshot-card">
              <button type="button" className="ha-screenshot-zoom" onClick={() => setZoom(s)}>
                <img src={s.src} alt={s.title} loading="lazy" />
              </button>
              <figcaption><strong>{i + 1}.</strong> {s.title}</figcaption>
              {s.caption && <p className="ha-muted">{s.caption}</p>}
            </figure>
          ))}
        </div>
      )}
      {zoom && (
        <div className="ha-lightbox" onClick={() => setZoom(null)} role="presentation">
          <button type="button" className="ha-lightbox-close" onClick={() => setZoom(null)}>✕</button>
          <img src={zoom.src} alt={zoom.title} />
          <p>{zoom.title}</p>
        </div>
      )}
    </div>
  );
}

function KnowledgeGraph({ nodes, onOpenSlug, onNavigateModule }) {
  if (!nodes?.length) return null;
  return (
    <div className="ha-knowledge-graph">
      <h3>Knowledge Graph</h3>
      <div className="ha-kg-flow">
        {nodes.map((n, i) => (
          <React.Fragment key={`${n.type}-${n.slug || n.id}-${i}`}>
            {n.type === "doc" ? (
              <button type="button" className="ha-kg-node" onClick={() => onOpenSlug?.(n.slug)}>{n.label || n.slug}</button>
            ) : n.type === "module" ? (
              <button type="button" className="ha-kg-node module" onClick={() => onNavigateModule?.(resolveModuleNavId(n.id))}>{n.label}</button>
            ) : (
              <span className="ha-kg-node static">{n.label || n.id}</span>
            )}
            {i < nodes.length - 1 && <span className="ha-path-arrow">↓</span>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

export default function AcademyDocReader({
  doc,
  loading,
  slug,
  favorited,
  note,
  onToggleFavorite,
  onSaveNote,
  onNavigateModule,
  onOpenSlug,
  onBack,
  onFeedback,
  scrollProgress,
  readingMode,
  currentLearningStep,
  onDocRefresh,
}) {
  const [localNote, setLocalNote] = useState(note || "");
  const [inDocSearch, setInDocSearch] = useState("");
  const [toc, setToc] = useState([]);
  const headingsRef = React.useRef(null);

  useEffect(() => { setLocalNote(note || ""); }, [note, slug]);

  useEffect(() => {
    if (!headingsRef.current) return;
    const hs = headingsRef.current.querySelectorAll("h2, h3");
    setToc(Array.from(hs).map((h) => ({ id: h.id, text: h.textContent, level: h.tagName })));
  }, [doc?.content]);

  const filteredContent = useMemo(() => {
    if (!doc?.content) return "";
    if (!inDocSearch.trim()) return doc.content;
    const q = inDocSearch.toLowerCase();
    return doc.content.split("\n").filter((line) => line.toLowerCase().includes(q)).join("\n\n") || doc.content;
  }, [doc?.content, inDocSearch]);

  const meta = doc?.meta || {};
  const related = {
    modules: meta.related_modules || meta.related || [],
    api: meta.related_api || [],
    workflow: meta.related_workflow || [],
    videos: meta.related_videos || [],
  };

  if (loading && !doc) return <AcademySkeleton lines={8} />;
  if (!doc) return null;

  const readerClass = `ha-reader-main ha-reading-${readingMode || "normal"}`;

  return (
    <div className="ha-reader-layout">
      <div className={readerClass}>
        <div className="ha-breadcrumb">
          <button type="button" className="ha-link-btn" onClick={onBack}>Academy</button>
          <span> / </span>
          <span>{meta.category || doc.section_title || "Doküman"}</span>
          <span> / </span>
          <strong>{meta.title || slug}</strong>
        </div>

        <div className="ha-reading-progress" style={{ width: `${scrollProgress || 0}%` }} />

        <LearningPathBar currentSection={doc.section_slug} currentStep={currentLearningStep} />

        <DocMetaCards
          meta={meta}
          readingTime={doc.reading_time_minutes}
          badgeReward={doc.badge_reward}
          status={doc.status}
          quality={doc.quality}
        />

        <div className="ha-in-doc-search">
          <input
            type="search"
            placeholder="Bu sayfada ara…"
            value={inDocSearch}
            onChange={(e) => setInDocSearch(e.target.value)}
          />
          {toc.length > 0 && (
            <div className="ha-toc">
              {toc.map((t) => (
                <a key={t.id} href={`#${t.id}`} className={t.level === "H3" ? "indent" : ""}>{t.text}</a>
              ))}
            </div>
          )}
        </div>

        <div className="ha-video-placeholder">
          <h3>▶ Video Academy</h3>
          <p className="ha-muted">Video içeriği yakında — placeholder</p>
        </div>

        <MarkdownBody
          content={filteredContent}
          headingsRef={headingsRef}
          onModuleLaunch={(mod) => {
            const navId = resolveModuleNavId(mod);
            if (navId) onNavigateModule?.(navId);
          }}
        />

        <ScreenshotGallery shots={doc.screenshots} />

        <InteractiveChecklist slug={slug} initial={doc.checklist} onChange={() => onDocRefresh?.()} />

        <AcademyMissions
          missions={doc.missions}
          slug={slug}
          onNavigateModule={onNavigateModule}
          onComplete={onDocRefresh}
        />

        <div className="ha-launch-shortcuts">
          {(related.modules || []).slice(0, 4).map((m) => {
            const navId = resolveModuleNavId(typeof m === "string" ? m : m.id);
            if (!navId) return null;
            return (
              <button key={String(m)} type="button" className="ha-launch-btn" onClick={() => onNavigateModule(navId)}>
                🚀 Aç — {typeof m === "string" ? m : m.title || m}
              </button>
            );
          })}
        </div>

        <AcademyQuiz quiz={doc.quiz} slug={slug} onComplete={onDocRefresh} />

        <KnowledgeGraph
          nodes={doc.knowledge_graph}
          onOpenSlug={onOpenSlug}
          onNavigateModule={onNavigateModule}
        />

        {(doc.recommendations || []).length > 0 && (
          <div className="ha-recommendations">
            <h3>Bunları da öğrenmek isteyebilirsin</h3>
            <div className="ha-peer-list">
              {doc.recommendations.map((r) => (
                <button key={r.slug} type="button" className="ha-link-btn" onClick={() => onOpenSlug(r.slug)}>
                  {r.title}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="ha-doc-nav">
          <div>
            {doc.prev && (
              <button type="button" className="ha-btn" onClick={() => onOpenSlug(doc.prev.slug)}>
                ⬅ {doc.prev.title}
              </button>
            )}
          </div>
          <div>
            {doc.next && (
              <button type="button" className="ha-btn primary" onClick={() => onOpenSlug(doc.next.slug)}>
                {doc.next.title} ➡
              </button>
            )}
          </div>
        </div>

        {doc.category_peers?.length > 0 && (
          <div className="ha-same-category">
            <h4>📖 Aynı kategoridekiler</h4>
            <div className="ha-peer-list">
              {doc.category_peers.map((p) => (
                <button key={p.slug} type="button" className="ha-link-btn" onClick={() => onOpenSlug(p.slug)}>
                  {p.title}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="ha-version-history">
          <h4>Version History</h4>
          <ul>
            {(meta.version_history || [meta.version || "1.0.0"]).map((v) => (
              <li key={v}>{v} — {meta.last_updated || ""} — {meta.last_editor || "HIVE Team"}</li>
            ))}
          </ul>
        </div>

        <p className="ha-ai-slot">{/* AI_UPDATE_SLOT */}</p>

        <div className="ha-feedback-v2">
          <strong>Geri bildirim</strong>
          <div className="ha-feedback-actions">
            <button type="button" className="ha-btn" onClick={() => onFeedback("helpful", true)}>👍</button>
            <button type="button" className="ha-btn" onClick={() => onFeedback("not_helpful", false)}>👎</button>
            <button type="button" className="ha-btn" onClick={() => onFeedback("missing", false)}>Eksik Bildir</button>
            <button type="button" className="ha-btn" onClick={() => onFeedback("error", false)}>Hata Bildir</button>
            <button type="button" className="ha-btn" onClick={() => onFeedback("improve", true)}>İyileştirme Öner</button>
          </div>
        </div>
      </div>

      <aside className="ha-reader-aside">
        <button type="button" className={`ha-fav-btn ${favorited ? "on" : ""}`} onClick={onToggleFavorite}>
          {favorited ? "★ Favoride" : "☆ Favori"}
        </button>

        <div className="ha-aside-block">
          <h4>İlgili Modüller</h4>
          <ul>
            {(related.modules || []).map((m) => {
              const navId = resolveModuleNavId(typeof m === "string" ? m : m.id);
              return (
                <li key={String(m)}>
                  {navId ? (
                    <button type="button" className="ha-link-btn" onClick={() => onNavigateModule(navId)}>Aç — {typeof m === "string" ? m : m.title}</button>
                  ) : (typeof m === "string" ? m : m.title)}
                </li>
              );
            })}
          </ul>
        </div>
        <div className="ha-aside-block">
          <h4>İlgili API</h4>
          <ul>{(related.api || []).map((a) => <li key={a}><code>{a}</code></li>)}</ul>
        </div>
        <div className="ha-aside-block">
          <h4>İlgili Workflow</h4>
          <ul>{(related.workflow || []).map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
        <div className="ha-aside-block">
          <h4>Video Academy</h4>
          <ul>{(related.videos || []).length ? related.videos.map((v) => <li key={v}>{v}</li>) : <li className="ha-muted">Yakında</li>}</ul>
        </div>

        <div className="ha-notes">
          <h4>Notlarım</h4>
          <textarea
            value={localNote}
            onChange={(e) => setLocalNote(e.target.value)}
            placeholder="Markdown destekli not…"
            rows={6}
          />
          <button type="button" className="ha-btn primary" onClick={() => onSaveNote(localNote)}>Kaydet</button>
        </div>
      </aside>
    </div>
  );
}
