# Write prompts/extract_{prompt_ver}.txt.
# In src/extract.py, load a note, call the API, validate with Pydantic, and save the result to outputs/.
# Add a short pause and retry between calls; the free tier allows 30 requests per minute.
# Done when: it runs on all 10 dev notes and reports how many passed validation.
import pandas as pd
import time, json
from schemas import DischargeExtraction
from llm import call_with_retry
from pydantic import ValidationError
from pathlib import Path 

def run_extraction(prompt_ver, model_name, split="dev"):
    ROOT = Path(__file__).resolve().parent.parent
    data = ROOT / "data" / f"{split}.csv"
    llm_dir_name = f"{split}_{prompt_ver}_{model_name.replace('/', '_')}"

    out_dir = ROOT / "outputs" / llm_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    notes_df = pd.read_csv(data)

    schema_text = json.dumps(DischargeExtraction.model_json_schema(), indent=2)
    prompt_template = (ROOT / "prompts" / f"extract_{prompt_ver}.txt").read_text()
    system_prompt = prompt_template.replace("{schema}", schema_text)

    passes = 0
    fail_records = []

    for note_id, note in zip(notes_df["note_id"], notes_df["transcription"]):
        extraction = None  # stays None if the failure happens before the API returns
        try:
            completion = call_with_retry([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": note}
                ], model_name, json_mode=True)
            extraction = completion.choices[0].message.content
            validated = DischargeExtraction.model_validate_json(extraction)
            print(f"[extract] note_{note_id}: PASS - saved to {out_dir.name}/note_{note_id}.json")
            passes += 1
            with open(out_dir / f"note_{note_id}.json", "w", encoding="utf-8") as f:
                f.write(validated.model_dump_json(indent=4))
        except ValidationError as e:
            fail_records.append({"note": note_id, "error": str(e), "raw": extraction})
            print(f"[extract] note_{note_id}: FAIL - schema validation error:\n{e.json(indent=2)}")
        except Exception as e:
            fail_records.append({"note": note_id, "error": str(e)})
            print(f"[extract] note_{note_id}: FAIL - {type(e).__name__}: {e}")
        time.sleep(5)

    print(f"[extract] Done ({prompt_ver}, {model_name}): {passes}/{len(notes_df)} {split} notes passed validation")
    print(f"[extract] Failures: {fail_records if fail_records else 'none'}")
    print(f"[extract] Stage 1 complete. Extractions saved to {out_dir}")
    return passes, len(notes_df)
