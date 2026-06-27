import React, { useEffect, useState } from "react";
import API from "../../api";
import MarkdownBody from "./MarkdownBody";

const API_PREFIX = "/api/academy";

export default function AcademyChangelog({ onBack }) {
  const [markdown, setMarkdown] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await API.get(`${API_PREFIX}/changelog`);
        setMarkdown(res.data.markdown || "");
      } catch {
        setError("Changelog yüklenemedi.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="ha-changelog">
      <button type="button" className="ha-link-btn" onClick={onBack}>← Dashboard</button>
      <h2>Academy Changelog</h2>
      {loading && <div className="ha-skeleton ha-skeleton-lg" />}
      {error && <p className="ha-muted">{error}</p>}
      {!loading && !error && <MarkdownBody content={markdown} />}
    </div>
  );
}
