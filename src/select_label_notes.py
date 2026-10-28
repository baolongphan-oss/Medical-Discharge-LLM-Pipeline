import sys
import random
import pandas as pd
from pathlib import Path

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent
    test_data_path = ROOT / "data" / "test.csv"
    test_df = pd.read_csv(test_data_path)
    test_ids_random = random.Random(42).sample(test_df['note_id'].tolist(), 25)

    label_selection_path = ROOT / "labels" / "selection.txt"
    if label_selection_path.is_file():
        sys.exit(f"{label_selection_path} already exists. Delete it manually if you really want to re-sample.")
    
    with open(label_selection_path, "w") as f:
        for test_id in test_ids_random:
            f.write(str(test_id) + "\n")

    hand_label_notes = test_df[test_df["note_id"].isin(test_ids_random)]
    print(hand_label_notes.head(5))