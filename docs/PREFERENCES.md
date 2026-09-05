# Single-user preferences

> Simplified Chinese: [单用户偏好](zh-CN/PREFERENCES.md)

JAI-022 adds one local user's structured preference profile and a read/full-replacement API. It stores inputs needed by later matching, but does not filter, score, or recompute jobs; JAI-023 owns that behavior.

## Contract

| Field | Type | Meaning when empty |
|---|---|---|
| `regions` | ordered unique region-code array | Any region |
| `education` | education enum or `null` | No education restriction |
| `majors` | ordered unique text array | Any major |
| `job_keywords` | ordered unique text array | No required job keyword |
| `organization_types` | ordered unique organization-type array | Any organization type |
| `exclusions` | ordered unique text array | No exclusion term |

Empty collections and `education=null` are deliberately unrestricted defaults. JAI-022 never interprets them as “match nothing.” Text items are Unicode NFKC-normalized, surrounding/repeated whitespace is removed, and case-insensitive duplicates retain their first occurrence.

Region and education codes reuse the deterministic extraction dictionaries. Organization types are a separate preference vocabulary because source categories such as `public_exam` describe collection, not an employer:

- `government`
- `public_institution`
- `state_owned`
- `private`
- `foreign_enterprise`

## API

`GET /preferences` returns the singleton profile and its audit/recomputation state.

`PUT /preferences` fully replaces all preference fields. Omitted preference fields therefore take their unrestricted defaults. Input is bounded by Pydantic schema lengths and enum values before persistence.

```json
{
  "regions": ["shanghai", "jiangsu"],
  "education": "bachelor_or_above",
  "majors": ["computer science"],
  "job_keywords": ["Python"],
  "organization_types": ["state_owned"],
  "exclusions": ["sales"],
  "trigger_recompute": true
}
```

The response repeats the normalized fields and adds `created_at`, `updated_at`, `recompute_required`, and `recompute_requested_at`. Infrastructure failures use stable `preferences.*` error codes; invalid input returns FastAPI's normal `422` response without calling persistence.

## Persistence and recomputation boundary

Migration `0006_single_user_preferences` creates `user_preferences` and inserts exactly one row with `id=1`. A check constraint rejects any second user ID. JSON fields must be arrays, the education value is database-constrained, and all audit times are timezone-aware UTC instants.

Updates lock the singleton row, replace all values in one transaction, and set `updated_at`. `trigger_recompute` defaults to `true`; when enabled, it sets the sticky `recompute_required` flag and records `recompute_requested_at`. An update with `trigger_recompute=false` never clears an already pending signal. JAI-023 may consume and acknowledge that signal as part of its versioned matching transaction; JAI-022 intentionally provides no scoring logic or public acknowledgement endpoint.

## Scope boundary

JAI-022 does not add hard filters, match scores, score versions, explanations, report generation, multi-user authentication, or source-specific behavior. It also does not infer preferences from collected recruitment data.
