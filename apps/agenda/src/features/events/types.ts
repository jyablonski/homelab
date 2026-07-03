import type { AgendaEvent, AgendaFreshness } from "@/lib/schemas";

export type FreshnessTone = "success" | "warning" | "danger" | "neutral";

export function freshnessTone(status: AgendaFreshness["status"]): FreshnessTone {
  switch (status) {
    case "fresh":
      return "success";
    case "stale":
      return "warning";
    case "fetch_failed":
      return "danger";
    default:
      return "neutral";
  }
}

const sourceBadgeClasses: Record<string, string> = {
  nba: "bg-blue-500/15 text-blue-300",
  ufc: "bg-red-500/15 text-red-300",
  cs2: "bg-orange-500/15 text-orange-300",
  personal: "bg-emerald-500/15 text-emerald-300",
};

const defaultSourceBadgeClass = "bg-slate-500/15 text-slate-300";

export function sourceBadgeClass(source: string): string {
  return sourceBadgeClasses[source] ?? defaultSourceBadgeClass;
}

export function findFreshnessForSource(
  freshness: AgendaFreshness[],
  source: AgendaEvent["source"],
): AgendaFreshness | undefined {
  return freshness.find((entry) => entry.source === source);
}
