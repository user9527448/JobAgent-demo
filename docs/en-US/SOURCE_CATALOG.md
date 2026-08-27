# Recruitment source catalog

> Simplified Chinese source document: [`../SOURCE_CATALOG.md`](../SOURCE_CATALOG.md).

This document records the target sources, integration status, and manual maintenance rules established by JAI-011 and JAI-021. [`config/source_catalog.toml`](../../config/source_catalog.toml) is the machine-readable authority; this document explains why each source is included, whether it can currently run, and the constraints for future integration.

## 1. Coverage goals

- Campus recruitment: prioritize education authorities, public student-employment services, and public job-fair information.
- Jiangsu/Zhejiang/Shanghai public examinations: cover public civil-service and public-institution notices, application periods, qualification review, and exam schedules.
- Central/state-owned enterprise recruitment: prefer stable official aggregators or representative enterprise announcement columns; disable persistently unreachable sources under the stability gate while retaining diagnostics.
- Foreign-enterprise recruitment: prioritize company-owned career sites for China and Jiangsu/Zhejiang/Shanghai jobs, with a separate product section later.
- Collect only public lists, details, and attachments that require no login. Never enter application forms, handle CAPTCHA, or bypass access controls.

## 2. Target sites

| Category | Region | Official source | Public entry | Status | Notes |
|---|---|---|---|---|---|
| Campus | National | National College Student Employment Service Platform | [Jobs](https://www.ncss.cn/student/jobs/index.html) | Active | Source 4; uses the page's own unauthenticated GET list and public details, never application actions |
| Campus | Shanghai/Yangtze River Delta | Shanghai Student Employment and Entrepreneurship Service | [Job fairs](https://www.firstjob.shec.edu.cn/jobfair) | Active | Source 3; public fair schedules from the Shanghai Student Affairs Center, using only the official read-only query |
| Public exam | Jiangsu | Jiangsu Personnel Examination Network | [Exam topics](https://jshrss.jiangsu.gov.cn/col/col57253/index.html) | Active | Source 2; public civil-service, institution, and related schedules; never the registration system |
| Public exam | Zhejiang | Zhejiang Civil Service Examination and Recruitment Network | [Home](https://gwy.zjks.gov.cn/) | Planned | Recruitment notices, registration statistics, and exam schedules |
| Public exam | Shanghai | Shanghai Civil Service Bureau | [Home](https://www.shacs.gov.cn/) | Planned | Public recruitment notices only; never application forms |
| Public exam | Shanghai | Shanghai Human Resources and Social Security Bureau | [Public-institution recruitment](https://rsj.sh.gov.cn/tsydwgkzp_17406/index.html) | Active | Source 5; recruitment-announcement paths only, excluding proposed-hire notices and registration systems |
| State-owned | National | State-owned Assets Supervision and Administration Commission | [Public recruitment](https://www.sasac.gov.cn/n2588035/n2588325/n2588350/index.html) | Blocked | JAI-011's first Adapter; disabled after two consecutive days of public-network/TLS failure, with historical contracts and diagnostics retained |
| State-owned | National/Jiangsu-Zhejiang-Shanghai | State Grid | [Recruitment](https://zhaopin.sgcc.com.cn/) | Planned | Dynamic portal; verify public interfaces, terms, and stability first |
| State-owned | National/Jiangsu-Zhejiang-Shanghai | China Mobile | [Recruitment announcements](https://job.10086.cn/personal/notice/) | Active | JAI-021 stability replacement; reads only same-origin static JSON declared by the page and public details, never account or application actions |
| State-owned | National/Jiangsu-Zhejiang-Shanghai | China Telecom | [Group recruitment](https://www.chinatelecom.com.cn/ct/zp/) | Planned | Prefer the group public column over personal application functions |
| State-owned | National/Jiangsu-Zhejiang-Shanghai | CNPC | [Graduate recruitment](https://zhaopin.cnpc.com.cn/) | Planned | Dynamic portal; verify public-list stability first |
| Foreign enterprise | China/Jiangsu-Zhejiang-Shanghai | Apple | [China careers](https://jobs.apple.com/zh-cn/search?location=shanghai-state157) | Planned | Official public student/graduate jobs; never submit applications |
| Foreign enterprise | China/Jiangsu-Zhejiang-Shanghai | Microsoft | [Greater China careers](https://careers.microsoft.com/v2/global/en/locations/gcr.html) | Planned | Official public jobs; never access candidate accounts |
| Foreign enterprise | China/Jiangsu-Zhejiang-Shanghai | Siemens | [Job search](https://jobs.siemens.com/en_US/externaljobs/SearchJobs/) | Planned | Verify China filters and public detail-URL stability first |
| Foreign enterprise | China/Jiangsu-Zhejiang-Shanghai | SAP | [China jobs](https://jobs.sap.com/go/China/8807101/) | Planned | Official China jobs/student programs; never submit talent-community forms |
| Foreign enterprise | China/Jiangsu-Zhejiang-Shanghai | P&G | [Greater China careers](https://www.pgcareers.com/global/en/locations/greaterchina/) | Planned | Official public jobs; never fill talent-community or application forms |

`Planned` means registered as a candidate, not that the program will access it. Machine configuration requires `implementation_status = "planned"` and `enabled = false`; `Blocked` uses `blocked` and likewise cannot be enabled.

All 11 official candidates remain mapped to the roadmap: JAI-011/JAI-021 currently enable five, China Mobile was absorbed early from JAI-041 as the stability replacement, SASAC remains one blocked source, and the five remaining planned sources stay under the unfinished JAI-038 through JAI-043 items. If a dynamic portal cannot be read stably without login/CAPTCHA and within its terms, it stays `planned` or becomes `blocked`; prefer a stable public announcement endpoint. Roadmap inclusion never authorizes bypassing restrictions.

Commercial platforms such as BOSS Zhipin are excluded from this executable catalog. Their manual-reference role and compliance boundary are documented in the [unofficial recruitment reference sources](../REFERENCE_SOURCES.md).

## 3. Manual maintenance

Edit the matching `[[sources]]` entry in `config/source_catalog.toml`:

- `key`: stable unique machine identifier; do not rename casually after launch.
- `category`: one of `campus`, `public_exam`, `state_owned`, or `foreign_enterprise`.
- `regions`: stable English identifiers such as `national`, `jiangsu`, `zhejiang`, and `shanghai`.
- `base_url` / `list_url`: credential-free HTTPS official URLs.
- `implementation_status`: `planned`, `active`, or `blocked`.
- `enabled`: true only for an `active` source with an Adapter.
- `include_keywords`: title must match at least one when present.
- `exclude_keywords`: any match excludes the title and takes precedence.
- `crawl_interval_minutes`: source-level suggested interval; the shared HTTP client still enforces request pacing.

After an edit, run:

```powershell
.\.venv\Scripts\python.exe scripts/run_source_preview.py --list
.\.venv\Scripts\python.exe -m pytest tests/crawlers/test_catalog.py -q
```

Low-frequency previews access public sites but do not write the database:

```powershell
.\.venv\Scripts\python.exe scripts/run_source_preview.py --source jiangsu-personnel-exam --limit 10 --fetch-first-detail
.\.venv\Scripts\python.exe scripts/run_source_preview.py --source shanghai-firstjob --limit 10 --fetch-first-detail
.\.venv\Scripts\python.exe scripts/run_source_preview.py --source ncss-jobs --limit 3 --fetch-first-detail
.\.venv\Scripts\python.exe scripts/run_source_preview.py --source shanghai-public-institution --limit 3 --fetch-first-detail
.\.venv\Scripts\python.exe scripts/run_source_preview.py --source china-mobile-recruitment --limit 3 --fetch-first-detail
```

## 4. New-source launch checklist

1. Verify the official owner, HTTPS entry, terms, and robots policy.
2. Confirm public access requires no login, CAPTCHA, or form submission.
3. Keep at least three sanitized list/detail fixture groups and pass Adapter contracts.
4. Keep configuration `planned`/`enabled = false` until Adapter, fixtures, and visible failures are ready; only then switch to `active`.
5. Complete low-frequency live smoke tests and two idempotent persistence runs before scheduling.

## 5. Current environment limitations

On 2026-08-27, the SASAC public recruitment column failed with retryable `PoolTimeout` for a second consecutive day. The user's normal browser also failed, the public `www` CDN could not be reached, and the official `wap` endpoint exposed an expired certificate, so the W6 stability gate moved it to disabled `blocked` status. China Mobile's official announcement page and same-origin static list/detail JSON returned 200 to bounded GET checks; the final replacement run completed three details and all five active sources, becoming stability day 1. One earlier list request did hit `PoolTimeout`, so observation must continue. Never infer an application deadline from JSON down-time; retain an image-only body's same-origin image URL without download or OCR; never enter registration, login, resume, or application actions.
