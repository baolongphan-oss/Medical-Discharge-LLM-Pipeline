# Stage 2: Patient translation
# In prompts/translate_v1.txt and src/translate.py, take the note plus the extracted medications and write 5th-grade instructions with a "Call your doctor if…" section.
# Score readability with the textstat package (Flesch-Kincaid grade).
# Add the dose safety check: every dose from the extraction must appear unchanged in the patient version. Flag any that don't.
# Done when: the 10 dev notes each produce a patient version, a grade level, and a pass/fail flag.

import pandas as pd
from pydantic import ValidationError
from pathlib import Path
import time, json, re, textstat
from schemas import DischargeExtraction
from llm import call_with_retry

# check if there are any missing doses from the llm response
def dose_check(meds, patient_text):
    missing = []
    text = patient_text.lower()
    for med in meds:
        if med.dose and med.dose.lower() not in text:
            missing.append(f"{med.name}: {med.dose}")
    return missing

def run_translation(extract_ver, translate_ver, model_name):
    ROOT = Path(__file__).resolve().parent.parent
    translate_dir_name = f"translate_{translate_ver}_{model_name.replace('/', '_')}"

    out_dir = ROOT / "outputs" / translate_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    data = ROOT / "data" / "dev.csv"
    dev_df = pd.read_csv(data)
    transcriptions = dev_df["transcription"]

    notes_path = Path(ROOT / "outputs" / f"{extract_ver}_{model_name.replace('/', '_')}")
    note_files = sorted([f.name for f in notes_path.iterdir() if f.is_file() and re.match(r'^note_(\d{2})\.json$', f.name)])
    # print(note_files)

    prompt = (ROOT / "prompts" / f"translate_{translate_ver}.txt").read_text()

    passes = 0
    fail_records = []
    results = []

    for f_name in note_files:
        note_num = int(re.match(r"^note_(\d{2})\.json$", f_name).group(1))
        try:
            # get the summary extraction and original transcription
            summary = DischargeExtraction.model_validate_json((notes_path / f_name).read_text())
            original_transcription = transcriptions.iloc[note_num - 1]
            # Build the user message: the note + the medication list
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

            # Score readability and run the dose check
            grade = textstat.flesch_kincaid_grade(patient_text)
            missing_doses = dose_check(summary.medications, patient_text)

            passes += 1
            results.append({
                "note": note_num,
                "grade": grade,
                "dose_check": "PASS" if not missing_doses else "FAIL",
                "missing_doses": "; ".join(missing_doses),
            })
            print(f"[translate] note_{note_num:02d}: DONE - grade {grade:.1f}, dose check {'PASS' if not missing_doses else 'FAIL (' + '; '.join(missing_doses) + ')'}")
            # Save the patient text to outputs/translate_v1_<model>/note_XX.txt
            with open(out_dir / f"note_{note_num:02d}.txt", "w", encoding="utf-8") as f:
                f.write(patient_text)

        except ValidationError as e:
            fail_records.append({"note": note_num, "error": str(e)})
            print(f"[translate] note_{note_num:02d}: FAIL - could not load extraction {f_name}:\n{e}")
        except Exception as e:
            fail_records.append({"note": note_num, "error": str(e)})
            print(f"[translate] note_{note_num:02d}: FAIL - {type(e).__name__}: {e}")
        time.sleep(15)

    print(f"[translate] Done ({translate_ver}, extraction {extract_ver}, {model_name}): {passes}/{len(note_files)} notes translated")
    print(f"[translate] Failures: {fail_records if fail_records else 'none'}")
    # See note number, grade level, dose check pass/fail
    pd.DataFrame(results).to_csv(out_dir / "summary.csv", index=False)
    print(f"[translate] Stage 2 complete. Patient texts and summary.csv saved to {out_dir}")
