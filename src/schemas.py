# Stage 1: Extraction (Oct 11–12)
# In src/schemas.py, write the Pydantic models: Medication (name, dose, frequency, status) and DischargeExtraction.
# Write prompts/extract_v1.txt.
# In src/extract.py, load a note, call the API, validate with Pydantic, and save the result to outputs/.
# Add a short pause and retry between calls; the free tier allows 30 requests per minute.
# Done when: it runs on all 10 dev notes and reports how many passed validation.
# Stage 2: Patient translation (Oct 12–13)
# In prompts/translate_v1.txt and src/translate.py, take the note plus the extracted medications and write 5th-grade instructions with a "Call your doctor if…" section.
# Score readability with the textstat package (Flesch-Kincaid grade).
# Add the dose safety check: every dose from the extraction must appear unchanged in the patient version. Flag any that don't.
# Done when: the 10 dev notes each produce a patient version, a grade level, and a pass/fail flag.