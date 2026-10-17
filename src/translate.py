# Stage 2: Patient translation
# In prompts/translate_v1.txt and src/translate.py, take the note plus the extracted medications and write 5th-grade instructions with a "Call your doctor if…" section.
# Score readability with the textstat package (Flesch-Kincaid grade).
# Add the dose safety check: every dose from the extraction must appear unchanged in the patient version. Flag any that don't.
# Done when: the 10 dev notes each produce a patient version, a grade level, and a pass/fail flag.
# v3: the LLM writes no medicines; the medicine table is built in code (med_table.py) and inserted after section 1.
# v4: the LLM cites the note as [[SOURCE: ...]]; citations are verified, kept in an audit file, and stripped before checks.

import pandas as pd
from pydantic import ValidationError
from pathlib import Path
import time, json, re, textstat, unicodedata
from schemas import DischargeExtraction
from llm import call_with_retry
from med_table import render_med_table

NOTE_FILE = re.compile(r"^note_(\d+)\.json$")
# headings that can start section 2 onward, as simplified keys (see heading_key); section 3 may be missing
LATER_HEADING_KEYS = ["yourfollowupappointments", "otherthingstodo", "callyourdoctororgototheer"]
CITATION = re.compile(r"\[\[SOURCE:\s*(.*?)\]\]", re.DOTALL)

# "v4" -> 4
def version_num(ver):
    return int(re.sub(r"\D", "", ver))

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
# leaked_doses vs narrative_dose_leaks (v3+ runs both; either finding = FAIL):
# - leaked_doses: searches for THIS note's extracted doses -> ["Lasix: 40 mg"] (knows which medicine)
#   misses doses that aren't in the extraction
# - narrative_dose_leaks: searches for ANY number + unit (DOSE_PATTERN) -> ["40 mg", "81 mg"]
#   catches made-up or missed doses, but doesn't know the medicine and misses unitless ones ("take 2 a day")
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

# letters and digits only, so "## Your follow\u2011up appointments" and "Your follow-up appointments"
# give the same key (NFKC alone turns U+2011 into U+2010, which still isn't a plain hyphen)
def heading_key(line):
    return re.sub(r"[^a-z0-9]", "", normalize(line))

# v3+: put the medicine table after section 1 (before the first later-section heading)
def build_v3_document(narrative, med_table):
    lines = narrative.split("\n")
    for i, line in enumerate(lines):
        # skip line 0 (section 1's own heading); only Markdown "#" lines count as headings,
        # and the line's simplified key must start with a section 2-4 key
        if i > 0 and line.lstrip().startswith("#") and heading_key(line).startswith(tuple(LATER_HEADING_KEYS)):
            before, after = "\n".join(lines[:i]).rstrip(), "\n".join(lines[i:]).lstrip()
            return f"{before}\n\n## Your medicines\n\n{med_table}\n\n{after}\n"
    # no later heading found: add the table at the end
    return f"{narrative.rstrip()}\n\n## Your medicines\n\n{med_table}\n"

