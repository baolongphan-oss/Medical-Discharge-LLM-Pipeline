from src.evaluate import freq_key, key, name_key, match_meds, score_note


def med(name, dose=None, status="unknown"):
    return {"name": name, "dose": dose, "frequency": None, "duration": None, "status": status}


def test_key_normalizes_and_keeps_none():
    assert key("Lasix 40 mg.") == "lasix40mg"
    assert key(None) is None


def test_taper_matches_by_dose_first():
    # two prednisone entries (taper): pass 1 must pair them by dose, not by order
    gold = [med("prednisone", "40 mg"), med("prednisone", "20 mg")]
    pred = [med("Prednisone", "20 mg"), med("prednisone", "40 mg")]
    pairs, fn, fp = match_meds(gold, pred)
    assert fn == 0 and fp == 0
    assert all(key(g["dose"]) == key(p["dose"]) for g, p in pairs)


def test_wrong_dose_still_matches_by_name_but_counts_dose_wrong():
    row = score_note([med("lasix", "80 mg")], [med("Lasix", "40 mg")])
    assert row["tp"] == 1 and row["dose_correct"] == 0


def test_invented_and_missed():
    row = score_note([med("aspirin")], [med("metoprolol")])
    assert (row["tp"], row["fn"], row["fp"]) == (0, 1, 1)


def test_freq_key_drops_route():
    assert freq_key("p.o. b.i.d") == freq_key("b.i.d.")
    assert freq_key("subcu daily") == "daily"


def test_name_key_drops_form():
    assert name_key("Combivent nebulizer") == name_key("Combivent")
    assert name_key("Flonase nasal spray") == "flonase"
