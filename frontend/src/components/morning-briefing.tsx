import {
  AlertTriangle,
  ArrowUpRight,
  CalendarClock,
  Check,
  CircleDashed,
  ClipboardCheck,
  Clock3,
  DatabaseZap,
  FileCheck2,
  Inbox,
  MapPin,
  RefreshCw,
  Send,
  ShieldAlert,
} from "lucide-react";

import {
  safeExternalUrl,
  type BriefingResponse,
  type DeliveryEvidence,
  type PipelineRunEvidence,
  type ReportEvidence,
  type ReportItemEvidence,
  type StageEvidence,
} from "../lib/api";
import { cn } from "../lib/utils";
import { Badge } from "./ui/badge";
import { Skeleton } from "./ui/skeleton";

const groupLabels: Record<string, string> = {
  priority_applications: "优先申请",
  closing_soon: "即将截止",
  added_today: "今日新增",
  needs_confirmation: "需要确认",
};

const stageLabels: Record<string, string> = {
  collection: "采集",
  extraction: "提取与校验",
  matching: "匹配",
  report: "报告",
  delivery: "投递",
};

interface MorningBriefingProps {
  data: BriefingResponse | null;
  error: string | null;
  loading: boolean;
  onRetry: () => void;
}

export function MorningBriefing({
  data,
  error,
  loading,
  onRetry,
}: MorningBriefingProps) {
  return (
    <div className="grid min-w-0 xl:grid-cols-[minmax(0,1fr)_356px]">
      <main className="min-w-0 px-4 py-8 sm:px-6 lg:px-8 xl:px-8 xl:py-9">
        <header className="border-b border-border pb-6">
          <h1 className="text-[32px] font-extrabold leading-tight tracking-[-0.035em] sm:text-[40px]">
            今日简报
          </h1>
          <p className="mt-2 max-w-2xl text-[15px] leading-7 text-muted-foreground">
            基于已持久化的招聘报告与运行台账，查看机会、流程和投递证据。
          </p>
        </header>

        {loading ? (
          <BriefingSkeleton />
        ) : error ? (
          <ErrorState message={error} onRetry={onRetry} />
        ) : data ? (
          <ReportBriefing data={data} />
        ) : (
          <ErrorState message="简报数据尚未载入。" onRetry={onRetry} />
        )}
      </main>

      <aside
        aria-label="运行证据"
        className="border-t border-border bg-muted/18 px-4 py-8 sm:px-6 lg:px-8 xl:min-h-[calc(100vh-68px)] xl:border-l xl:border-t-0 xl:px-6 xl:py-8"
      >
        {loading ? (
          <EvidenceSkeleton />
        ) : data ? (
          <EvidenceRail data={data} />
        ) : (
          <EvidenceUnavailable />
        )}
      </aside>
    </div>
  );
}

