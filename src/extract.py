# Write prompts/extract_v1.txt.
# In src/extract.py, load a note, call the API, validate with Pydantic, and save the result to outputs/.
# Add a short pause and retry between calls; the free tier allows 30 requests per minute.
# Done when: it runs on all 10 dev notes and reports how many passed validation.
import pandas as pd
import json
import os
from schemas import DischargeExtraction
from openai import OpenAI
from pathlib import Path 
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
data = ROOT / "data" / "dev.csv"
load_dotenv(ROOT / ".env")

dev_df = pd.read_csv(data)
sample_note = dev_df.iloc[3]["transcription"]

schema_text = json.dumps(DischargeExtraction.model_json_schema(), indent=2)
prompt_template = (ROOT / "prompts" / "extract_v1.txt").read_text()
system_prompt = prompt_template.replace("{schema}", schema_text)

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY") 
)

completion = client.chat.completions.create(
    model=os.environ.get("LLM_MODEL"),
    messages=[
         {"role": "system", "content": system_prompt},
        {"role": "user", "content": sample_note}
    ]
)

print(completion.choices[0].message.content)


# """
# "HISTORY OF PRESENT ILLNESS:  ,A 67-year-old male with COPD and history of bronchospasm, who presents with a 3-day history of increased cough, respiratory secretions, wheezings, and shortness of breath.  He was seen by me in the office on the day of admission and noted to be dyspneic with audible wheezing and he was admitted for acute asthmatic bronchitis, superimposed upon longstanding COPD.  Unfortunately over the past few months he has returned to pipe smoking.  At the time of admission, he denied fever, diaphoresis, nausea, chest pain or other systemic symptoms.,PAST MEDICAL HISTORY: , Status post artificial aortic valve implantation in summer of 2002 and is on chronic Coumadin therapy.  COPD as described above, history of hypertension, and history of elevated cholesterol.,PHYSICAL EXAMINATION: , Heart tones regular with an easily audible mechanical click.  Breath sounds are greatly diminished with rales and rhonchi over all lung fields.,LABORATORY STUDIES:  ,Sodium 139, potassium 4.5, BUN 42, and creatinine 1.7.  Hemoglobin 10.7 and hematocrit 31.7.,HOSPITAL COURSE: , He was started on intravenous antibiotics, vigorous respiratory therapy, intravenous Solu-Medrol.  The patient improved on this regimen.  Chest x-ray did not show any CHF.  The cortisone was tapered.  The patient's oxygenation improved and he was able to be discharged home.,DISCHARGE DIAGNOSES:  ,Chronic obstructive pulmonary disease and acute asthmatic bronchitis.,COMPLICATIONS: , None.,DISCHARGE CONDITION: , Guarded.,DISCHARGE PLAN: , Prednisone 20 mg 3 times a day for 2 days, 2 times a day for 5 days and then one daily, Keflex 500 mg 3 times a day and to resume his other preadmission medication, can be given a pneumococcal vaccination before discharge.  To follow up with me in the office in 4-5 days.
# """