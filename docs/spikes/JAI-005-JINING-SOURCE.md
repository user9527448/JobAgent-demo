# JAI-005 — Jining public recruitment source Spike

> 简体中文：[JAI-005 — 济宁公开招聘来源技术验证](../zh-CN/spikes/JAI-005-JINING-SOURCE.md)

## Outcome

The source can support a future JOBAGENT Adapter: a list page exposes detail links and dates, the selected detail page exposes stable metadata, body text and PDF attachment links, and the selected four-page PDF yields non-empty page-level text.

This is a technical validation, not the production crawler. Rate limiting, retries, conditional requests, storage and idempotency remain in JAI-006 through JAI-010.

## Source record

| Item | Value |
|---|---|
| Owner | Jining Human Resources and Social Security Bureau |
| Category | Public institution recruitment |
| List | `https://hrss.jining.gov.cn/col/col71291/index.html` |
| Detail sample | `https://hrss.jining.gov.cn/art/2026/1/22/art_71291_2718366.html` |
| PDF sample | `https://hrss.jining.gov.cn/attach/0/566c19e3bedd4043b7786ffb15540704.pdf` |
| Page types | UTF-8 static HTML and text PDF |
| Authentication | None |
| CAPTCHA | None |
| Planned frequency | Once daily, sequential requests, at least one second apart |

## Access and compliance check

Checked on 2026-08-09:

- `robots.txt` returned HTTP 200 and contained comments only; it declared no disallowed paths.
- The list, detail and PDF returned HTTP 200 without login, cookies or browser automation.
- Requests used `JOBAGENT/0.1 (+personal recruitment intelligence research; low-frequency)`.
- The Spike made sequential requests and retained one fixed sample of each required resource. Automated tests are fully offline.
- No login, CAPTCHA, access control or source restriction was bypassed. If the site's rules or access behavior change, collection must stop pending review.

## Verified structure

### List discovery

The page embeds records as HTML inside `<![CDATA[...]]>` blocks. Each item contains:

- detail path matching `art_71291_`;
- full title in the anchor's `title` attribute;
- publication date in `span.sp_time`.

Because the item markup is inside CDATA, parsing the outer page with a CSS selector alone returns no items. The Spike extracts each CDATA fragment and parses that fragment as HTML.

### Detail extraction

- title: `meta[name="ArticleTitle"]`;
- publication time: `meta[name="pubdate"]`;
- body: `#zoom .wenz`;
- PDF attachments: anchors inside the body whose URL contains `.pdf`.

The download links use `module/download/downfile.jsp` with a stored filename query parameter and redirect or stream a PDF response.

### PDF extraction

PyMuPDF extracts text from all four pages. Output retains a one-based page number so later field evidence can point back to the source page. The selected file is text-based and does not require OCR.

## Reproduction

Run the deterministic offline regression tests as part of the normal quality gate:

```powershell
python scripts/check.py
```

The optional live check performs exactly three sequential GET requests:

```powershell
python scripts/run_jining_spike.py
```

Do not schedule this Spike script. JAI-008 will provide the production HTTP policy.

## Known limitations and recommendation

- The list format is vendor-specific and invalid enough that CDATA handling needs a contract fixture.
- Publication metadata can differ from later page update metadata; the Spike uses the visible `pubdate` field.
- PDF table reading order is suitable for discovery and evidence, but not yet normalized into job rows.
- Scanned or encrypted PDFs are not covered.
- The list includes notices from multiple stages of a recruitment cycle, so a future Adapter needs announcement-type classification.
- Before promoting this source in JAI-011, add at least two more detail fixtures and keep live HTTP concerns in the shared JAI-008 client.