function ReportBriefing({ data }: { data: BriefingResponse }) {
  const report = data.latest_report;
  if (!report) return <EmptyReport />;

  return (
    <div>
      <section aria-labelledby="report-heading" className="pt-7">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2
            id="report-heading"
            className="text-[23px] font-bold tracking-[-0.02em]"
          >
            最近持久化日报 · {formatDateOnly(report.report_date)}
          </h2>
          <div className="text-right text-xs leading-5 text-muted-foreground">
            <p>快照 #{report.snapshot_id}</p>
            <p>{formatDateTime(report.created_at, data.timezone)} 生成</p>
          </div>
        </div>

        <div className="mt-5 min-h-[168px] rounded-[var(--radius)] border border-primary/10 bg-primary/[0.055] px-5 py-5 sm:px-6 sm:py-6">
          <div className="flex items-start gap-4">
            <span className="mt-0.5 grid size-10 shrink-0 place-items-center rounded-full bg-primary/10 text-primary">
              <FileCheck2 aria-hidden="true" className="size-5" />
            </span>
            <div>
              <h3 className="text-base font-bold text-primary">执行摘要</h3>
              <p className="mt-2 text-sm leading-7 text-secondary-foreground">
                本期日报固化了 <strong>{report.item_count}</strong>{" "}
                条分组记录，其中
                <strong>
                  {" "}
                  {countGroup(report, "priority_applications")}
                </strong>{" "}
                条属于优先申请，
                <strong> {countGroup(report, "closing_soon")}</strong>{" "}
                条临近截止。
                以下内容严格来自不可变日报快照，空缺字段保持为“未提供”。
              </p>
            </div>
          </div>
        </div>

        <ReportMetrics report={report} runCount={data.recent_runs.length} />
      </section>

      <section
        aria-labelledby="recommendations-heading"
        className="border-t border-border pt-7"
      >
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2
              id="recommendations-heading"
              className="text-xl font-bold tracking-[-0.015em]"
            >
              报告中的职位机会
            </h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              保留日报分组与条目顺序，展示当前快照中的可追溯信息。
            </p>
          </div>
          <a
            className="inline-flex items-center gap-1 rounded-sm text-sm font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            href={`/reports/daily/${report.snapshot_id}/html`}
            rel="noopener"
            target="_blank"
          >
            查看完整日报
            <ArrowUpRight aria-hidden="true" className="size-4" />
          </a>
        </div>

        {report.items.length ? (
          <ol className="mt-4 divide-y divide-border">
            {report.items.map((item, index) => (
              <RecommendationItem
                item={item}
                key={`${item.group}-${item.match_result_id ?? index}`}
                rank={index + 1}
              />
            ))}
          </ol>
        ) : (
          <div className="mt-5 rounded-lg border border-dashed border-border px-5 py-8 text-center">
            <Inbox
              aria-hidden="true"
              className="mx-auto size-7 text-muted-foreground"
            />
            <p className="mt-3 font-semibold">这份日报没有职位条目</p>
            <p className="mt-1 text-sm text-muted-foreground">
              快照存在，但四个报告分组当前均为空。
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function ReportMetrics({
  report,
  runCount,
}: {
  report: ReportEvidence;
  runCount: number;
}) {
  const metrics = [
    { value: report.item_count, label: "报告分组记录" },
    { value: countGroup(report, "priority_applications"), label: "优先申请" },
    { value: countGroup(report, "needs_confirmation"), label: "需要确认" },
    { value: runCount, label: "近期运行台账" },
  ];
  return (
    <dl className="grid grid-cols-2 gap-y-6 py-7 sm:grid-cols-4">
      {metrics.map((metric, index) => (
        <div
          className={cn(
            "pr-5",
            index > 0 && "sm:border-l sm:border-border sm:pl-6",
          )}
          key={metric.label}
        >
          <dd className="text-[28px] font-extrabold tabular-nums tracking-[-0.03em]">
            {metric.value}
          </dd>
          <dt className="mt-0.5 text-sm text-muted-foreground">
            {metric.label}
          </dt>
        </div>
      ))}
    </dl>
  );
}

function RecommendationItem({
  item,
  rank,
}: {
  item: ReportItemEvidence;
  rank: number;
}) {
  const sourceUrl = safeExternalUrl(item.source_url);
  return (
    <li className="grid gap-3 py-5 sm:grid-cols-[48px_140px_minmax(0,1fr)_58px] sm:items-start">
      <span className="grid size-9 place-items-center rounded-lg bg-secondary text-sm font-bold tabular-nums text-secondary-foreground">
        {rank}
      </span>
      <div className="min-w-0">
        <Badge variant="evidence">
          {groupLabels[item.group] ?? item.group}
        </Badge>
        <p className="mt-2 truncate text-sm font-semibold">
          {item.organization || "单位未提供"}
        </p>
      </div>
      <div className="min-w-0">
        <h3 className="font-bold leading-6">
          {item.title || "职位名称未提供"}
        </h3>
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <MapPin aria-hidden="true" className="size-3.5" />
            {item.region || "地区未提供"}
          </span>
          <span>截止：{formatDeadline(item.deadline)}</span>
          {sourceUrl ? (
            <a
              aria-label={`查看 ${item.organization || "该单位"} ${item.title || "该职位"} 的原始来源`}
              className="inline-flex items-center gap-1 font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              href={sourceUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              原始来源
              <ArrowUpRight aria-hidden="true" className="size-3" />
            </a>
          ) : null}
        </div>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {item.reason || "未记录推荐理由。"}
        </p>
        {item.risks.length ? (
          <p className="mt-1.5 text-xs leading-5 text-attention-foreground">
            待确认：{item.risks.join("；")}
          </p>
        ) : null}
      </div>
      <div className="sm:text-right">
        <strong className="text-2xl font-extrabold tabular-nums text-evidence">
          {item.score ?? "—"}
        </strong>
        <p className="text-xs text-muted-foreground">匹配分</p>
      </div>
    </li>
  );
}

function EvidenceRail({ data }: { data: BriefingResponse }) {
  return (
    <div className="space-y-6">
      <SchedulePanel data={data} />
      <LedgerGapNotice dates={data.missing_record_dates} />
      <PipelinePanel
        run={data.recent_runs[0] ?? null}
        timezone={data.timezone}
      />
      <DeliveryPanel delivery={data.delivery} timezone={data.timezone} />
    </div>
  );
}

function SchedulePanel({ data }: { data: BriefingResponse }) {
  const schedule = data.scheduler;
  return (
    <section
      aria-labelledby="schedule-heading"
      className="rounded-lg border border-border bg-card p-5"
    >
      <div className="flex items-center gap-3 text-evidence">
        <CalendarClock aria-hidden="true" className="size-5" />
        <h2 id="schedule-heading" className="font-bold text-foreground">
          下一次计划运行
        </h2>
      </div>
      {schedule.present && schedule.next_run_at ? (
        <>
          <p className="mt-4 text-xl font-extrabold tabular-nums tracking-[-0.025em]">
            {formatDateTime(schedule.next_run_at, data.timezone)}
          </p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            来自固定作业 <code className="text-xs">{schedule.job_id}</code>{" "}
            的持久化证据。
          </p>
        </>
      ) : (
        <div className="mt-4 flex gap-3 text-sm leading-6 text-muted-foreground">
          <CircleDashed aria-hidden="true" className="mt-1 size-4 shrink-0" />
          <p>
            {schedule.present
              ? "作业存在，但未记录下一次运行时间。"
              : "未找到固定调度作业记录。"}
          </p>
        </div>
      )}
    </section>
  );
}

function LedgerGapNotice({ dates }: { dates: string[] }) {
  if (!dates.length) {
    return (
      <section
        className="rounded-lg border border-success/20 bg-success/[0.055] p-5"
        aria-label="运行记录完整性"
      >
        <div className="flex gap-3">
          <Check
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0 text-success"
          />
          <div>
            <h2 className="font-bold">近期未发现台账日期缺口</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              仅依据接口返回的有限日期窗口。
            </p>
          </div>
        </div>
      </section>
    );
  }
  return (
    <section
      className="rounded-lg border border-border bg-secondary/70 p-5"
      aria-labelledby="gap-heading"
    >
      <div className="flex gap-3">
        <Clock3
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-muted-foreground"
        />
        <div>
          <h2 id="gap-heading" className="font-bold">
            {formatDateRange(dates)} 无运行记录
          </h2>
          <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
            这些日期没有流水线台账行；这不代表成功、失败、取消或 misfire。
          </p>
        </div>
      </div>
    </section>
  );
}

function PipelinePanel({
  run,
  timezone,
}: {
  run: PipelineRunEvidence | null;
  timezone: string;
}) {
  return (
    <section
      aria-labelledby="pipeline-heading"
      className="border-t border-border pt-6"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 id="pipeline-heading" className="text-lg font-bold">
            最近处理流程
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {run
              ? `${formatDateOnly(run.report_date)} · #${run.id}`
              : "没有可展示的运行台账"}
          </p>
        </div>
        {run ? <StatusBadge status={run.status} /> : null}
      </div>
      {run ? (
        <ol className="mt-5 space-y-0">
          {run.stages.map((stage, index) => (
            <StageRow
              isLast={index === run.stages.length - 1}
              key={`${stage.stage}-${stage.attempt}`}
              stage={stage}
              timezone={timezone}
            />
          ))}
        </ol>
      ) : (
        <p className="mt-4 rounded-lg border border-dashed border-border p-4 text-sm leading-6 text-muted-foreground">
          数据库尚未提供近期 pipeline_runs 证据。
        </p>
      )}
    </section>
  );
}

function StageRow({
  stage,
  timezone,
  isLast,
}: {
  stage: StageEvidence;
  timezone: string;
  isLast: boolean;
}) {
  const completed = stage.status === "succeeded";
  const Icon =
    stage.stage === "delivery"
      ? Send
      : stage.stage === "report"
        ? FileCheck2
        : ClipboardCheck;
  return (
    <li className="grid grid-cols-[40px_minmax(0,1fr)] gap-3">
      <div className="flex flex-col items-center">
        <span
          className={cn(
            "grid size-9 place-items-center rounded-full bg-muted text-muted-foreground",
            completed && "bg-evidence/10 text-evidence",
          )}
        >
          <Icon aria-hidden="true" className="size-4" />
        </span>
        {!isLast ? (
          <span
            aria-hidden="true"
            className="my-1 min-h-4 w-px flex-1 bg-border"
          />
        ) : null}
      </div>
      <div className={cn("pb-5", isLast && "pb-0")}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-semibold">
              {stageLabels[stage.stage] ?? stage.stage}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              第 {stage.attempt} 次尝试 ·{" "}
              {formatDateTime(stage.started_at, timezone)}
            </p>
          </div>
          <StatusBadge status={stage.status} />
        </div>
      </div>
    </li>
  );
}

function DeliveryPanel({
  delivery,
  timezone,
}: {
  delivery: DeliveryEvidence;
  timezone: string;
}) {
  const content = deliveryCopy(delivery);
  return (
    <section
      aria-labelledby="delivery-heading"
      className={cn(
        "rounded-lg border p-5",
        delivery.state === "succeeded"
          ? "border-success/20 bg-success/[0.055]"
          : "border-attention/25 bg-attention/[0.08]",
      )}
    >
      <div className="flex gap-3">
        {delivery.state === "succeeded" ? (
          <Check
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0 text-success"
          />
        ) : (
          <ShieldAlert
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0 text-attention-foreground"
          />
        )}
        <div>
          <h2 id="delivery-heading" className="font-bold">
            {content.title}
          </h2>
          <p className="mt-1 text-sm font-medium text-muted-foreground">
            {content.status}
          </p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {content.description}
          </p>
          {delivery.updated_at ? (
            <p className="mt-2 text-xs tabular-nums text-muted-foreground">
              更新于 {formatDateTime(delivery.updated_at, timezone)}
            </p>
          ) : null}
          {delivery.error_code ? (
            <p className="mt-2 text-xs text-muted-foreground">
              安全错误码：{delivery.error_code}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "succeeded"
      ? "success"
      : status === "failed" || status === "interrupted"
        ? "destructive"
        : status === "partial" || status === "unknown"
          ? "attention"
          : "neutral";
  const labels: Record<string, string> = {
    pending: "等待中",
    running: "运行中",
    sending: "发送中",
    succeeded: "成功",
    partial: "部分完成",
    failed: "失败",
    cancelled: "已取消",
    interrupted: "已中断",
    unknown: "状态未知",
  };
  return <Badge variant={variant}>{labels[status] ?? status}</Badge>;
}

function EmptyReport() {
  return (
    <section
      className="py-16 text-center"
      aria-labelledby="empty-report-heading"
    >
      <span className="mx-auto grid size-12 place-items-center rounded-full bg-muted text-muted-foreground">
        <DatabaseZap aria-hidden="true" className="size-6" />
      </span>
      <h2 id="empty-report-heading" className="mt-4 text-xl font-bold">
        尚无持久化日报
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
        页面已连接证据接口，但数据库目前没有可展示的日报快照。这里不会生成临时报告或推测业务结果。
      </p>
    </section>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <section
      className="py-16 text-center"
      aria-labelledby="briefing-error-heading"
    >
      <span className="mx-auto grid size-12 place-items-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle aria-hidden="true" className="size-6" />
      </span>
      <h2 id="briefing-error-heading" className="mt-4 text-xl font-bold">
        暂时无法读取简报
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
        {message}
      </p>
      <button
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        onClick={onRetry}
        type="button"
      >
        <RefreshCw aria-hidden="true" className="size-4" />
        重新读取
      </button>
    </section>
  );
}

function BriefingSkeleton() {
  return (
    <div
      aria-label="正在载入今日简报"
      aria-live="polite"
      className="space-y-7 pt-8"
    >
      <div className="space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-36 w-full" />
      </div>
      <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton className="h-16" key={index} />
        ))}
      </div>
      <Skeleton className="h-7 w-48" />
      {Array.from({ length: 3 }).map((_, index) => (
        <Skeleton className="h-24 w-full" key={index} />
      ))}
      <span className="sr-only">正在载入</span>
    </div>
  );
}

function EvidenceSkeleton() {
  return (
    <div aria-hidden="true" className="space-y-5">
      <Skeleton className="h-40" />
      <Skeleton className="h-32" />
      <Skeleton className="h-72" />
      <Skeleton className="h-40" />
    </div>
  );
}

function EvidenceUnavailable() {
  return (
    <div className="rounded-lg border border-dashed border-border p-5 text-sm leading-6 text-muted-foreground">
      <CircleDashed aria-hidden="true" className="mb-3 size-5" />
      运行证据将在简报接口恢复后显示；当前不会根据前端时间推测调度或投递结果。
    </div>
  );
}

function deliveryCopy(delivery: DeliveryEvidence) {
  const copies: Record<
    DeliveryEvidence["state"],
    { title: string; status: string; description: string }
  > = {
    unavailable_schema: {
      title: "投递尚未启用",
      status: "等待迁移与配置",
      description: "当前数据库没有投递台账结构；这不是一次发送失败。",
    },
    no_report: {
      title: "暂无可投递日报",
      status: "没有报告快照",
      description: "日报快照创建后，投递台账才可能产生记录。",
    },
    not_created: {
      title: "尚无投递记录",
      status: "未创建",
      description: "当前报告与所选通道尚未形成投递台账。",
    },
    pending: {
      title: "微信投递",
      status: "等待发送",
      description: "台账已创建，正在等待有界发送流程。",
    },
    sending: {
      title: "微信投递",
      status: "发送处理中",
      description: "发送流程已开始，请以最终持久化状态为准。",
    },
    succeeded: {
      title: "微信投递",
      status: "已成功发送",
      description: "同一日报与通道的成功记录将阻止重复发送。",
    },
    failed: {
      title: "微信投递",
      status: "发送失败",
      description: "已保留安全错误码；页面不会显示原始响应或密钥。",
    },
    unknown: {
      title: "微信投递",
      status: "结果未知",
      description: "远端结果未能确认，不应直接重复提交。",
    },
  };
  return copies[delivery.state];
}

function countGroup(report: ReportEvidence, group: string) {
  return report.group_counts[group] ?? 0;
}

function formatDateOnly(value: string) {
  const [year, month, day] = value.split("-");
  return year && month && day ? `${year}-${month}-${day}` : value;
}

function formatDateTime(value: string, timezone: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: timezone,
  }).format(new Date(value));
}

function formatDeadline(value: string | null) {
  if (!value) return "未提供";
  const instant = new Date(value);
  if (Number.isNaN(instant.valueOf())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(instant);
}

function formatDateRange(values: string[]) {
  if (values.length === 1) return values[0];
  return `${values[0]}—${values.at(-1)}`;
}
