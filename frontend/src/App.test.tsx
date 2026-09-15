import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { BriefingResponse } from "./lib/api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Morning Briefing", () => {
  it("renders persisted report and explicit ledger-gap evidence", async () => {
    vi.stubGlobal("fetch", vi.fn(fetchStub));

    render(<App />);

    expect(screen.getByLabelText("正在载入今日简报")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "报告中的职位机会" }),
    ).toBeInTheDocument();
    expect(screen.getByText("合成单位")).toBeInTheDocument();
    expect(
      screen.getByText("2026-09-07—2026-09-08 无运行记录"),
    ).toBeInTheDocument();
    expect(screen.getByText("投递尚未启用")).toBeInTheDocument();
    expect(screen.getByText("系统正常")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /查看 合成单位 合成岗位 的原始来源/ }),
    ).toHaveAttribute("href", "https://example.invalid/jobs/6");
  });

  it("uses a safe error state without rendering backend error text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        const path = String(input);
        if (path.includes("/dashboard/")) {
          return Promise.resolve(
            Response.json(
              {
                detail: {
                  message: "postgresql://secret@database should not appear",
                },
              },
              { status: 503 },
            ),
          );
        }
        return Promise.resolve(
          Response.json({ status: path.endsWith("ready") ? "ready" : "alive" }),
        );
      }),
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "暂时无法读取简报" }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/secret/)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "重新读取" }),
    ).toBeInTheDocument();
  });

  it("renders an explicit empty state before the first persisted report", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        const path = String(input);
        if (path.endsWith("/health/live"))
          return Promise.resolve(
            Response.json({ status: "alive", checks: null }),
          );
        if (path.endsWith("/health/ready")) {
          return Promise.resolve(
            Response.json({
              status: "ready",
              checks: { database: "available" },
            }),
          );
        }
        return Promise.resolve(
          Response.json({
            ...fixture,
            scheduler: {
              job_id: "jobagent.daily-pipeline.v1",
              present: false,
              next_run_at: null,
            },
            recent_runs: [],
            missing_record_dates: [],
            latest_report: null,
            delivery: {
              state: "no_report",
              channel: null,
              updated_at: null,
              error_code: null,
            },
          } satisfies BriefingResponse),
        );
      }),
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "尚无持久化日报" }),
    ).toBeInTheDocument();
    expect(screen.getByText("暂无可投递日报")).toBeInTheDocument();
    expect(screen.getByText("未找到固定调度作业记录。")).toBeInTheDocument();
  });
});

async function fetchStub(input: string | URL | Request) {
  const path = String(input);
  if (path.endsWith("/health/live"))
    return Response.json({ status: "alive", checks: null });
  if (path.endsWith("/health/ready")) {
    return Response.json({
      status: "ready",
      checks: { database: "available" },
    });
  }
  return Response.json(fixture);
}

const fixture: BriefingResponse = {
  generated_at: "2026-09-14T00:30:00Z",
  timezone: "Asia/Shanghai",
  scheduler: {
    job_id: "jobagent.daily-pipeline.v1",
    present: true,
    next_run_at: "2026-09-15T00:00:00Z",
  },
  recent_runs: [
    {
      id: 1,
      scheduled_for: "2026-09-06T00:00:00Z",
      report_date: "2026-09-06",
      trigger: "makeup",
      status: "succeeded",
      current_stage: null,
      started_at: "2026-09-06T00:00:00Z",
      finished_at: "2026-09-06T00:05:00Z",
      stages: [
        {
          stage: "collection",
          attempt: 1,
          status: "succeeded",
          started_at: "2026-09-06T00:00:00Z",
          finished_at: "2026-09-06T00:01:00Z",
        },
      ],
    },
  ],
  missing_record_dates: ["2026-09-07", "2026-09-08"],
  latest_report: {
    snapshot_id: 2,
    report_date: "2026-09-06",
    report_version: "jai-024-v1",
    created_at: "2026-09-06T00:04:00Z",
    item_count: 1,
    group_counts: { priority_applications: 1 },
    items: [
      {
        group: "priority_applications",
        position_id: 6,
        match_result_id: 6,
        organization: "合成单位",
        title: "合成岗位",
        region: "北京",
        deadline: null,
        score: 88,
        reason: "与合成偏好匹配。",
        risks: [],
        source_url: "https://example.invalid/jobs/6",
      },
    ],
  },
  delivery: {
    state: "unavailable_schema",
    channel: null,
    updated_at: null,
    error_code: null,
  },
};
