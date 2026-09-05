# Deterministic matching and versioned scoring

> Simplified Chinese: [确定性匹配与版本化评分](zh-CN/MATCHING.md)

JAI-023 converts one explicit position snapshot and the JAI-022 preference snapshot into a deterministic, explainable result. The engine is pure: it performs no database, network, LLM, report, or notification operation, and receives the evaluation instant explicitly.

## Hard filters

The total score is zero when any hard filter fails:

| Rule | Passing behavior |
|---|---|
| `validation_eligibility` | The current extraction version has `recommendation_eligible=true` from JAI-020 |
| `education` | No evidenced mismatch exists, or the candidate's explicit education rank meets the explicit position requirement |
| `deadline` | No deadline is evidenced, or the UTC deadline is strictly later than `evaluated_at` |
| `exclusion` | No NFKC/case-folded exclusion term is a substring of the organization, announcement/position title, department, major, or requirements |

Missing education or deadline evidence is never invented and does not itself hard-filter a position. Missing data is instead reflected by the completeness component and remains available for JAI-024's needs-confirmation grouping. The exact deadline instant is treated as closed.

Education ranks are deterministic: `no_requirement` < `high_school`/`secondary_vocational` < `associate`/`associate_or_above` < `bachelor`/`bachelor_or_above` < `master`/`master_or_above` < `doctorate`.

## Component scores

When all hard filters pass, `jai-023-v1` uses the planned 100-point formula:

| Component | Maximum | Rule |
|---|---:|---|
| `region` | 25 | Empty preferences are neutral/full; `national` or an exact region match receives full points |
| `job_direction` | 30 | Empty preferences are neutral/full; any explicit job keyword match receives full points |
| `major` | 15 | Empty preferences are neutral/full; any explicit major match receives full points |
| `organization_type` | 10 | Empty preferences are neutral/full; otherwise exact enum match |
| `deadline_urgency` | 10 | Open deadline: ≤72h = 10, ≤7d = 8, ≤14d = 5, later = 2; missing/closed = 0 |
| `information_completeness` | 10 | Two points each for organization, position/announcement title, region, deadline, and source URL |

For persisted extraction data, employer type is derived only from categories whose meaning is direct: `civil_service → government`, `public_institution → public_institution`, and `state_owned → state_owned`. `campus` and `social` do not prove an employer type and remain unknown rather than being guessed.

Each hard filter persists its rule, inputs, pass/fail decision, and explanation. Each component persists its component name, rule version, inputs, score, maximum, and explanation. Reports and user-facing recommendation narratives remain JAI-024.

## Determinism and versioning

`DeterministicMatchingEngine.evaluate()` requires the position data, normalized preferences, timezone-aware `evaluated_at`, and score version. UTC-normalized canonical JSON produces separate SHA-256 hashes for the position/time input, preferences, and complete result. Identical inputs and `jai-023-v1` therefore produce identical decisions, scores, components, explanations, and hashes.

Unknown score versions fail explicitly. Changing a rule or weight requires a new version; it must never silently change the meaning of `jai-023-v1`. Database `generated_at` is audit metadata and is excluded from deterministic result hashing.

## Persistence and full recomputation

Migration `0007_versioned_match_results` adds `match_results`:

- one restricted foreign key to `job_positions` and the singleton `user_preferences` row;
- score/input/preference/result hashes, explicit `score_version`, `evaluated_at`, and the preference update instant;
- JSONB `matched_rules` and `components` explanation payloads;
- append-only `supersedes_id` history and one current result per position;
- database checks for hashes, score range, JSON arrays, and zero score after a failed hard filter.

`SqlAlchemyMatchingService.recompute_if_requested()` locks the singleton preference row and, when its sticky signal is set, evaluates every position belonging to a current `job_posts` version in stable position-ID order. Result creation, current-history replacement, and signal acknowledgement share one transaction. Any failure rolls back both results and acknowledgement, so a pending request cannot be lost. Successful acknowledgement keeps the preference `updated_at` unchanged because it identifies the preference values used for the batch.

Repeated consumption with no pending signal is a no-op. Repeating the same position/input/preference update instant reuses an identical result; a different result under the same calculation identity raises `matching.version_not_deterministic`.

## Scope boundary

JAI-023 does not implement daily-report queries, grouping, Markdown/HTML rendering, snapshots, delivery, notifications, scheduling, LLM ranking, embeddings, or user-facing matching APIs. JAI-024 owns reports; later pipeline/API Issues may call the reusable matching service.
