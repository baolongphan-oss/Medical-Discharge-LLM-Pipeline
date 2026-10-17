# Stage 2: Patient translation
# In prompts/translate_v1.txt and src/translate.py, take the note plus the extracted medications and write 5th-grade instructions with a "Call your doctor if…" section.
# Score readability with the textstat package (Flesch-Kincaid grade).
# Add the dose safety check: every dose from the extraction must appear unchanged in the patient version. Flag any that don't.
# Done when: the 10 dev notes each produce a patient version, a grade level, and a pass/fail flag.
# v3: the LLM writes no medicines; the medicine table is built in code (med_table.py) and inserted after section 1.

import pandas as pd
from pydantic import ValidationError
from pathlib import Path
import time, json, re, textstat, unicodedata
from schemas import DischargeExtraction
from llm import call_with_retry
from med_table import render_med_table

NOTE_FILE = re.compile(r"^note_(\d+)\.json$")
# headings that can start section 2 onward, in prompt order (section 3 may be missing)
LATER_HEADINGS = re.compile(r"follow-up appointments|other things to do|call your doctor or go to the er", re.IGNORECASE)

# NFKC turns look-alike characters (e.g. U+202F narrow no-break space) into plain ones,
# then whitespace is collapsed so "20 mg" and "20  mg" both compare as "20 mg"
def normalize(text):
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip().lower()

# check if there are any missing doses from the llm response (v1/v2)
def dose_check(meds, patient_text):
    text = normalize(patient_text)
    return [f"{med.name}: {med.dose}" for med in meds if med.dose and normalize(med.dose) not in text]

# v3: the narrative should contain no doses at all, so flag any extracted dose that shows up
def leaked_doses(meds, narrative):
    text = normalize(narrative)
    return [f"{med.name}: {med.dose}" for med in meds if med.dose and normalize(med.dose) in text]

# v3: flag ANY dose-like text in the narrative (a number followed by a dose unit), even if it isn't in the extraction
# DOSE_PATTERN matches a number, which can be a decimal, followed by mg, mcg, g, mL, mEq, unit(s), tablet(s) or puff(s). 
# It ignores case and runs after NFKC normalization.
# For example: 2 tablets, 40 mg, 1.5 ml and 5 puffs
# regex: start with word (\b), then one or more digits (\d+), then decimal points if present ((?:\.\d+)?), 
# zero or more spaces, pick one unit from the list, and add a word boundary (i.e. the unit ends the word with \b)

DOSE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|meq|units?|tablets?|puffs?|grams?|milligrams?)\b", re.IGNORECASE)

def narrative_dose_leaks(narrative):
    return DOSE_PATTERN.findall(normalize(narrative))

# v3: put the medicine table after section 1 (before the first later-section heading)
def build_v3_document(narrative, med_table):
    lines = narrative.split("\n")
    for i, line in enumerate(lines):
        if i > 0 and LATER_HEADINGS.search(line):
            before, after = "\n".join(lines[:i]).rstrip(), "\n".join(lines[i:]).lstrip()
            return f"{before}\n\n## Your medicines\n\n{med_table}\n\n{after}\n"
    # no later heading found: add the table at the end
    return f"{narrative.rstrip()}\n\n## Your medicines\n\n{med_table}\n"

