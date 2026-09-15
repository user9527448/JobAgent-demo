# JAI-050 Design QA

> 简体中文：[JAI-050 设计验收](docs/zh-CN/DESIGN_QA.md)

## Inputs and boundary

- Normative specification: `docs/DESIGN.md`.
- Selected reference: `docs/assets/jai-050/morning-briefing-reference.png`, `1484x1060`.
- Implementation: the production build served by FastAPI at `/app/`.
- State: the read-only `FakeDashboardService` synthetic fixture. No business database, scheduler,
  provider, or live source was contacted, and no synthetic screenshot is committed.

The reference and implementation capture were reviewed together at the same `1484x1060` viewport.
The reference controlled composition and hierarchy; persisted API fields controlled all displayed
facts.

## Comparison and fixes

| Priority | Finding | Resolution |
|---|---|---|
| P2 | The first implementation added an English eyebrow absent from the selected reference, pushing the main hierarchy down. | Removed it and aligned the title/subtitle/divider with the reference header rhythm. |
| P2 | The report identity occupied two rows while the reference used one compact line. | Combined the label and report date; retained snapshot ID and persisted creation time at the right. |
| P2 | The executive-summary region was visually too shallow. | Restored the reference density with a bounded 168 px desktop minimum height while preserving natural narrow-screen growth. |

No open P0, P1, or P2 finding remains.

## Browser verification

| View | Result |
|---|---|
| `1484x1060` reference viewport | Header, 196 px navigation, reading column, 356 px evidence rail, summary, metrics, recommendations, and evidence hierarchy match the selected composition. |
| `1440x900` desktop | Desktop evidence rail retained; `scrollWidth=1425 <= innerWidth=1440`; no console warning or error. |
| `1024x900` tablet | Navigation retained and evidence moved below report content; `scrollWidth=1009 <= innerWidth=1024`. |
| `390x844` mobile | Single-column content and two-column metrics retained all labels; `scrollWidth=375 <= innerWidth=390`. |
| `720x900` 200%-zoom equivalent | Compact navigation and one-column evidence remained usable; `scrollWidth=705 <= innerWidth=720`. |

The mobile navigation opened with `Tab` + `Enter`, trapped focus in the Radix sheet, and closed with
`Escape`. The persisted HTML report link opened the same-origin GET endpoint. Source links expose
accessible names and safe `rel` attributes; no external source was opened during QA. Loading, loaded,
empty, and sanitized error states are covered by automated tests.

## Gate

final result: passed
