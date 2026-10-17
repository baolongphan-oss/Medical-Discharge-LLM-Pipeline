# main.py
import argparse, os
from extract import run_extraction
from translate import run_translation

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", default="v3")
    parser.add_argument("--translate", default="v3")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    args = parser.parse_args()

    model = os.environ.get("LLM_MODEL")
    extract_passes, extract_total = run_extraction(args.extract, model, split=args.split)
    stats = run_translation(args.extract, args.translate, model, split=args.split)

    # final summary of both stages
    print("\n===== Pipeline summary =====")
    print(f"Model: {model} | split: {args.split} | extract {args.extract} | translate {args.translate}")
    print(f"Stage 1 extraction:  {extract_passes}/{extract_total} notes passed validation")
    print(f"Stage 2 translation: {stats['translated']}/{stats['total']} notes translated")
    print(f"Dose check:          {stats['dose_check_pass']}/{stats['translated']} passed")
    print(f"Mean reading grade (Flesch-Kincaid): {stats['mean_grade']}")