def run_translation(extract_ver, translate_ver, model_name, split="dev"):
    ROOT = Path(__file__).resolve().parent.parent
    model_dir = model_name.replace('/', '_')
    is_v3 = translate_ver == "v3"

    out_dir = ROOT / "outputs" / f"{split}_translate_{translate_ver}_{model_dir}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # look up each note's text by its stable note_id, never by position
    notes_df = pd.read_csv(ROOT / "data" / f"{split}.csv")
    transcriptions = dict(zip(notes_df["note_id"], notes_df["transcription"]))

    notes_path = ROOT / "outputs" / f"{split}_{extract_ver}_{model_dir}"
    note_files = sorted(f.name for f in notes_path.iterdir() if f.is_file() and NOTE_FILE.match(f.name))

    prompt = (ROOT / "prompts" / f"translate_{translate_ver}.txt").read_text()

    passes = 0
    fail_records = []
    results = []

    for f_name in note_files:
        note_id = int(NOTE_FILE.match(f_name).group(1))
        try:
            if note_id not in transcriptions:
                raise KeyError(f"note_id {note_id} is not in {split}.csv")

            # get the summary extraction and original transcription
            summary = DischargeExtraction.model_validate_json((notes_path / f_name).read_text())
            original_transcription = transcriptions[note_id]

            # Build the user message: v3 sends only the note; v1/v2 also send the medication list
            if is_v3:
                user_msg = f"DISCHARGE SUMMARY:\n{original_transcription}"
            else:
                user_msg = f"""DISCHARGE SUMMARY:
{original_transcription}

MEDICATION LIST (copy doses exactly):
{json.dumps([med.model_dump() for med in summary.medications])}"""

            # call the API to process the user message
            completion = call_with_retry([
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg}
                ], model_name)
            patient_text = completion.choices[0].message.content

            # Score readability and run the dose check on the LLM text only (never the v3 table)
            grade = textstat.flesch_kincaid_grade(patient_text)
            if is_v3:
                flagged = leaked_doses(summary.medications, patient_text)
                pattern_leaks = narrative_dose_leaks(patient_text)
                document = build_v3_document(patient_text, render_med_table(summary.medications))
                out_file = f"note_{note_id}.md"
            else:
                flagged = dose_check(summary.medications, patient_text)
                pattern_leaks = []
                document = patient_text
                out_file = f"note_{note_id}.txt"

            passes += 1
            dose_ok = not flagged and not pattern_leaks
            results.append({
                "note_id": note_id,
                "grade": grade,
                "dose_check": "PASS" if dose_ok else "FAIL",
                "missing_doses": "; ".join(flagged),  # v3: extraction doses that leaked into the narrative
                "narrative_dose_leaks": "; ".join(pattern_leaks),  # v3 only: any dose-like text in the narrative
                "n_medications": len(summary.medications),
            })
            label = "extraction doses in narrative" if is_v3 else "missing"
            problems = []
            if flagged:
                problems.append(f"{label}: " + "; ".join(flagged))
            if pattern_leaks:
                problems.append("dose-like text in narrative: " + "; ".join(pattern_leaks))
            print(f"[translate] note_{note_id}: DONE - grade {grade:.1f}, dose check {'PASS' if dose_ok else 'FAIL (' + ' | '.join(problems) + ')'}")
            with open(out_dir / out_file, "w", encoding="utf-8") as f:
                f.write(document)

        except ValidationError as e:
            fail_records.append({"note": note_id, "error": str(e)})
            print(f"[translate] note_{note_id}: FAIL - could not load extraction {f_name}:\n{e}")
        except Exception as e:
            fail_records.append({"note": note_id, "error": str(e)})
            print(f"[translate] note_{note_id}: FAIL - {type(e).__name__}: {e}")
        time.sleep(15)

    print(f"[translate] Done ({split}, {translate_ver}, extraction {extract_ver}, {model_name}): {passes}/{len(note_files)} notes translated")
    print(f"[translate] Failures: {fail_records if fail_records else 'none'}")
    # See note id, grade level, dose check pass/fail
    summary_df = pd.DataFrame(results, columns=["note_id", "grade", "dose_check", "missing_doses", "narrative_dose_leaks", "n_medications"])
    summary_df.to_csv(out_dir / "summary.csv", index=False)
    print(f"[translate] Stage 2 complete. Patient texts and summary.csv saved to {out_dir}")

    return {
        "translated": passes,
        "total": len(note_files),
        "dose_check_pass": int((summary_df["dose_check"] == "PASS").sum()),
        "mean_grade": round(summary_df["grade"].mean(), 1) if len(summary_df) else None,
    }
