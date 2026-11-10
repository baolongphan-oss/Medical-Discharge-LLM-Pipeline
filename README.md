# Medical Discharge LLM Pipeline

## Roadmap
Ideas parked here instead of built now (prompts are frozen at `prompts-frozen-v4`).

- Add `form` and `route` fields to the schema; today they leak into `name` and `frequency`, and the evaluator strips them.
- Looser medication name matching (brand vs generic, e.g. Lasix / furosemide).
- Fuzzy citation matching for paraphrased quotes (5/118 near-misses in v4).
- Dose-leak check: require a digit or unit, so words like "one" don't trigger false positives.
- Filter notes by content, not MTSamples category title (note 2210 was an admission note).
- LangChain refactor and a minimal LangGraph with a safety review step.
- Minimal RAG: ICD-10 code suggestions with a top-5 hit rate.
