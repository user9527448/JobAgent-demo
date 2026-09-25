# JOBAGENT Frontend Foundation

> 简体中文：[JOBAGENT 前端基底](zh-CN/FRONTEND.md)

## Scope

JAI-050 introduces the production frontend foundation and the first read-only **Morning Briefing**
page. The visual authority is [DESIGN.md](DESIGN.md). This page reads persisted evidence only; it
does not start, retry, make up, send, resend, configure, or edit anything.

## Stack and directories

- `frontend/`: React, strict TypeScript, Vite, Tailwind CSS v4, repository-owned shadcn/ui-style
  components, Radix primitives, and Lucide icons.
- `src/jobagent/dashboard/`: bounded read-only evidence aggregation.
- `GET /dashboard/briefing`: stable page-level contract.
- `src/jobagent/api/frontend.py`: same-origin `/app/` shell and static-asset serving.

The committed `pnpm-lock.yaml` is authoritative. Do not commit `node_modules`, `dist`, Vite caches,
pnpm stores, runtime API responses, or screenshots containing business data.

## Local development

Reuse the existing repository Python environment and start the API separately on port 8000. Then:

```powershell
Set-Location frontend
pnpm install --frozen-lockfile
pnpm dev
```

Vite serves `/app/` and proxies only `/dashboard`, `/health`, and `/reports` to the local FastAPI
process. It does not hold provider tokens or other secrets.

## Checks and production build

```powershell
pnpm format
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:sites
```

`pnpm build` writes the client to `frontend/dist/client`. The Docker multi-stage build installs from
the frozen lockfile, builds that client, copies it to `/app/frontend-dist`, and sets
`JOBAGENT_FRONTEND_DIST_PATH` for FastAPI. Client paths below `/app/` fall back to the built
`index.html`; API prefixes remain independent and never receive an HTML fallback.

## Evidence and error rules

- Missing ledger rows remain **no run record**; they are never translated into a guessed status.
- Delivery schema absence is a capability state, not a failed send.
- Frontend errors use fixed safe copy. Raw database/provider text, URLs containing credentials,
  tokens, hashes, and provider payloads are not rendered.
- External source links are accepted only for `http` or `https`, open deliberately, and carry safe
  `rel` attributes.
- Loaded, empty, unavailable, and loading states are separate and testable.

## Issue boundary

Future navigation labels are disabled placeholders. JAI-051 owns writable feedback, including its
schema and API. JAI-050 does not authorize migration `0010`, live PushPlus calls, scheduler changes,
makeup runs, JAI-028 unattended trials, or JAI-029 release work.
