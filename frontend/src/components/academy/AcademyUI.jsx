import React from "react";

export function AcademySkeleton({ lines = 3 }) {
  return (
    <div className="ha-skeleton-wrap" aria-busy="true" aria-label="Yükleniyor">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`ha-skeleton ${i === 0 ? "ha-skeleton-lg" : ""}`} />
      ))}
    </div>
  );
}

export function AcademyEmpty({ title, hint, action }) {
  return (
    <div className="ha-empty">
      <p className="ha-empty-title">{title}</p>
      {hint && <p className="ha-muted">{hint}</p>}
      {action}
    </div>
  );
}

export function AcademyToast({ message, onClose }) {
  if (!message) return null;
  return (
    <div className="ha-toast" role="status">
      <span>{message}</span>
      <button type="button" className="ha-toast-close" onClick={onClose} aria-label="Kapat">×</button>
    </div>
  );
}
