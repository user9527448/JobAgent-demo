# JOBAGENT Product UI Design Specification

> 简体中文：[JOBAGENT 产品界面设计规范](zh-CN/DESIGN.md)

## 1. Status and scope

This document is the version-controlled visual and interaction authority for JAI-050. It governs the
production frontend foundation and the first read-only **Morning Briefing** page. Later UI Issues may
extend it through paired English and Simplified Chinese updates; they must not silently replace its
tokens, evidence rules, or accessibility baseline.

The selected visual reference is [Morning Briefing option 1](assets/jai-050/morning-briefing-reference.png)
(`1484x1060`, SHA-256 `09D55CFD2B5550E6D4D199004F690992DA90703B73AC38828808F94295AF8DE4`).
It is a composition and hierarchy reference, not a source of business truth. Generated dates, counts,
companies, roles, and status copy must be replaced by API evidence or explicit empty states.

## 2. Product outcome and evidence boundary

The first page lets one local user answer three questions in under a minute:

1. What is the latest persisted daily report, and which opportunities deserve attention?
2. What does the ledger prove about the most recent pipeline and its stages?
3. When is the fixed daily job next scheduled, and what is the safe delivery state?

JAI-050 is read-only. It contains no run, makeup, retry, send, resend, source-toggle, preference-write,
or feedback-write action. Missing ledger rows are displayed as **no run record** and are never inferred
as success, failure, cancellation, or misfire. The page must distinguish API liveness, database
readiness, scheduler evidence, pipeline evidence, and delivery capability.

## 3. Design-source hierarchy

Use the following authority order when sources disagree:

1. Persisted backend evidence, API contracts, tests, and repository security rules.
2. This paired DESIGN specification and the selected reference's information hierarchy.
3. Official shadcn/ui component and theme contracts, then Tailwind CSS v4 theme-variable contracts.
4. External DESIGN.md examples as documentation-structure inspiration only.

The reference image must not cause fabricated metrics, private recruitment data, third-party brand
identity, external registry code, gradients, emoji icons, or unapproved interactions. Use Lucide icons
because D-038 explicitly approved them; use text labels with every non-decorative icon.

## 4. Application architecture

- Root: `frontend/`, managed by pnpm with a committed lockfile.
- Runtime: React, TypeScript, and Vite; strict type checking.
- Styling: Tailwind CSS v4 and semantic CSS variables.
- Components: repository-owned shadcn/ui source components using Radix primitives.
- Icons: Lucide React, stroked consistently at 18–20 px.
- Development: Vite proxies the narrow FastAPI prefixes used by the page.
- Production: a deterministic frontend build is copied into the Python image and served at `/app/`
  from the existing FastAPI origin. Registered client routes fall back to the same `index.html`.
- Data access: one page-level query boundary aggregates read-only dashboard evidence; existing health
  endpoints remain separate so the shell can report database failure safely.

No separate frontend deployment, authentication layer, server-side rendering framework, design SaaS
runtime, analytics SDK, or client-side secret is introduced.

## 5. Information architecture and responsive layout

The desktop page follows the selected editorial layout:

- A 68 px application header with product name, evidence-backed health summary, and local clock.
- A 196 px left navigation rail. Only **Morning Briefing** is an active route in JAI-050; future items
  may be visibly labelled as planned but must not behave like completed pages.
- A fluid main reading column, approximately 760–860 px at the reference viewport, containing the
  page heading, latest report identity, executive summary, metric strip, and recommendation list.
- A 340–360 px evidence rail containing next schedule, missing-record evidence, latest pipeline
  stages, and delivery capability/status.

Responsive behavior is content-preserving:

- `>= 1280px`: full header, navigation, reading column, and evidence rail.
- `768px–1279px`: compact navigation; evidence rail moves below the report without changing meaning.
- `< 768px`: one column, a keyboard-operable navigation sheet, stacked metrics, and recommendation
  rows with metadata wrapping below the title. No horizontal page scrolling.

The page uses a maximum content width of 1484 px, 24–32 px desktop gutters, 16 px narrow-screen
gutters, and an 8 px spacing grid. Related content uses typography and separators before containers;
cards must not be nested merely to create hierarchy.

## 6. Visual tokens

The default and only JAI-050 theme is light. Token names follow shadcn/ui semantics and are consumed
through Tailwind utilities rather than raw color values inside components.

```css
:root {
  --background: oklch(0.985 0.004 250);
  --foreground: oklch(0.205 0.035 255);
  --card: oklch(1 0 0);
  --card-foreground: var(--foreground);
  --popover: oklch(1 0 0);
  --popover-foreground: var(--foreground);
  --primary: oklch(0.56 0.16 250);
  --primary-foreground: oklch(0.985 0.005 250);
  --secondary: oklch(0.955 0.018 245);
  --secondary-foreground: oklch(0.31 0.055 250);
  --muted: oklch(0.96 0.009 250);
  --muted-foreground: oklch(0.52 0.035 255);
  --accent: oklch(0.94 0.03 245);
  --accent-foreground: oklch(0.32 0.08 250);
  --destructive: oklch(0.58 0.21 25);
  --border: oklch(0.90 0.012 250);
  --input: var(--border);
  --ring: oklch(0.63 0.15 250);
  --evidence: oklch(0.53 0.105 205);
  --attention: oklch(0.72 0.15 72);
  --success: oklch(0.62 0.15 155);
  --radius: 0.625rem;
}
```

