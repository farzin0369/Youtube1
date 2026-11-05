import importlib.util, math
from pathlib import Path

spec = importlib.util.spec_from_file_location("bamo_prefabs", Path(__file__).resolve().parents[1] / "scripts" / "bamo_prefabs.py")
pf = importlib.util.module_from_spec(spec); spec.loader.exec_module(pf)
SHAPES = {"sphere", "cube", "cylinder", "cone", "torus", "icosphere"}
ROLES = {"primary", "accent", "neutral", "dark"}


def test_every_kind_builds_valid_parts():
    for kind in pf.PREFAB_KINDS:
        parts = pf.build_parts(kind, "x1")
        assert 2 <= len(parts) <= 260, kind
        for p in parts:
            assert p["shape"] in SHAPES and p["role"] in ROLES
            assert len(p["pos"]) == 3 and len(p["scale"]) == 3 and len(p["rot"]) == 3
            assert all(math.isfinite(v) for v in p["pos"] + p["scale"] + p["rot"])
            assert all(s > 0 for s in p["scale"]), (kind, p)
            assert all(abs(v) < 12 for v in p["pos"]), (kind, p)


def test_deterministic_and_seed_varies():
    assert pf.build_parts("tree", "a") == pf.build_parts("tree", "a")
    assert pf.build_parts("wave_field", "a") != pf.build_parts("wave_field", "b")
    assert pf.build_parts("particle_cloud", "a") != pf.build_parts("particle_cloud", "b")


def test_aliases_and_unknown():
    assert pf.canonical_kind("Person") == "figure"
    assert pf.canonical_kind("minaret") == "tower"
    assert pf.canonical_kind("cube") == "cube"
    try:
        pf.build_parts("cube"); raise AssertionError("should fail")
    except ValueError:
        pass


def test_kinds_do_not_collide_with_base_grammar():
    base = {"sphere", "cube", "cylinder", "torus", "cone", "icosphere", "ring", "line"}
    assert not (base & pf.PREFAB_KINDS)
    assert not (base & set(pf.PREFAB_ALIASES))
