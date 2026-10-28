# Labeling Guide

Ground truth for Stage 3 evaluation. The rules here are frozen once note #3 is
labeled. If a later note forces a rule change, update this file, add a line to
the changelog at the bottom, and re-check every label already written.

## Which notes

- 25 test notes, listed in `labels/selection.txt` (picked with a fixed seed;
  see `src/select_label_notes.py`).
- Label each note **before** running the pipeline on it. Do not open any
  model output for these notes until all 25 labels are committed.
- One file per note: `labels/note_<note_id>.json`.

## File format

Same shape as `DischargeExtraction`, but only `medications` is scored.
Leave the other fields empty.

```json
{
  "note_id": 2114,
  "final_diagnoses": [],
  "medications": [
    {
      "name": "Lasix",
      "dose": "40 mg, 2 tablets",
      "frequency": "twice a day",
      "duration": null,
      "status": "continued"
    }
  ],
  "procedures": [],
  "follow_up": [],
  "labeler_notes": "free text: anything ambiguous, with the rule you applied"
}
```

`labeler_notes` is not part of the schema. The eval script ignores it.

## What counts as a medication

Include medications the patient should take, change, or stop **after
discharge**, taken from discharge medications, discharge instructions, or
plan sections.

Exclude:
- Drugs given only during the stay (IV antibiotics in hospital, anesthesia,
  intra-op drugs, one-time doses in the ER), unless the note says to continue
  them at home.
- Admission or home medication lists, **unless** the discharge section refers
  back to them ("resume home medications as listed above"). In that case,
  label each listed drug with status `continued`.
- Non-drug items: oxygen, diet, therapy, devices (spirometer, stockings).
  Exception: a nebulizer medication with a named drug (e.g. albuterol neb)
  counts.
- Vaccines given in hospital.

## Fields

Copy what the note says. Do not correct, convert, or infer.

| Field | Rule | Example |
|---|---|---|
| name | As written. Brand stays brand, generic stays generic. Keep combination products as one entry. | "Coumadin", "Percocet" |
| dose | Strength plus tablet/puff count, exactly as written. `null` if not stated. | "40 mg, 2 tablets", "2 puffs", `null` |
| frequency | As written, keep PRN wording. `null` if not stated. | "b.i.d.", "every 6 hours as needed" |
| duration | Only if stated. `null` otherwise. | "x 10 days", "until follow-up" |
| status | See below. | |

Put route (p.o., IV) in the frequency field only if it is in the same phrase;
don't add it otherwise. It is not scored.

### Status

| Status | Use when the note explicitly says... |
|---|---|
| new | start, begin, new, "was started on" (for a home medication) |
| changed | the dose or frequency of an existing medication changed (increase, decrease, "now take") |
| continued | continue, resume, "same as before" |
| stopped | stop, discontinue, hold, "do not take" |
| unknown | the drug is listed with no wording that says which of the above |

**When unsure between two statuses, use `unknown`.** Do not guess from
clinical knowledge (e.g. "an antibiotic after surgery is probably new").
Most plain discharge med lists will be `unknown`, and that is fine.

## Edge cases

- **Same drug, two doses** (e.g. a taper, or morning/evening doses): two entries.
- **Ranges**: copy them as written ("1-2 tablets").
- **"Resume all home medications" with no list anywhere:** no entries. Write
  it in `labeler_notes`.
- **Medication mentioned only in a warning** ("avoid NSAIDs"): label as
  `stopped` only if it tells the patient to stop or avoid a specific drug
  or drug class. Otherwise skip.
- **No discharge medications at all** (several therapy and neonatal notes):
  `"medications": []`. This is a valid label, not a missing one.
- Tablet/unit count with no strength ("one", "one to two") goes in dose. (note_id=2114)
- Keep the reason in frequency ("p.r.n. pain", "for difficulty breathing"). (note_id=2114)
- Drug on the admission/home list but not mentioned at discharge, with no stop wording: don't label it. (note_id=132)

Add new cases here as you hit them, with the note_id.

## How the eval script matches (fixed now, before labeling)

- **Name match:** `normalize_for_match(pred) == normalize_for_match(gold)`,
  or the pair appears in `labels/aliases.json` (brand/generic pairs, e.g.
  `{"lasix": "furosemide"}`). Add a pair only when a note actually uses both
  names; never add one just because the model used a different name.
- **One-to-one:** each gold medication matches at most one predicted one.
- **Dose / frequency / status accuracy:** computed only on matched pairs,
  using normalized string equality. `null == null` counts as correct.
- **Notes with zero gold medications:** excluded from recall. Any
  medication the model predicts there counts as a false positive and is
  reported separately as "invented medications on medication-free notes".

## Post-hoc audit: unsupported instructions (Thursday, after labeling)

This is **not** pre-labeled, because it depends on what the model wrote.
For each patient-facing output, count every instruction sentence that no
sentence in the note supports.

- Supported: the note says it directly, or it restates a discharge
  instruction in plainer words.
- Unsupported: invented care (incision care, spirometer, stockings, diet)
  that the note doesn't mention; follow-ups with no source; wrong timing.
- Generic safety advice ("call 911 for chest pain") is supported only if the
  note mentions that symptom or a related condition.
- Record the count and the sentences in `labels/audit_<note_id>_<version>.json`.
  Audit every version you compare on the same notes, in one sitting, with these same rules.

## Changelog

- v1 (2026-10-27): initial rules.
