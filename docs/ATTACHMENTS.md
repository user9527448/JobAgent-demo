# Attachment discovery and storage

> 简体中文：[附件发现与存储](zh-CN/ATTACHMENTS.md)

JAI-010 adds bounded, traceable storage for PDF, XLS and XLSX files linked by an immutable raw-document version. File interpretation remains a later pipeline stage; storing a file never marks it parsed.

## Discovery

`discover_attachment_links()` examines announcement anchor elements and returns supported links in document order. It:

- recognizes `.pdf`, `.xls` and `.xlsx` from the URL path or visible link text;
- resolves relative URLs and applies the same canonicalization rules as raw documents;
- removes fragments and known tracking parameters while retaining meaningful query parameters;
- de-duplicates canonical URLs within the announcement;
- sanitizes display names without using them as storage paths.

Discovery does not fetch links and does not infer attachments from arbitrary page text.

## Download and validation

`AttachmentStorageService` uses the shared source HTTP client's streamed request path, so source concurrency, pacing, timeout, retry and safe logging rules still apply. Both `Content-Length` and actual streamed bytes are checked against `JOBAGENT_ATTACHMENT_MAX_BYTES`; streamed chunks use `JOBAGENT_ATTACHMENT_CHUNK_BYTES`.

An extension alone is never enough to accept a file:

| Declared type | Required content | Accepted response MIME types |
|---|---|---|
| PDF | `%PDF-` signature near the beginning | `application/pdf` or a generic binary type |
| XLS | OLE compound-file signature | `application/vnd.ms-excel` or a generic binary type |
| XLSX | ZIP containing `[Content_Types].xml` and `xl/workbook.xml` | XLSX MIME, `application/zip` or a generic binary type |

HTML error pages, empty bodies, mismatched signatures and incompatible non-generic MIME types are rejected. Validation intentionally establishes file identity only; the common parser contract is documented in [`PARSING.md`](PARSING.md), while PDF text extraction, OCR and spreadsheet parsing belong to JAI-014 through JAI-016.

## Atomic content-addressed storage

The service streams into `<storage-root>/.tmp`, flushes and synchronizes the complete file, validates it, and computes SHA-256 before publishing it with an atomic same-volume replace. Final objects use:

```text
objects/<first-two-sha256-characters>/<sha256>.<extension>
```

The database stores this relative path, never a machine-specific absolute path. Repeating the same document URL reuses a valid stored row and local object without another request. Different URLs with identical content converge on the same object path. An interrupted or rejected download removes its `.part` file and cannot be marked `stored`.

## Database state

Attachment download and parsing are independent state machines:

- `download_status`: `pending`, `stored` or `failed`;
- `parse_status`: remains `pending` until the later parsing Issues run;
- successful storage requires MIME type, SHA-256, relative path, byte count and download timestamp;
- failure clears successful-storage metadata and records only a safe error code/message.

The unique `(document_id, url)` constraint and PostgreSQL advisory lock prevent duplicate metadata rows. The content-addressed final path prevents duplicate file objects even when two workers race after row creation.

## Configuration

| Environment variable | Default | Purpose |
|---|---:|---|
| `JOBAGENT_ATTACHMENT_STORAGE_PATH` | `data/attachments` | Local attachment object-store root |
| `JOBAGENT_ATTACHMENT_MAX_BYTES` | `26214400` | Maximum response size (25 MiB) |
| `JOBAGENT_ATTACHMENT_CHUNK_BYTES` | `65536` | Stream read/write chunk size |

Compose maps the storage root to the named `attachment-data` volume at `/app/data/attachments`, writable by the non-root API user. Runtime attachment data remains outside Git.
