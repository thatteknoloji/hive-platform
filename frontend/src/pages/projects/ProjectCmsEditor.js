import React, { useCallback, useEffect, useState } from "react";
import API from "../../api";
import {
  HivePanel,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveAlert,
  HiveTable,
} from "../../components/HiveModuleUI";

function apiError(e) {
  return e?.response?.data?.detail || e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

export default function ProjectCmsEditor({ projectId, project, onUpdated }) {
  const [pages, setPages] = useState(project?.pages || []);
  const [selectedPageId, setSelectedPageId] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setPages(project?.pages || []);
    if (project?.pages?.length && !selectedPageId) {
      setSelectedPageId(project.pages[0].id);
    }
  }, [project, selectedPageId]);

  const selectedPage = pages.find((p) => p.id === selectedPageId);

  const updateBlockField = (sectionId, blockId, key, value) => {
    setPages((prev) => prev.map((page) => {
      if (page.id !== selectedPageId) return page;
      return {
        ...page,
        sections: (page.sections || []).map((sec) => {
          if (sec.id !== sectionId) return sec;
          return {
            ...sec,
            blocks: (sec.blocks || []).map((blk) => {
              if (blk.id !== blockId) return blk;
              const fieldKey = blk.content ? "content" : "props";
              return { ...blk, [fieldKey]: { ...(blk[fieldKey] || {}), [key]: value } };
            }),
          };
        }),
      };
    }));
  };

  const savePage = useCallback(async () => {
    if (!selectedPage) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await API.patch(`/api/v3/projects/${projectId}/pages/${selectedPage.id}`, {
        title: selectedPage.title,
        slug: selectedPage.slug,
        status: selectedPage.status,
        sections: selectedPage.sections,
        seo: selectedPage.seo,
      });
      setMessage("Sayfa kaydedildi.");
      if (onUpdated) onUpdated();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setSaving(false);
    }
  }, [projectId, selectedPage, onUpdated]);

  if (!pages.length) {
    return (
      <HivePanel title="CMS Editor">
        <p>Site skeleton yok. Retro-seed veya yeni proje oluşturun.</p>
      </HivePanel>
    );
  }

  return (
    <HivePanel title="CMS Editor">
      {error && <HiveAlert type="error">{error}</HiveAlert>}
      {message && <HiveAlert type="ok">{message}</HiveAlert>}

      <div className="hive-cms-layout">
        <div className="hive-cms-pages">
          <div className="hive-brand-review-label">Sayfalar</div>
          {pages.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`hive-cms-page-btn ${p.id === selectedPageId ? "active" : ""}`}
              onClick={() => setSelectedPageId(p.id)}
            >
              <span>{p.title}</span>
              <code>{p.slug ? `/${p.slug}` : "/"}</code>
            </button>
          ))}
        </div>

        {selectedPage && (
          <div className="hive-cms-editor">
            <HiveField label="Başlık">
              <HiveInput
                value={selectedPage.title || ""}
                onChange={(e) => setPages((prev) => prev.map((p) => (p.id === selectedPageId ? { ...p, title: e.target.value } : p)))}
              />
            </HiveField>
            <HiveField label="Slug">
              <HiveInput
                value={selectedPage.slug || ""}
                onChange={(e) => setPages((prev) => prev.map((p) => (p.id === selectedPageId ? { ...p, slug: e.target.value } : p)))}
              />
            </HiveField>

            {(selectedPage.sections || []).map((sec) => (
              <div key={sec.id} className="hive-cms-section">
                <div className="hive-brand-review-label">Section: {sec.type}</div>
                {(sec.blocks || []).map((blk) => {
                  const fields = blk.content || blk.props || {};
                  return (
                  <div key={blk.id} className="hive-cms-block">
                    <strong>{blk.type}</strong>
                    {Object.entries(fields).map(([key, val]) => {
                      if (typeof val === "object") return null;
                      return (
                        <HiveField key={key} label={key}>
                          <HiveInput
                            value={String(val ?? "")}
                            onChange={(e) => updateBlockField(sec.id, blk.id, key, e.target.value)}
                          />
                        </HiveField>
                      );
                    })}
                  </div>
                  );
                })}
              </div>
            ))}

            <HiveBtn variant="primary" onClick={savePage} disabled={saving}>
              {saving ? "Kaydediliyor..." : "Sayfayı Kaydet"}
            </HiveBtn>
          </div>
        )}
      </div>

      <HiveTable
        columns={["Başlık", "Tip", "Durum", "Slug", "Blok"]}
        rows={pages.map((p) => [
          p.title,
          p.type,
          p.status,
          p.slug ? `/${p.slug}` : "/",
          (p.sections || []).reduce((n, s) => n + (s.blocks || []).length, 0),
        ])}
      />
    </HivePanel>
  );
}
