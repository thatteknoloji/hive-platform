import React from "react";
import { AcademySkeleton } from "../AcademyUI";
import AcademyHero from "./AcademyHero";
import AcademyStats from "./AcademyStats";
import ContinueLearning from "./ContinueLearning";
import RecentDocs from "./RecentDocs";
import RecommendedTopics from "./RecommendedTopics";
import LearningPath from "./LearningPath";
import RecentlyViewed from "./RecentlyViewed";
import QuickAccess from "./QuickAccess";

export default function AcademyDashboard({
  data,
  progress,
  index,
  onContinue,
  onOpenDoc,
  onNavigate,
  onViewAllDocs,
}) {
  if (!data) {
    return (
      <div className="academy-dashboard academy-dashboard--loading">
        <AcademyHero />
        <div className="academy-dashboard__skeleton">
          <AcademySkeleton lines={8} />
        </div>
      </div>
    );
  }

  const recommended = data.recommended_topics || data.recommended || [];

  return (
    <div className="academy-dashboard">
      <AcademyHero />

      <div className="academy-dashboard__content">
        <AcademyStats data={data} />

        <div className="academy-dashboard__row academy-dashboard__row--top">
          <ContinueLearning data={data} onContinue={onContinue} progress={progress} />
          <RecentDocs
            docs={data.recent_docs || []}
            onOpenDoc={onOpenDoc}
            onViewAll={onViewAllDocs}
          />
          <RecommendedTopics topics={recommended} onOpenDoc={onOpenDoc} />
        </div>

        <div className="academy-dashboard__row academy-dashboard__row--bottom">
          <LearningPath steps={data.learning_path_steps} horizontal />
          <RecentlyViewed
            items={data.recently_viewed}
            progress={progress}
            index={index}
            onOpenDoc={onOpenDoc}
          />
          <QuickAccess items={data.quick_access} onNavigate={onNavigate} />
        </div>
      </div>
    </div>
  );
}

export const STATUS_LABEL = { completed: "✓", in_progress: "◐", not_started: "○", active: "◐", pending: "○" };
