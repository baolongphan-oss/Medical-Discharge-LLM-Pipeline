# main.py
import argparse, os
from extract import run_extraction
from translate import run_translation

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", default="v2")
    parser.add_argument("--translate", default="v2")
    args = parser.parse_args()

    model = os.environ.get("LLM_MODEL")
    run_extraction(args.extract, model)
    run_translation(args.extract, args.translate, model)