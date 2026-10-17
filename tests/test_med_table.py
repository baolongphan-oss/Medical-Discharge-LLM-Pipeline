import sys
from pathlib import Path

# src/ isn't a package, so add it to the import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from med_table import plain_frequency, render_med_table
from schemas import Medication


def test_abbreviations_with_and_without_periods():
    assert plain_frequency("b.i.d.") == "2 times a day"
    assert plain_frequency("BID") == "2 times a day"
    assert plain_frequency("t.i.d.") == "3 times a day"
    assert plain_frequency("q.i.d.") == "4 times a day"
    assert plain_frequency("q.d.") == "1 time a day"
    assert plain_frequency("q.h.s.") == "at bedtime"


def test_combined_phrase():
    assert plain_frequency("1 tablet p.o. q.d. p.r.n.") == "1 tablet by mouth 1 time a day only when you need it"


def test_every_n_hours():
    assert plain_frequency("q.4h") == "every 4 hours"
    assert plain_frequency("q6h") == "every 6 hours"
    assert plain_frequency("q.8 hours") == "every 8 hours"


def test_eyes():
    assert plain_frequency("1 drop OU") == "1 drop both eyes"


def test_unmatched_stays_unchanged():
    assert plain_frequency("one daily with food") == "one daily with food"


def test_empty_medication_list():
    assert render_med_table([]) == "Ask your care team which medicines to take at home."


def test_nulls_and_new_duration():
    table = render_med_table([Medication(name="Keflex", status="new")])
    assert "| Keflex | Ask your doctor | Ask your doctor | Ask your doctor how long |" in table


def test_continued_null_duration_is_blank():
    table = render_med_table([Medication(name="Lasix", dose="40 mg", frequency="daily", status="continued")])
    assert "| Lasix | 40 mg | 1 time a day |  |" in table


def test_daily():
    assert plain_frequency("daily") == "1 time a day"
    # counted forms are not lone "daily", so they stay as written
    assert plain_frequency("twice daily") == "twice daily"


def test_prn_drops_duplicate_as_needed():
    assert plain_frequency("p.r.n. as needed for pain") == "only when you need it for pain"
    assert plain_frequency("q.4h p.r.n. as needed") == "every 4 hours only when you need it"


def test_group_order_and_unknown_in_your_medicines():
    meds = [
        Medication(name="Aspirin", status="stopped"),
        Medication(name="Metformin", dose="500 mg", status="unknown"),
        Medication(name="Lasix", dose="40 mg", status="continued"),
        Medication(name="Lisinopril", dose="20 mg", status="changed"),
        Medication(name="Keflex", dose="500 mg", status="new"),
    ]
    table = render_med_table(meds)
    headings = ["### New medicines", "### Changed medicines", "### Keep taking", "### Medicines to take", "### STOP taking"]
    positions = [table.index(h) for h in headings]
    assert positions == sorted(positions)
    # unknown goes under the neutral heading, not "Keep taking"
    assert "| Metformin |" in table.split("### Medicines to take")[1].split("###")[0]
    assert "| Metformin |" not in table.split("### Keep taking")[1].split("###")[0]
    # stopped group shows the name column only
    assert "| Aspirin |" in table and "| Aspirin | " not in table
