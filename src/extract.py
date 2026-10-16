# Write prompts/extract_v1.txt.
# In src/extract.py, load a note, call the API, validate with Pydantic, and save the result to outputs/.
# Add a short pause and retry between calls; the free tier allows 30 requests per minute.
# Done when: it runs on all 10 dev notes and reports how many passed validation.
import pandas as pd
import time, json, os
from schemas import DischargeExtraction
from pydantic import ValidationError
from openai import OpenAI
from pathlib import Path 
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
data = ROOT / "data" / "dev.csv"
load_dotenv(ROOT / ".env")

model_name = os.environ.get("LLM_MODEL")
llm_dir_name = f"v1_{model_name.replace('/', '_')}"

out_dir = ROOT / "outputs" / llm_dir_name
out_dir.mkdir(parents=True, exist_ok=True)

dev_df = pd.read_csv(data)
sample_notes = dev_df["transcription"]

schema_text = json.dumps(DischargeExtraction.model_json_schema(), indent=2)
prompt_template = (ROOT / "prompts" / "extract_v1.txt").read_text()
system_prompt = prompt_template.replace("{schema}", schema_text)

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

passes = 0
fail_records = []

for idx, note in enumerate(sample_notes):
    try:
        completion = client.chat.completions.create(
            model=model_name,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": note}
            ]
        )
        extraction = completion.choices[0].message.content
        validated = DischargeExtraction.model_validate_json(extraction)
        print(f"Valid format for note_{idx+1:02d}!")
        passes += 1
        with open(out_dir / f"note_{idx+1:02d}.json", "w", encoding="utf-8") as f:
            f.write(validated.model_dump_json(indent=4))
    except ValidationError as e:
        fail_records.append({"note": idx+1, "error": str(e), "raw": extraction})
        print(e.json(indent=2))
    except Exception as e:
        fail_records.append({"note": idx+1, "error": str(e)})
        print(e)
    time.sleep(3)

print(f"Validation passes: {passes}/{len(sample_notes)}")
print(fail_records)