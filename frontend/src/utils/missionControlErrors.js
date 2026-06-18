const RESTART_CMD = "bash scripts/stop-hive.sh && bash scripts/start-hive.sh";

export { formatHiveApiError as formatMissionControlApiError } from "./hiveApiErrors";

export function missionControlErrorText(info) {
  if (!info) return "";
  if (typeof info === "string") return info;
  return info.title || "Bilinmeyen hata";
}
