# main.py
import argparse, os
from extract import run_extraction
from translate import run_translation
from pathlib import Path

def load_ids(ids_path):
    """Return the set of note_ids to run, minus any in labels/excluded.txt. None = all notes."""
    if ids_path is None:
        return None 
    ids = set()
    for line in ids_path.read_text().split():
        if line.strip():
            ids.add(int(line))
    excluded_path = ids_path.parent / "excluded.txt"
    if excluded_path.is_file():
        excluded = set()
        for line in excluded_path.read_text().splitlines():
            if line.strip():
                excluded.add(int(line.split()[0]))
        ids -= excluded
    return ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", default="v4")
    parser.add_argument("--translate", default="v4")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--ids", type=Path, default=None, help="file with one note_id per line; run only these notes")
    args = parser.parse_args()

    note_ids = load_ids(args.ids)
    if note_ids is not None:
        print(f"Running {len(note_ids)} notes from {args.ids}")

    model = os.environ.get("LLM_MODEL")
    extract_passes, extract_total = run_extraction(args.extract, model, split=args.split, skip_existing=args.skip_existing, note_ids=note_ids)
    stats = run_translation(args.extract, args.translate, model, split=args.split, skip_existing=args.skip_existing, note_ids=note_ids)

    # final summary of both stages
    print("\n===== Pipeline summary =====")
    print(f"Model: {model} | split: {args.split} | extract {args.extract} | translate {args.translate}")
    if extract_total == 0:
        print("Stage 1 extraction:  All notes were already extracted")
    else:
        print(f"Stage 1 extraction:  {extract_passes}/{extract_total} notes passed validation")

    if stats['attempted'] == 0:
        print("Stage 2 translation: All notes were already translated")
    else:
        print(f"Stage 2 translation: {stats['translated']}/{stats['attempted']} notes translated")
    print(f"Dose check (all notes):  {stats['dose_check_pass']}/{stats['total_notes']} passed")
    print(f"Mean reading grade (Flesch-Kincaid): {stats['mean_grade']}")
