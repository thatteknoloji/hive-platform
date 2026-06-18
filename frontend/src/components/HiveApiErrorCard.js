import React from "react";
import { HiveAlert } from "./HiveModuleUI";

export default function HiveApiErrorCard({ errorInfo }) {
  if (!errorInfo) return null;
  if (typeof errorInfo === "string") {
    return <HiveAlert type="error" pulse>{errorInfo}</HiveAlert>;
  }
  return (
    <div className="hive-os-api-error-card" role="alert">
      <div className="hive-os-api-error-title">{errorInfo.title}</div>
      {errorInfo.description && (
        <p className="hive-os-api-error-desc">{errorInfo.description}</p>
      )}
      <dl className="hive-os-api-error-meta">
        <div>
          <dt>Endpoint</dt>
          <dd><code>{errorInfo.endpoint}</code></dd>
        </div>
        {errorInfo.statusCode != null && (
          <div>
            <dt>HTTP status</dt>
            <dd>{errorInfo.statusCode}</dd>
          </div>
        )}
        <div>
          <dt>Yapılacak aksiyon</dt>
          <dd>{errorInfo.action}</dd>
        </div>
      </dl>
    </div>
  );
}
