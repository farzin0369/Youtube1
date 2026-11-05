import math
import pytest
from app import bamo_scene_kit as kit


def _spec(name, **opts):
    return {"prop": name, "at": [0, 0, -0.1], "size": 1.0, "options": opts}


def test_every_prop_expands_to_valid_grammar():
    for name in kit.PROPS:
        objs = kit.expand_props([_spec(name)])
        assert 3 <= len(objs) <= kit.MAX_OBJECTS_PER_SCENE, name
        kit.validate_objects(objs)


def test_ids_unique_across_multiple_props():
    objs = kit.expand_props([{"prop": "figure", "at": [-2, 0, 0]}, {"prop": "figure", "at": [2, 0, 0], "options": {"pose": "run"}}])
    ids = [o["id"] for o in objs]
    assert len(ids) == len(set(ids))


def test_deterministic():
    a = kit.expand_props([_spec("terrain")])
    b = kit.expand_props([_spec("terrain")])
    assert a == b


def test_props_are_visually_distinct():
    sigs = {name: tuple((o["kind"], tuple(round(v, 2) for v in o["position"])) for o in kit.expand_props([_spec(name)]))
            for name in kit.PROPS}
    assert len(set(sigs.values())) == len(kit.PROPS)


def test_bar_orientation_points_cylinder_axis_at_target():
    b = kit._Builder("t")
    a, c = (0.0, 0.0, 0.0), (1.0, 2.0, 3.0)
    b.bar("x", "r", a, c, 0.1, "key")
    item = b.items[0]
    _, beta, gamma = item["rotation"]
    axis = (math.sin(beta) * math.cos(gamma), math.sin(beta) * math.sin(gamma), math.cos(beta))
    length = math.sqrt(14)
    expect = (1 / length, 2 / length, 3 / length)
    assert all(abs(p - q) < 1e-9 for p, q in zip(axis, expect))
    assert abs(item["scale"][2] - length / 2) < 1e-9


def test_poses_change_the_figure():
    stand = kit.expand_props([_spec("figure", pose="stand")])
    kick = kit.expand_props([_spec("figure", pose="kick")])
    assert [o["position"] for o in stand] != [o["position"] for o in kick]


def test_molecule_formulas_differ_and_water_angle():
    water = kit.expand_props([_spec("molecule", formula="water")])
    benzene = kit.expand_props([_spec("molecule", formula="benzene")])
    assert len(benzene) > len(water)
    atoms = [o for o in water if o["role"].endswith("atom")]
    o_pos = next(o["position"] for o in atoms if o["role"] == "O atom")
    hs = [o["position"] for o in atoms if o["role"] == "H atom"]
    v1 = [hs[0][i] - o_pos[i] for i in range(3)]
    v2 = [hs[1][i] - o_pos[i] for i in range(3)]
    cos = sum(x * y for x, y in zip(v1, v2)) / (math.dist(v1, (0, 0, 0)) * math.dist(v2, (0, 0, 0)))
    assert abs(math.degrees(math.acos(cos)) - 104.5) < 0.5


def test_bar_chart_is_data_driven():
    objs = kit.expand_props([_spec("bar_chart", values=[1, 2, 8])])
    bars = [o for o in objs if o["role"] == "data bar"]
    heights = [o["scale"][2] for o in bars]
    assert heights[2] > heights[1] > heights[0]
    assert bars[2]["material"] == "accent"


def test_prop_motion_and_size_scaling_stay_in_bounds():
    objs = kit.expand_props([{"prop": "columned_hall", "at": [5.9, 5.9, 5.9], "size": 2.0, "motion": "rise", "motion_amount": 9}])
    kit.validate_objects(objs)
    assert any(o["action"] == "rise" and o["action_amount"] == 4 for o in objs)


def test_rejects_bad_specs():
    with pytest.raises(ValueError):
        kit.expand_props([{"prop": "nonexistent"}])
    with pytest.raises(ValueError):
        kit.expand_props([])
    with pytest.raises(ValueError):
        kit.expand_props([_spec("football_pitch")] * 4)


def test_scene_object_cap():
    with pytest.raises(ValueError):
        kit.expand_props([_spec("ellipse_construction"), _spec("neural_network"), _spec("football_pitch")], max_objects=40)


def test_director_wrapper_uses_props(monkeypatch):
    base = {"visual_thesis": "t", "objects": [{"id": "old"}], "relationships": [{"x": 1}], "provider": "p", "camera": {"move": "orbit"}}
    monkeypatch.setattr(kit, "_direct_scene", lambda **kw: dict(base))
    monkeypatch.setattr(kit, "_generate_text", lambda *a, **k: ('{"props":[{"prop":"molecule","at":[0,0,0],"options":{"formula":"water"}}],"reason":"x"}', "m"))
    plan = kit.direct_scene_with_props(narration="n", visual_brief="v")
    assert plan["scene_kit"]["used"] and plan["relationships"] == [] and plan["provider"].endswith("+scene-kit")
    assert plan["director_primitives"] == base["objects"]


def test_director_wrapper_falls_back_on_any_error(monkeypatch):
    base = {"visual_thesis": "t", "objects": [{"id": "old"}], "relationships": [], "provider": "p"}
    monkeypatch.setattr(kit, "_direct_scene", lambda **kw: dict(base))
    monkeypatch.setattr(kit, "_generate_text", lambda *a, **k: ("not json", "m"))
    plan = kit.direct_scene_with_props(narration="n", visual_brief="v")
    assert plan["objects"] == base["objects"] and plan["scene_kit"]["used"] is False
    monkeypatch.setattr(kit, "_generate_text", lambda *a, **k: ('{"props":[{"prop":"bogus"}]}', "m"))
    plan = kit.direct_scene_with_props(narration="n", visual_brief="v")
    assert plan["objects"] == base["objects"] and plan["scene_kit"]["used"] is False
