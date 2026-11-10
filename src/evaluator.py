# evaluate.py: pseudocode

import re, json, unicodedata
import pandas as pd
from pathlib import Path 

LABELS = Path("labels")
OUTPUTS = Path("outputs")
RESULTS = Path("results")
FIELDS = ['dose', 'frequency', 'duration', 'status']

def key(text):
    if text is None:
        return None 
    # normalize unicode text, in lower case, and remove anything not a letter or digit
    clean_text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[^a-zA-Z0-9]", "", clean_text)

# regex of dosage-form words
FORM = re.compile(r"\b(nebulizers?|neb|inhalers?|tablets?|tabs?|capsules?|patch|nasal spray|spray|cream|ointment|respules|solution|injection)\b")
def name_key(text):
    "remove dosage from the name"
    # for example: 'Combivent nebulizer' == 'Combivent'
    return key(FORM.sub(" ", text.lower()))

# a word from our list that starts at a word boundary and is followed by a space or the end of the text.
ROUTE = re.compile(r"\b(p\.?o\.?|by mouth|orally|subcu|subq|s\.?c\.?|sq|i\.?v\.?|i\.?m\.?|inhaled|topically)(?=\s|$)")
def freq_key(text):
    "remove route words from the frequency"
    # for example: "p.o. b.i.d" == "b.i.d."
    if text is None:
        return None
    return key(ROUTE.sub(" ", text.lower())) or None

def load_meds(path):
    "load the medications for each note"
    if not path.exists():
      return []
    return json.loads(path.read_text()).get("medications", [])

def match_meds(actual, pred):
    pairs = []
    found_actuals = set()
    found_preds = set()

    # run a strict match first, then a second pass for loose matches (correct name but wrong dosage)
    # do this because medications might be listed twice or more times (taper medications)
    # so we pair by doses first
    for strict_match in [True, False]:
        for i, a in enumerate(actual):
            if i in found_actuals:
                continue
            for j, p in enumerate(pred):
                # loose match
                if j in found_preds or name_key(a["name"]) != name_key(p["name"]):
                    continue
                # strict match: name and dose must be correct
                if strict_match and key(a["dose"]) != key(p["dose"]):
                    continue
                pairs.append((a, p))
                found_actuals.add(i)
                found_preds.add(j)
                break 
    fn = len(actual) - len(found_actuals)
    fp = len(pred) - len(found_preds)
    return pairs, fn, fp

def score_note(actual, pred):
    pairs, fn, fp = match_meds(actual, pred)
    row = {
        "actual":   len(actual),
        "pred":     len(pred),
        "tp":       len(pairs),
        "fn":       fn,
        "fp":       fp
    }
    for f in FIELDS:
        sum_field = 0
        sum_freq = 0
        for a, p in pairs:
            # compares value match in each field
            if key(a.get(f)) == key(p.get(f)):
                sum_field += 1
            # compares frequency with route information stripped out
            if freq_key(a.get("frequency")) == freq_key(p.get("frequency")):
                sum_freq += 1
        row[f"{f}_correct"] = sum_field
        row["frequency_noroute_correct"] = sum_freq
    return row

def evaluate(pred_dir):
    "give a note score for each note_id in the LABELS folder"
    res = []
    label_files = sorted(LABELS.glob("note_*.json"))
    for f in label_files:
        actual_medications = load_meds(f)
        pred = load_meds(pred_dir / f.name)
        note_id = int(f.stem.split("_")[1])
        res.append({"note_id": note_id, **score_note(actual_medications, pred)})
    return pd.DataFrame(res)

def summarize(df, ver):
    tp = df.get("tp").sum()
    fn = df.get("fn").sum()
    fp = df.get("fp").sum()
    precision = tp / (tp+fp) if tp+fp>0 else 0
    recall = tp / (tp+fn) if tp+fn>0 else 0
    med_free_notes = df[df["actual"] == 0]
    invented_med_free_notes = med_free_notes.get("pred").sum()

    res = {
        "version":                  ver,
        "num_notes":                len(df),
        "actual_meds":              int(df["actual"].sum()),
        "precision":                round(precision, 3),
        "recall":                   round(recall, 3),
        "med_free_notes":           len(med_free_notes),
        "invented_med_free_notes":  invented_med_free_notes,
    }

    for f in FIELDS + ["frequency_noroute"]:
        res[f"{f}_accuracy"] = round(df[f"{f}_correct"].sum() / tp, 3) if tp > 0 else 0

    return res

if __name__ == "__main__":
    RESULTS.mkdir(exist_ok=True)
    summaries = []
    for version in ["v3", "v4"]:
        df = evaluate(OUTPUTS / f"test_{version}_openai_gpt-oss-120b")
        df.to_csv(RESULTS / f"eval_{version}_per_note.csv", index=False)
        summaries.append(summarize(df, version))
    summary = pd.DataFrame(summaries)
    summary.to_csv(RESULTS / "eval_summary.csv", index=False)
    print(summary.T.to_string())
