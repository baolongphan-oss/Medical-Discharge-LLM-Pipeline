# main.py
import argparse, os
from extract import run_extraction
from translate import run_translation

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", default="v4")
    parser.add_argument("--translate", default="v4")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    model = os.environ.get("LLM_MODEL")
    extract_passes, extract_total = run_extraction(args.extract, model, split=args.split, skip_existing=args.skip_existing)
    stats = run_translation(args.extract, args.translate, model, split=args.split, skip_existing=args.skip_existing)

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
