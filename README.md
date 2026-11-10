# Medical Discharge LLM Pipeline

Turns hospital discharge summaries into (1) a structured extraction (diagnoses, medications, procedures, follow-up) and (2) plain-language patient instructions. Python, OpenAI SDK on Groq (`openai/gpt-oss-120b`), Pydantic, pandas, textstat, pytest.

## Results (test set)
24 MTSamples discharge summaries, hand-labeled for medications (91 meds; 8 notes have none). Prompts were frozen (`prompts-frozen-v4`) before the test set was run. Reproduce with `python -m src.evaluate`; see `results/`.

**Medication extraction**

| Metric | v3 | v4 |
|---|---|---|
| Precision | 0.90 | 0.90 |
| Recall | 0.89 | 0.90 |
| Dose accuracy* | 0.95 | 0.94 |
| Frequency accuracy* | 0.83 | 0.84 |
| Duration accuracy* | 0.91 | 0.89 |
| Status accuracy* | 0.85 | 0.82 |
| Meds extracted on med-free notes | 3 | 5 |

\*On matched medications. Micro-averaged over all notes.

**Patient instructions**

| Metric | v3 | v4 |
|---|---|---|
| Notes translated | 24/24 | 24/24 |
| Dose check passed | 23/24** | 24/24 |
| Mean reading grade (Flesch-Kincaid) | 6.4 | 5.4 |
| Citations quoted exactly | — | 113/118 (5 paraphrased, 0 fabricated) |

\*\*The one failure is a checker false positive (see `docs/failure_log.md`).

**Takeaway:** v3 and v4 extract medications equally well; the differences are within noise for 24 notes. v4's gain is in the patient instructions: one grade level easier to read, every dose carried through.

## Limitations
- Small test set (24 notes) from one public source (MTSamples); not real EHR data.
- Ground truth covers medications only, labeled by one person (no inter-rater agreement). Rules: `docs/labeling_guide.md`.
- Name matching is exact after normalization: brand vs generic (Lasix / furosemide) counts as a miss.
- Route and dosage-form words are removed before comparing frequencies and names, because the schema has no fields for them.
- Unsupported-instruction and citation checks were manual.
- Not clinically validated; not for patient use.

## Roadmap
Ideas parked here instead of built now (prompts are frozen at `prompts-frozen-v4`).

- Add `form` and `route` fields to the schema; today they leak into `name` and `frequency`, and the evaluator strips them.
- Looser medication name matching (brand vs generic, e.g. Lasix / furosemide).
- Fuzzy citation matching for paraphrased quotes (5/118 near-misses in v4).
- Dose-leak check: require a digit or unit, so words like "one" don't trigger false positives.
- Filter notes by content, not MTSamples category title (note 2210 was an admission note).
- LangChain refactor and a minimal LangGraph with a safety review step.
- Minimal RAG: ICD-10 code suggestions with a top-5 hit rate.
