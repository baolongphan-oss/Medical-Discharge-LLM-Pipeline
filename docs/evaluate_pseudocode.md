# evaluate.py: pseudocode

Build it in this order. Run `pytest tests/test_evaluate.py` after each step that has a test.
The finished version is in git (commit 37d13f0). Peek only when stuck.

## Step 1: Imports and constants
- import json, re, unicodedata, Path, pandas
- LABELS = folder "labels", OUTPUTS = "outputs", RESULTS = "results"
- FIELDS = the four fields to score: dose, frequency, duration, status

## Step 2: key(text)
- if text is None → return None   (None must stay None, so "missing" == "missing")
- normalize unicode (NFKC), lowercase
- remove every character that isn't a letter or digit
- return it
- Test: "Lasix 40 mg." → "lasix40mg"

## Step 3: name_key(text) and freq_key(text)
- FORM = regex of dosage-form words (nebulizer, inhaler, tablet, patch, spray, cream, respules…)
- name_key: lowercase, replace FORM words with a space, then key()
- ROUTE = regex of route words (p.o., by mouth, subcu, IV, IM…)
- freq_key: if None → None; lowercase, replace ROUTE words with a space, key(); empty string → None
- Tests: "Combivent nebulizer" == "Combivent"; "p.o. b.i.d" == "b.i.d."

## Step 4: load_meds(path)
- if the file doesn't exist → return []   (model produced nothing)
- read the JSON, return its "medications" list (empty list if missing)

## Step 5: match_meds(gold, pred)   ← the core
- pairs = [], used_gold = set of indexes, used_pred = set of indexes
- run two passes: first strict (name AND dose must match), then loose (name only)
  - for each pred med not already used:
    - for each gold med not already used:
      - skip if name_key differs
      - in the strict pass, also skip if key(dose) differs
      - otherwise: save the pair, mark both used, stop searching (break)
- fn = gold meds never used (missed)
- fp = pred meds never used (invented / extra)
- return pairs, fn, fp
- Why two passes: a taper has the same drug twice (prednisone 40 mg, 20 mg). Pairing by dose first
  stops 40 from pairing with 20 just because of list order.

## Step 6: score_note(gold, pred)
- pairs, fn, fp = match_meds(...)
- row = gold count, pred count, tp = number of pairs, fn, fp
- for each field in FIELDS: count pairs where key(gold field) == key(pred field)
- extra: frequency_noroute_correct using freq_key
- return row (a dict)

## Step 7: evaluate(pred_dir)
- for each label file in labels/ (sorted):
  - gold = its medications
  - pred = load_meds(pred_dir / same filename)
  - add {note_id, **score_note(gold, pred)} to a list
- return it as a DataFrame

## Step 8: summarize(df, version)
- add up tp, fn, fp over ALL notes (micro-average)
- precision = tp / (tp + fp); recall = tp / (tp + fn)   (guard against dividing by 0)
- med-free notes = rows where gold == 0; invented = sum of their pred counts
- each field accuracy = total correct / total tp
- round to 3 places, return a dict

## Step 9: main
- make results/ if needed
- for v3 and v4: evaluate the test output folder, save per-note CSV, collect summarize()
- save the summary CSV, print it transposed

## Check yourself
Your output should match results/eval_summary.csv (v4: precision 0.901, recall 0.901).