Typography uses the system-first stack `Inter, "Noto Sans SC", "Microsoft YaHei", system-ui,
sans-serif`; the product must not depend on a live font CDN. Body copy is 14–16 px with at least 1.5
line height. The page title is 36–40 px on desktop and 30–32 px on narrow screens. Numerical evidence
uses tabular figures. Borders are one pixel; shadows are rare and subtle; no gradients are permitted.

## 7. Components, content, and states

Build reusable page-level components around shadcn/ui primitives:

- `AppShell`, `AppHeader`, and `PrimaryNavigation` define the durable layout.
- `ReportBriefing` shows the immutable snapshot ID, report date, created time, and a short deterministic
  summary derived from its sections.
- `ReportMetrics` counts persisted items only and labels exactly what each number measures.
- `RecommendationList` preserves report section order and item order. Each row includes organization,
  role, region, deadline, score, reason, risks, and a safe original-source link when present.
- `ScheduleEvidence`, `LedgerGapNotice`, `PipelineStages`, and `DeliveryEvidence` form the evidence rail.
- `StatusBadge` maps backend states to text plus color/icon; color alone never carries meaning.

Every data region has four explicit states: loading skeleton, empty evidence, safely summarized error,
and loaded content. Empty is not error. An unavailable delivery schema before JAI-027 G5 is rendered as
**Delivery not enabled · awaiting migration/configuration**, not as a failed delivery. Raw exception
texts, provider payloads, hashes, tokens, and database URLs never reach the page.

## 8. Read-only API contract

JAI-050 uses these GET boundaries only:

- `GET /health/live`: existing process liveness.
- `GET /health/ready`: existing database readiness.
- `GET /dashboard/briefing`: one bounded aggregate containing server time/timezone, the fixed job's
  presence and next-run timestamp, up to seven recent pipeline runs with latest stage attempts, the
  latest immutable report and ordered report items, expected dates with no pipeline ledger row, and
  the selected report's delivery capability/status.
- `GET /reports/daily/{snapshot_id}/html`: existing persisted HTML for an explicit report link; the
  dashboard does not generate or mutate a report.

`/dashboard/briefing` must return a stable Pydantic response, order arrays deterministically, cap all
collections, and expose enumerated safe error codes only. It checks whether JAI-027 delivery tables
exist before querying them, allowing the current `0009_pipeline_scheduling` business database to
render an honest pre-migration state. Database query failure maps to a sanitized 503 response.

## 9. Accessibility and interaction rules

- Use landmarks (`header`, `nav`, `main`, complementary evidence rail) and one page-level `h1`.
- All links and disclosure controls work by keyboard and show a visible `:focus-visible` ring.
- Maintain WCAG 2.2 AA contrast for text, controls, borders that convey state, and focus indication.
- Respect reduced motion. JAI-050 needs no decorative animation; loading indicators must not flash.
- Original-source links open deliberately with accessible names and safe `rel` attributes.
- At 200% zoom, content remains usable without losing evidence labels or requiring two-dimensional
  scrolling.

## 10. Verification and delivery gates

Before JAI-050 may be handed off:

1. Frontend format, lint, strict type check, unit tests, and production build pass from locked deps.
2. FastAPI unit/contract tests cover loaded, empty, pre-`0010`, and sanitized database-error states.
3. The existing Python `scripts/check.py` gate passes with PostgreSQL and no skipped tests.
4. Browser checks cover the reference viewport (`1484x1060`), 1440 px desktop, tablet, and narrow
   mobile widths; primary navigation and report/source links are exercised.
5. Design QA compares the reference and implementation at the same viewport, fixes all P0–P2
   findings, and records `final result: passed` in the Issue-owned QA report.

JAI-050 cannot merge to `develop` before JAI-027. It does not authorize business migration `0010`,
credentials, live PushPlus requests, scheduler restart, makeup runs, live sources, JAI-028 trials,
JAI-051 feedback migration, or JAI-029 release work.

## 11. Decision history and references

- D-038/U1-R and the stacked-branch order were approved on 2026-09-14.
- U2 selected option 1, **Morning Briefing**, as the production visual baseline.
- [Google DESIGN.md specification](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md)
- [shadcn/ui theming](https://ui.shadcn.com/docs/theming)
- [shadcn/ui Vite installation](https://ui.shadcn.com/docs/installation/vite)
- [Tailwind CSS theme variables](https://tailwindcss.com/docs/theme)
- [Tailwind CSS responsive design](https://tailwindcss.com/docs/responsive-design)
