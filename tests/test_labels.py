# tests/test_labels.py
import json
from pathlib import Path
import pytest
import sys
# src/ isn't a package: add it to the import path so schemas can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from schemas import DischargeExtraction

LABELS = Path(__file__).resolve().parent.parent / "labels"

# parametrize makes pytest call test_label_file once per item in the list, passing each item in as `path`
# "path" is the name of the parameter in the test_label_file function
# find every file in "labels" folder that fits the format "note_*.json" (sorted list)
# get the name of the file as the name of each test in the output
@pytest.mark.parametrize("path", sorted(LABELS.glob("note_*.json")), ids=lambda p: p.name)
def test_label_file(path):
    # read file and parse the JSON into a dict
    data = json.loads(path.read_text())
    # check note_id field is the same as the note number (int) on the file name
    assert data["note_id"] == int(path.stem.split("_")[1]), "note_id doesn't match filename"
    # remove the two fields not in the schema. 
    # labeler_notes is optional so if it's not there, return None instead of crashing
    data.pop("labeler_notes", None); data.pop("note_id")
    # raises ValidationError (test fails) if fields, types, or status values don't match the schema
    DischargeExtraction.model_validate(data)