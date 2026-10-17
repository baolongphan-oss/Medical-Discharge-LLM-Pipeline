# Stage 2: Patient translation
# In prompts/translate_v1.txt and src/translate.py, take the note plus the extracted medications and write 5th-grade instructions with a "Call your doctor if…" section.
# Score readability with the textstat package (Flesch-Kincaid grade).
# Add the dose safety check: every dose from the extraction must appear unchanged in the patient version. Flag any that don't.
# Done when: the 10 dev notes each produce a patient version, a grade level, and a pass/fail flag.
import pandas as pd
from pydantic import ValidationError
from pathlib import Path
import os, time, json, re
from extract import DischargeExtraction
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

model_name = os.environ.get("LLM_MODEL")
llm_dir_name = f"v1_{model_name.replace('/', '_')}"

translate_dir_name = f"translate_v1_{model_name}"
out_dir = ROOT / "outputs" / translate_dir_name
out_dir.mkdir(parents=True, exist_ok=True)

data = ROOT / "data" / "dev.csv"
dev_df = pd.read_csv(data)
transcriptions = dev_df["transcriptions"]

notes_path = Path(ROOT / "outputs" / llm_dir_name)
note_files = sorted([f.name for f in notes_path.iterdir() if f.is_file() and re.match(f, r'^note_(\d{2}).json')])
print(note_files)

schema_text = json.dumps(DischargeExtraction.model_json_schema(), indent=2)
prompt = (ROOT / "prompts" / "translate_v1.txt").read_text()

# client = OpenAI(
#     base_url="https://api.groq.com/openai/v1",
#     api_key=os.environ.get("GROQ_API_KEY")
# )

passes = 0
fail_records = []

# for idx, f_name in enumerate(files):
#     with open(f_name, 'r', encoding='utf-8') as file:
#         summary = json.load(file)['raw']
#         original_transcription = transcriptions.iloc[idx]
#         try:
#             summary = DischargeExtraction.model_validate_json(summary)

#             user_msg = f"""
#             DISCHARGE SUMMARY:
#             {original_transcription}

#             MEDICATION LIST (copy doses exactly):
#             {json.dumps([med.model_dump() for med in summary.medications])}
#             """

#             completion = client.chat.completions.create(
#                 model=model_name,
#                 temperature=0,
#                 response_format={"type": "json_object"},
#                 messages=[
#                     {"role": "system", "content": prompt},
#                     {"role": "user", "content": user_msg}
#                 ]
#             )
#             extraction = completion.choices[0].message.content
#             passes += 1
#             with open(out_dir / f"note_{idx+1:02d}.json", "w", encoding="utf-8") as f:
#                 f.write(extraction)
#         except ValidationError as e:
#             fail_records.append({"note": idx+1, "error": str(e), "raw": extraction})
#             print(e)
#         except Exception as e:
#             fail_records.append({"note": idx+1, "error": str(e)})
#             print(e)
#     time.sleep(3)

print(f"Validation passes: {passes}/{len(note_files)}")
print(fail_records)

# For each dev note:
#   1. Load the note text and its saved extraction JSON from outputs/
#      (DischargeExtraction.model_validate_json(path.read_text()))
#   2. Build the user message: the note + the medication list
#      (validated.model_dump_json() for the meds)
#   3. Call the API with translate_v1.txt as the system prompt.
#      No response_format here: the output is plain text, not JSON.
#   4. Score readability: textstat.flesch_kincaid_grade(text)
#   5. Run the dose check (below)
#   6. Save the patient text to outputs/translate_v1_<model>/note_XX.txt
#   7. Print: note number, grade level, dose check pass/fail
