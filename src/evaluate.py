# Stage 3: Evaluation
# Compare frozen prompt versions on the hand-labeled test notes (labels/note_*.json).
# Metrics: medication precision/recall (micro-averaged), dose/frequency/duration/status
# accuracy on matched pairs, invented meds on med-free notes.
# Unsupported instructions and citation checks come from the manual audit (docs/failure_log.md).
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

LABELS = Path("labels")
OUTPUTS = Path("outputs")
RESULTS = Path("results")
FIELDS = ["dose", "frequency", "duration", "status"]


def key(text):
    # same idea as translate.heading_key: lowercase, letters and digits only. None stays None.
    if text is None:
        return None
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[^a-z0-9]", "", text)


ROUTE = re.compile(r"\b(p\.?o\.?|by mouth|orally|subcu|subq|s\.?c\.?|sq|i\.?v\.?|i\.?m\.?|inhaled|topically)(?=\s|$)")


def freq_key(text):
    # labels keep the route ("p.o. daily"); the schema has no route field, so compare without it
    if text is None:
        return None
    return key(ROUTE.sub(" ", text.lower())) or None


FORM = re.compile(r"\b(nebulizers?|neb|inhalers?|tablets?|tabs?|capsules?|patch|nasal spray|spray|cream|ointment|respules|solution|injection)\b")


def name_key(text):
    # dosage form isn't a schema field; models (and some labels) put it in the name
    return key(FORM.sub(" ", text.lower()))


def load_meds(path):
    if not path.exists():
        return []  # no prediction file = model extracted nothing
    return json.loads(path.read_text()).get("medications", [])


def match_meds(gold, pred):
    # one-to-one matching. Pass 1: name + dose. Pass 2: name only, first unmatched gold.
    pairs, used_g, used_p = [], set(), set()
    for exact_dose in (True, False):
        for pi, p in enumerate(pred):
            if pi in used_p:
                continue
            for gi, g in enumerate(gold):
                if gi in used_g or name_key(g["name"]) != name_key(p["name"]):
                    continue
                if exact_dose and key(g.get("dose")) != key(p.get("dose")):
                    continue
                pairs.append((g, p))
                used_g.add(gi)
                used_p.add(pi)
                break
    return pairs, len(gold) - len(used_g), len(pred) - len(used_p)


def score_note(gold, pred):
    pairs, fn, fp = match_meds(gold, pred)
    row = {"gold": len(gold), "pred": len(pred), "tp": len(pairs), "fn": fn, "fp": fp}
    for f in FIELDS:
        row[f"{f}_correct"] = sum(key(g.get(f)) == key(p.get(f)) for g, p in pairs)
    row["frequency_noroute_correct"] = sum(freq_key(g.get("frequency")) == freq_key(p.get("frequency")) for g, p in pairs)
    return row


def evaluate(pred_dir):
    rows = []
    for label_path in sorted(LABELS.glob("note_*.json")):
        gold = json.loads(label_path.read_text())["medications"]
        pred = load_meds(pred_dir / label_path.name)
        rows.append({"note_id": int(label_path.stem.split("_")[1]), **score_note(gold, pred)})
    return pd.DataFrame(rows)


def summarize(df, version):
    tp, fn, fp = df.tp.sum(), df.fn.sum(), df.fp.sum()
    med_free = df[df.gold == 0]
    out = {
        "version": version,
        "notes": len(df),
        "gold_meds": int(df.gold.sum()),
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "med_free_notes": len(med_free),
        "invented_on_med_free": int(med_free.pred.sum()),
    }
    for f in FIELDS + ["frequency_noroute"]:
        out[f"{f}_acc"] = round(df[f"{f}_correct"].sum() / tp, 3) if tp else None
    return out


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
