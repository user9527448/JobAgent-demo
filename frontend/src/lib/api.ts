export type DeliveryState =
  | "unavailable_schema"
  | "no_report"
  | "not_created"
  | "pending"
  | "sending"
  | "succeeded"
  | "failed"
  | "unknown";

export interface ScheduleEvidence {
  job_id: string;
  present: boolean;
  next_run_at: string | null;
}

export interface StageEvidence {
  stage: string;
  attempt: number;
  status: string;
  started_at: string;
  finished_at: string | null;
}

export interface PipelineRunEvidence {
  id: number;
  scheduled_for: string;
  report_date: string;
  trigger: string;
  status: string;
  current_stage: string | null;
  started_at: string | null;
  finished_at: string | null;
  stages: StageEvidence[];
}

export interface ReportItemEvidence {
  group: string;
  position_id: number | null;
  match_result_id: number | null;
  organization: string | null;
  title: string | null;
  region: string | null;
  deadline: string | null;
  score: number | null;
  reason: string | null;
  risks: string[];
  source_url: string | null;
}

export interface ReportEvidence {
  snapshot_id: number;
  report_date: string;
  report_version: string;
  created_at: string;
  item_count: number;
  group_counts: Record<string, number>;
  items: ReportItemEvidence[];
}

export interface DeliveryEvidence {
  state: DeliveryState;
  channel: string | null;
  updated_at: string | null;
  error_code: string | null;
}

export interface BriefingResponse {
  generated_at: string;
  timezone: string;
  scheduler: ScheduleEvidence;
  recent_runs: PipelineRunEvidence[];
  missing_record_dates: string[];
  latest_report: ReportEvidence | null;
  delivery: DeliveryEvidence;
}

export type HealthStatus = "alive" | "ready" | "not_ready" | "unreachable";

export interface HealthSnapshot {
  live: HealthStatus;
  ready: HealthStatus;
}

export class DashboardRequestError extends Error {
  constructor() {
    super("暂时无法读取简报证据，请稍后重试。");
    this.name = "DashboardRequestError";
  }
}

export async function getBriefing(
  signal?: AbortSignal,
): Promise<BriefingResponse> {
  const response = await fetch("/dashboard/briefing", {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) throw new DashboardRequestError();
  return (await response.json()) as BriefingResponse;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthSnapshot> {
  const [live, ready] = await Promise.all([
    getHealthStatus("/health/live", signal),
    getHealthStatus("/health/ready", signal),
  ]);
  return { live, ready };
}

async function getHealthStatus(
  path: string,
  signal?: AbortSignal,
): Promise<HealthStatus> {
  try {
    const response = await fetch(path, {
      headers: { Accept: "application/json" },
      signal,
    });
    const body = (await response.json()) as { status?: HealthStatus };
    return body.status ?? "unreachable";
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    return "unreachable";
  }
}

export function safeExternalUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:"
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}
