/**
 * Ağır sayfalar — route-based code splitting (Performance Sprint).
 * Mission Control ve shell eager kalır.
 */
import { lazy } from "react";

export const LazyTalonHub = lazy(() => import("./pages/TalonHub"));
export const LazyAstroFactory = lazy(() => import("./pages/AstroFactory"));
export const LazyWordPressManager = lazy(() => import("./pages/WordPressManager"));
export const LazyStoryForge = lazy(() => import("./pages/StoryForge"));
export const LazyCrawlGapEngine = lazy(() => import("./pages/CrawlGapEngine"));
export const LazyAuthorityMeshEngine = lazy(() => import("./pages/AuthorityMeshEngine"));
export const LazyEntityGeoGraph = lazy(() => import("./pages/EntityGeoGraph"));
export const LazyPlaceSEOPipeline = lazy(() => import("./pages/PlaceSEOPipeline"));
export const LazyQuestionIntelligenceEngine = lazy(() => import("./pages/QuestionIntelligenceEngine"));
export const LazyExecutiveAI = lazy(() => import("./pages/ExecutiveAI"));

export function PageLoadFallback() {
  return (
    <div className="hive-page-loading" style={{ padding: "2rem", opacity: 0.7 }}>
      Yükleniyor…
    </div>
  );
}
