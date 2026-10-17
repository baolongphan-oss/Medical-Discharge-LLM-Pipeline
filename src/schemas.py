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
