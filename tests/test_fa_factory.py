import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fa_factory import bank, compose
from fa_factory.tts import Beat


def test_seed_bank_valid_and_unique():
    ideas = bank.load()
    assert len(ideas) >= 20
    idx = bank.DedupIndex()
    for i in ideas:
        assert bank.validate(i) == [], i["id"]
        assert not idx.is_duplicate(i), i["id"]
        idx.add(i)


def test_validator_rejects_digits_and_latin():
    base = {"id": "x", "category": "c", "visual": "cosmos", "title": "t", "sentences": ["الف ب ج"] * 5}
    assert bank.validate(base) == []
    bad = dict(base, sentences=["عدد 5 است"] + ["الف ب ج"] * 4)
    assert any("digit" in e for e in bank.validate(bad))
    bad = dict(base, sentences=["hello"] + ["الف ب ج"] * 4)
    assert any("latin" in e for e in bank.validate(bad))


def test_dedup_catches_near_copies():
    ideas = bank.load()
    idx = bank.DedupIndex(ideas)
    copy = dict(ideas[0], id="copy-1", title=ideas[0]["title"] + " !")
    assert idx.is_duplicate(copy)


def test_selection_never_repeats(tmp_path, monkeypatch):
    monkeypatch.setattr(bank, "HISTORY", tmp_path / "h.jsonl")
    seen = set()
    total = len([i for i in bank.load() if not bank.validate(i)])
    for k in range(total):
        i = bank.select_idea(seed=k)
        assert i["id"] not in seen
        seen.add(i["id"])
        bank.record_use(i, ok=True)
    try:
        bank.select_idea()
        assert False, "should be exhausted"
    except RuntimeError:
        pass


def test_html_has_all_beats_and_rtl():
    idea = bank.load()[0]
    beats = [Beat(s, 1 + k * 3, 3.5 + k * 3) for k, s in enumerate(idea["sentences"])]
    h = compose.build_html(idea, beats, 25.0)
    assert 'dir="rtl"' in h and 'data-composition-id="main"' in h
    for k in range(len(beats)):
        assert f'id="beat{k}"' in h
    assert "__" not in h.replace("__timelines", "").replace("__bamo", "")