# for comparing quotes: like normalize, but punctuation becomes a space
# 1. normalize: NFKC, lowercase, collapse whitespace
# 2. [^\w\s] = any character that is not a letter/digit/underscore or whitespace -> replace with " "
#    (so "follow-up," and "follow up" both become "follow up")
# 3. collapse the extra spaces that step 2 created
# e.g. "Activity as  tolerated!" -> "activity as tolerated"
def quote_key(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", normalize(text))).strip()

# v4+: return (all quotes, quotes not found in the note)
# basically, check_citations chekcs if the exact words in the raw text appears in the note

# CITATION.findall returns only the text inside each [[SOURCE: ...]] (the regex's capture group).
# A quote is verified if its key appears anywhere inside the note's key (a substring match),
# so the model must copy a continuous run of words; changing or reordering words makes it unverified.
def check_citations(raw_text, note):
    quotes = [q.strip() for q in CITATION.findall(raw_text)]
    note_key = quote_key(note)  # computed once, reused for every quote
    unverified = [q for q in quotes if quote_key(q) not in note_key]
    return quotes, unverified

# v4+: remove every citation (and the space before it) to get the patient-facing text
# [ \t]*      spaces/tabs before the citation, so "Rest. [[SOURCE: ...]]" becomes "Rest." with no trailing space
# \[\[SOURCE: the literal opening "[[SOURCE:" (brackets are escaped because [ ] mean something in regex)
# .*?         the quote itself; "?" makes it lazy, so it stops at the FIRST "]]" instead of
#             swallowing everything up to the last citation on the line
# \]\]        the literal closing "]]"
# re.DOTALL   lets "." match newlines too, in case a quote spans more than one line
def strip_citations(raw_text):
    return re.sub(r"[ \t]*\[\[SOURCE:.*?\]\]", "", raw_text, flags=re.DOTALL)

def run_translation(extract_ver, translate_ver, model_name, split="dev"):
    ROOT = Path(__file__).resolve().parent.parent
    model_dir = model_name.replace('/', '_')
    is_v3_plus = version_num(translate_ver) >= 3  # v3+: code-built medicine table
    has_citations = version_num(translate_ver) >= 4  # v4+: [[SOURCE: ...]] citations

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

            # Build the user message: v3+ sends only the note; v1/v2 also send the medication list
            if is_v3_plus:
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

            # v4+: verify citations, keep the raw output for auditing, then strip citations
            # so every check below runs on the clean narrative only
            quotes, unverified = [], []
            if has_citations:
                quotes, unverified = check_citations(patient_text, original_transcription)
                with open(out_dir / f"note_{note_id}_audit.md", "w", encoding="utf-8") as f:
                    f.write(patient_text)
                patient_text = strip_citations(patient_text)

            # Score readability and run the dose check on the LLM text only (never the v3 table)
            grade = textstat.flesch_kincaid_grade(patient_text)
            if is_v3_plus:
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
            row = {
                "note_id": note_id,
                "grade": grade,
                "dose_check": "PASS" if dose_ok else "FAIL",
                "missing_doses": "; ".join(flagged),  # v3+: extraction doses that leaked into the narrative
                "narrative_dose_leaks": "; ".join(pattern_leaks),  # v3+ only: any dose-like text in the narrative
                "n_medications": len(summary.medications),
            }
            if has_citations:
                row["n_citations"] = len(quotes)
                row["unverified_citations"] = len(unverified)
                row["unverified_quotes"] = "; ".join(unverified)
            results.append(row)
            label = "extraction doses in narrative" if is_v3_plus else "missing"
            problems = []
            if flagged:
                problems.append(f"{label}: " + "; ".join(flagged))
            if pattern_leaks:
                problems.append("dose-like text in narrative: " + "; ".join(pattern_leaks))
            cite_msg = f", citations {len(quotes) - len(unverified)}/{len(quotes)} verified" if has_citations else ""
            print(f"[translate] note_{note_id}: DONE - grade {grade:.1f}, dose check {'PASS' if dose_ok else 'FAIL (' + ' | '.join(problems) + ')'}{cite_msg}")
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
    columns = ["note_id", "grade", "dose_check", "missing_doses", "narrative_dose_leaks", "n_medications"]
    if has_citations:
        columns += ["n_citations", "unverified_citations", "unverified_quotes"]
    summary_df = pd.DataFrame(results, columns=columns)
    summary_df.to_csv(out_dir / "summary.csv", index=False)
    print(f"[translate] Stage 2 complete. Patient texts and summary.csv saved to {out_dir}")

    return {
        "translated": passes,
        "total": len(note_files),
        "dose_check_pass": int((summary_df["dose_check"] == "PASS").sum()),
        "mean_grade": round(summary_df["grade"].mean(), 1) if len(summary_df) else None,
    }
