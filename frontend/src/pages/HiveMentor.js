import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { HiveCommandBar } from "../components/HiveAppShell";
import {
  HiveShell,
  HivePanel,
  HiveBtn,
  HiveBadge,
  HiveSection,
  HiveEmptyState,
} from "../components/HiveModuleUI";
import HiveApiErrorCard from "../components/HiveApiErrorCard";
import { formatHiveApiError } from "../utils/hiveApiErrors";

const API_PREFIX = "/api/hive-mentor";

const PRIORITY_TONE = { CRITICAL: "danger", HIGH: "warning", MEDIUM: "info", LOW: "neutral" };

const INTENT_LABELS = {
  keyword_growth: "Keyword Büyütme",
  serp_defense: "SERP Savunması",
  publish: "İçerik Yayınlama",
  authority: "Authority Kurma",
  new_site: "Yeni Site",
  faq_content: "FAQ İçerik",
  daily_ops: "Günlük Operasyon",
  google_sites_setup: "Google Sites Kurulum",
  wordpress_setup: "WordPress Bağlantı",
  github_pages_setup: "GitHub Pages",
  refresh_content: "İçerik Yenileme",
  mission_control_help: "Mission Control",
  brain_memory: "HIVE Brain Hafıza",
  general: "Genel Yönlendirme",
};

const EXAMPLE_QUESTIONS = [
  "Kuşadası gece hayatında yükselmek istiyorum",
  "Google Sites nasıl açılır?",
  "SERP tehditi var ne yapmalıyım?",
  "Bugün ne yapmalıyım?",
  "İlk içeriği nasıl yayınlarım?",
  "WordPress bağlantısı nasıl kurulur?",
  "GitHub Pages token nasıl ayarlanır?",
  "Brain timeline boş, ne yapmalıyım?",
];

function apiError(e, endpoint = `${API_PREFIX}/ask`) {
  return formatHiveApiError(e, endpoint);
}

export default function HiveMentor({ onNavigate }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const go = (id, meshTab) => {
    if (meshTab) {
      sessionStorage.setItem("hive_mesh_tab", meshTab);
      window.dispatchEvent(new Event("hive-mesh-tab"));
    }
    onNavigate?.(id);
  };

  const loadContext = useCallback(async () => {
    try {
      const res = await API.get(`${API_PREFIX}/context`);
      setContext(res.data);
    } catch {
      setContext(null);
    }
  }, []);

  useEffect(() => { loadContext(); }, [loadContext]);

  const ask = async (q) => {
    const text = (q ?? question).trim();
    if (!text) return;
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`${API_PREFIX}/ask`, { question: text });
      setAnswer(res.data);
      setQuestion(text);
      await loadContext();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="hive-module hive-learn-page">
      <section className="hive-os-hero hive-learn-hero">
        <div className="hive-os-hero-glow" aria-hidden />
        <div className="hive-os-hero-top">
          <div>
            <span className="hive-os-hero-kicker">HIVE SEO OS · Learn</span>
            <h1 className="hive-os-hero-title">🧭 HIVE Mentor</h1>
            <p className="hive-os-hero-sub">
              Kural tabanlı modül yönlendirme — {context?.available_intents?.length ?? 0} intent ·
              {" "}{context?.questions_asked ?? 0} soru yanıtlandı
            </p>
          </div>
          {context && (
            <div className="hive-learn-progress-badge">
              <span>Sorular</span>
              <strong>{context.questions_asked ?? 0}</strong>
            </div>
          )}
        </div>
        <HiveCommandBar
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Hedefinizi yazın — örn. Google Sites nasıl açılır?"
          onSubmit={ask}
        />
      </section>

      <HiveShell title="" subtitle="" actions={<HiveBtn onClick={() => ask()} disabled={loading}>{loading ? "Düşünüyor…" : "Sor"}</HiveBtn>}>
        {error && <HiveApiErrorCard errorInfo={error} />}

        <HiveSection title="Örnek sorular">
          <div className="hive-mentor-examples">
            {EXAMPLE_QUESTIONS.map((ex) => (
              <button key={ex} type="button" className="hive-mentor-example-btn" onClick={() => ask(ex)}>{ex}</button>
            ))}
          </div>
        </HiveSection>

        {context?.intent_catalog?.length > 0 && (
          <HiveSection title="Intent kataloğu" description="Mentor'un anlayabildiği konu alanları">
            <div className="hive-intent-catalog">
              {context.intent_catalog.map((item) => (
                <div key={item.intent} className="hive-intent-card">
                  <strong>{INTENT_LABELS[item.intent] || item.intent.replace(/_/g, " ")}</strong>
                  <p>{(item.sample_keywords || []).join(", ")}</p>
                  <HiveBadge tone="neutral">{item.step_count} modül adımı</HiveBadge>
                </div>
              ))}
            </div>
          </HiveSection>
        )}

        {!answer ? (
          <HiveEmptyState
            icon="🧭"
            title="Mentor hazır"
            description="SEO hedefinizi yazın — hangi modüle, hangi sırayla gideceğinizi ve nedenini açıklayacağım."
            actionLabel="Academy'ye Git"
            onAction={() => go("hive_academy")}
          />
        ) : (
          <HivePanel title="Mentor Yanıtı" className="hive-mentor-answer">
            <p className="hive-mentor-question">Soru: {answer.question}</p>
            <p className="hive-mentor-summary">{answer.summary}</p>
            <HiveBadge tone={PRIORITY_TONE.HIGH}>{INTENT_LABELS[answer.intent] || answer.intent?.replace(/_/g, " ")}</HiveBadge>

            {answer.tips?.length > 0 && (
              <div className="hive-mentor-tips">
                <h4>💡 İpuçları</h4>
                <ul>
                  {answer.tips.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            )}

            <h4 className="hive-mentor-steps-title">Önerilen modül sırası</h4>
            <ol className="hive-mentor-steps">
              {(answer.steps || []).map((s) => (
                <li key={s.order}>
                  <button
                    type="button"
                    className="hive-mentor-step-card"
                    onClick={() => go(s.module_id, s.mesh_tab)}
                  >
                    <span className="hive-os-mission-order">{s.order}</span>
                    <div>
                      <strong>{s.title}</strong>
                      <p>{s.reason}</p>
                    </div>
                    <HiveBtn size="sm">Modüle Git</HiveBtn>
                  </button>
                </li>
              ))}
            </ol>

            <div className="hive-mentor-actions">
              {answer.workflow_id && (
                <HiveBtn variant="secondary" onClick={() => go("hive_academy")}>
                  📋 Workflow: {answer.workflow_id.replace(/_/g, " ")} → Academy
                </HiveBtn>
              )}
              {answer.academy_guide && (
                <HiveBtn variant="secondary" onClick={() => go("hive_academy")}>
                  📖 Academy rehberi: {answer.academy_guide.replace("guide_", "")}
                </HiveBtn>
              )}
            </div>
          </HivePanel>
        )}

        {context?.recent_questions?.length > 0 && (
          <HiveSection title="Son sorular">
            <ul className="hive-mentor-recent">
              {context.recent_questions.slice(0, 5).map((q) => (
                <li key={q.answer_id || q.at}>
                  <button type="button" className="hive-link-btn" onClick={() => ask(q.question)}>{q.question}</button>
                  <span className="hive-mentor-recent-intent">{q.intent}</span>
                </li>
              ))}
            </ul>
          </HiveSection>
        )}
      </HiveShell>
    </div>
  );
}
