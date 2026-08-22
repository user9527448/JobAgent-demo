# JOBAGENT English Documentation Index

> 简体中文索引：[`../zh-CN/README.md`](../zh-CN/README.md).

Repository documentation uses separate English and Simplified Chinese files. Updating either version requires updating its counterpart in the same commit. Code identifiers, environment variables, error codes, URLs, and commands remain unchanged. JAI-047/JAI-048 migrate legacy single-language files in bounded steps; one language must never overwrite the other.

## Current bilingual documentation

| Topic | English | 简体中文 |
|---|---|---|
| Repository collaboration rules | [English](../../AGENTS.md) | [中文](../zh-CN/AGENTS.md) |
| Detailed development plan | [English](DEVELOPMENT_PLAN.md) | [中文](../DEVELOPMENT_PLAN.md) |
| GitHub Issues backlog | [English](GITHUB_ISSUES.md) | [中文](../GITHUB_ISSUES.md) |
| Continuous development work log | [English](../WORKLOG.md) | [中文](../zh-CN/WORKLOG.md) |
| Source Adapter and collection orchestration | [English](../COLLECTION.md) | [中文](../zh-CN/COLLECTION.md) |
| Database models and migrations | [English](../DATABASE.md) | [中文](../zh-CN/DATABASE.md) |
| Source HTTP client policy | [English](../HTTP_CLIENT.md) | [中文](../zh-CN/HTTP_CLIENT.md) |
| Raw announcement normalization and versioning | [English](../RAW_DOCUMENTS.md) | [中文](../zh-CN/RAW_DOCUMENTS.md) |
| Attachment discovery and storage | [English](../ATTACHMENTS.md) | [中文](../zh-CN/ATTACHMENTS.md) |
| Parser contracts and intermediate format | [English](../PARSING.md) | [中文](../zh-CN/PARSING.md) |
| Deterministic field extraction and normalization | [English](../EXTRACTION.md) | [中文](../zh-CN/EXTRACTION.md) |
| JAI-005 Jining source Spike | [English](../spikes/JAI-005-JINING-SOURCE.md) | [中文](../zh-CN/spikes/JAI-005-JINING-SOURCE.md) |
| Database migration guide | [English](../../migrations/README.md) | [中文](../zh-CN/MIGRATIONS.md) |
| JAI-005 fixture guide | [English](../../tests/fixtures/jining/README.md) | [中文](../zh-CN/fixtures/JINING.md) |
| JAI-016 attachment golden fixtures | [English](../../tests/fixtures/attachments/README.md) | [中文](../zh-CN/fixtures/ATTACHMENTS.md) |

## Historical archive

- The [original mixed-language WORKLOG through JAI-046](../archive/WORKLOG-LEGACY-THROUGH-JAI-046.md) is preserved byte-for-byte with SHA-256 `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`.
- The archive receives no new entries and is intentionally not translated. Current work is recorded only in the separate active logs listed above.

## JAI-048 legacy migration inventory

The following repository-authored documents still lack an independent counterpart. JAI-048 will retain every original file's language and add the missing version. If another Issue substantively changes one first, that same commit must add its counterpart.

| Document | Current language | Missing version |
|---|---|---|
| [Project README](../../README.md) | Simplified Chinese | English |
| [Configuration, logging, and error conventions](../CONFIGURATION.md) | Simplified Chinese | English |
| [Recruitment source catalog](../SOURCE_CATALOG.md) | Simplified Chinese | English |
| [Unofficial recruitment reference sources](../REFERENCE_SOURCES.md) | Simplified Chinese | English |
| [Firstjob fixture guide](../../tests/fixtures/firstjob/README.md) | English | Simplified Chinese |
| [Jiangsu personnel-exam fixture guide](../../tests/fixtures/jiangsu/README.md) | Simplified Chinese | English |
| [SASAC fixture guide](../../tests/fixtures/sasac/README.md) | Simplified Chinese | English |

## Synchronization rules

1. Update both language files in the same commit for every paired document.
2. Add both English and Simplified Chinese files and both index entries for new repository documentation.
3. Keep sections, constraints, and examples semantically aligned; do not translate code/API identifiers.
4. If the two versions diverge, use code and tests as the technical authority and correct both files together.
5. Historical archives and third-party source material require an explicit non-translation reason and must not be presented as paired documentation.
