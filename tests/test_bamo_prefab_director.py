"""Tests the wrapper logic against a faithful stand-in for the director's normalize/validate."""
import types, re


def _fake_director():
    mod = types.ModuleType("app.bamo_ai_director")
    mod.SYSTEM = "BASE"
    mod._DOMAIN_HINTS = (("x", "old"),)
    alias = {"planet": "sphere", "pyramid": "cone", "star": "sphere"}
    allowed = {"sphere", "cube", "cylinder", "torus", "cone", "icosphere", "ring", "line"}

    def normalize(raw):
        g = dict(raw)
        out = []
        for i, it in enumerate(raw["objects"]):
            o = dict(it)
            o["id"] = re.sub(r"[^a-z0-9_]", "_", str(o["id"]).lower())
            k = str(o["kind"]).lower()
            o["kind"] = alias.get(k, k)
            out.append(o)
        g["objects"] = out
        return g

    def validate(raw):
        objs = []
        for it in raw["objects"]:
            if it["kind"] not in allowed:
                raise ValueError("unsupported kind " + it["kind"])
            objs.append({"id": it["id"], "kind": it["kind"]})  # drops extras like the real one
        return {"objects": objs}

    mod.normalize_scene_graph, mod.validate_scene_graph = normalize, validate
    return mod


def test_prefabs_survive_validation_and_unknown_still_rejected():
    fake = _fake_director()
    import app.bamo_prefab_director as kit
    assert kit.install(fake) is True and kit.install(fake) is False
    raw = {"objects": [
        {"id": "Hero 1", "kind": "Person"}, {"id": "dome_a", "kind": "dome"},
        {"id": "p", "kind": "planet"}, {"id": "ball", "kind": "sphere"}, {"id": "pyr", "kind": "pyramid"}]}
    res = fake.validate_scene_graph(fake.normalize_scene_graph(raw))
    assert [o["kind"] for o in res["objects"]] == ["figure", "dome", "planet", "sphere", "pyramid"]
    try:
        fake.validate_scene_graph(fake.normalize_scene_graph({"objects": [{"id": "z", "kind": "teapot"}]}))
        raise AssertionError("unknown kind must still be rejected")
    except ValueError:
        pass
    assert "figure" in fake.SYSTEM and fake.SYSTEM.startswith("BASE")
    assert len(fake._DOMAIN_HINTS) == 5 and fake._DOMAIN_HINTS[-1] == ("x", "old")
    assert any("Never depict holy persons" in h for _, h in fake._DOMAIN_HINTS)
