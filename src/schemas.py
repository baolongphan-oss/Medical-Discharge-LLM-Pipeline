# Stage 1: Extraction
# In src/schemas.py, write the Pydantic models: Medication (name, dose, frequency, status) and DischargeExtraction.
from pydantic import BaseModel
from typing import Literal

# Define your data schema
class Medication(BaseModel):
    name: str
    dose: str | None=None
    frequency: str | None=None
    status: Literal["new", "changed", "continued", "stopped", "unknown"] = "unknown"

class DischargeExtraction(BaseModel):
    final_diagnoses: list[str]
    # history_of_present_illnesses: list[str]
    medications: list[Medication]
    procedures: list[str]
    # hospital_course: list[str]
    follow_up: list[str]

# inspect the json schema
# import json
# print(json.dumps(DischargeExtraction.model_json_schema(), indent=2))

# Stage 2: Patient translation (Oct 12–13)
# In prompts/translate_v1.txt and src/translate.py, take the note plus the extracted medications and write 5th-grade instructions with a "Call your doctor if…" section.
# Score readability with the textstat package (Flesch-Kincaid grade).
# Add the dose safety check: every dose from the extraction must appear unchanged in the patient version. Flag any that don't.
# Done when: the 10 dev notes each produce a patient version, a grade level, and a pass/fail flag.