# Failure Log

## v1 — gpt-oss-120b — 2026-10-11 (dev notes)

| Note | Field | Issue | Severity | Fix idea |
|---|---|---|---|---|
| COPD/asthmatic bronchitis | medications.frequency | "one daily" → "once daily" (paraphrase) | Low | Normalize in eval; stress "copy exactly" |
| COPD/asthmatic bronchitis | follow_up | Missed "resume preadmission meds" + vaccine | Medium | Define follow-up scope in prompt |

## v2 — 2026-10 (dev notes)

| Note | Field | Issue | Severity | Fix idea |
|---|---|---|---|---|
| several | translation | Invented home care (incision care, spirometer, compression stockings) | High | Grounding rules (v3) |
| several | translation | Real warning signs placed in the wrong section | Medium | Section rules (v3) |
| death summary | translation | Instructions written for a deceased patient | High | Drop death summaries in prepare_data |

## v3 — 2026-10 (dev notes)

| Note | Field | Issue | Severity | Fix idea |
|---|---|---|---|---|
| 3513 | medications.dose | Lasix "40 mg 2 tablets" lost "2 tablets" (patient would take half dose) | High | Keep tablet count in dose (v4) |

## v4 — 2026-10-27 (dev notes)

| Note | Field | Issue | Severity | Fix idea |
|---|---|---|---|---|
| 5 notes | pipeline | Groq rate limits stopped the run after 4/9 notes | Medium | Pacing, retry with suggested wait, --skip-existing |

## Test set, v3 and v4 (24 notes, 2026-10-31 / 11-09)
Prompts frozen at `prompts-frozen-v4`. Issues logged, not fixed: fixing them would mean tuning on the test set.

| Note | Version | Field | Issue | Severity | Fix idea |
|---|---|---|---|---|---|
| 1913, 3400, 3539, 3596, 3933 | v4 | citations | 5/118 quotes not exact: pronoun swaps ("He" for "The patient") and dropped words. Manual check: all supported, 0 fabricated | Low | Fuzzy citation matching (roadmap) |
| 2114 | v3 | dose check | False positive: dose "one" matched the ordinary word "one" in the narrative | Low (checker bug) | Require a digit or unit in dose-leak matching (roadmap) |
| 2210 | — | data | MTSamples "discharge summary" is actually a TCU admission note; excluded | Medium (data quality) | Filter by note content, not category title (roadmap) |