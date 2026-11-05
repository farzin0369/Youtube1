"""BAMO scene kit: parametric 3D props that expand into executable primitives.

The AI director only knows eight primitives, so characters, buildings, molecules,
pitches and charts could never be depicted literally. This kit adds a library of
deterministic, bounded prop generators. Each prop expands into plain scene-graph
objects (sphere/cube/cylinder/cone/torus) that the existing Blender interpreter
(`scripts/bamo_blender_motifs_b.py`) already renders - no Blender changes needed.

Limbs and bonds are cylinder OBJECTS (not relationships) so they move together
with the rest of a prop when a prop-level motion is applied.
"""
from __future__ import annotations

import json
import math
import random
import re
from typing import Any, Callable

ALLOWED_KINDS = {"sphere", "cube", "cylinder", "torus", "cone", "icosphere", "ring", "line"}
ALLOWED_MATERIALS = {"key", "accent", "neutral", "dark"}
ALLOWED_ACTIONS = {"rise", "fall", "rotate", "orbit", "pulse", "travel_x", "travel_y", "reveal", "none"}
PROP_MOTIONS = {"none", "reveal", "rise", "fall", "travel_x", "travel_y"}
MAX_OBJECTS_PER_SCENE = 90
_ID_RE = re.compile(r"[a-z][a-z0-9_]{1,31}")

Vec = tuple[float, float, float]


def _c(value: Any, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(low, min(high, number))


class _Builder:
    """Collects objects in prop-local coordinates with unique ids."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.items: list[dict[str, Any]] = []

    def add(self, kind: str, tag: str, role: str, pos: Vec, scale: Vec, material: str,
            rotation: Vec = (0.0, 0.0, 0.0), action: str = "none", amount: float = 0.0) -> None:
        self.items.append({
            "kind": kind, "tag": tag, "role": role, "position": list(pos), "scale": list(scale),
            "rotation": list(rotation), "material": material, "action": action, "action_amount": amount,
        })

    def bar(self, tag: str, role: str, a: Vec, b: Vec, radius: float, material: str) -> None:
        """Cylinder object spanning a->b (limb, bond, edge, rod)."""
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-6:
            return
        beta = math.acos(max(-1.0, min(1.0, dz / length)))
        gamma = math.atan2(dy, dx)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
        self.add("cylinder", tag, role, mid, (radius, radius, length / 2), material, (0.0, beta, gamma))


# ----------------------------------------------------------------- prop generators

def _domed_sanctuary(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    b.add("cube", "plinth", "stone platform", (0, 0, 0.07), (3.6, 2.4, 0.14), "neutral")
    b.add("cube", "hall", "main prayer hall", (0, 0, 0.6), (1.8, 1.4, 0.9), "neutral")
    b.add("cylinder", "drum", "dome drum", (0, 0, 1.25), (0.78, 0.78, 0.25), "neutral")
    b.add("sphere", "dome", "central dome", (0, 0, 1.5), (0.88, 0.88, 0.78), "key")
    b.add("cone", "finial", "dome finial", (0, 0, 2.42), (0.07, 0.07, 0.28), "accent")
    for side, x in (("l", -1.5), ("r", 1.5)):
        b.add("cylinder", f"shaft_{side}", "minaret shaft", (x, 0.6, 1.24), (0.16, 0.16, 1.1), "neutral")
        b.add("torus", f"ring_{side}", "minaret balcony", (x, 0.6, 1.95), (0.19, 0.19, 0.4), "accent")
        b.add("cone", f"cap_{side}", "minaret cap", (x, 0.6, 2.72), (0.2, 0.2, 0.4), "key")
    for side, x in (("l", -0.8), ("r", 0.8)):
        b.add("sphere", f"semi_{side}", "side semi-dome", (x, -0.15, 1.12), (0.38, 0.38, 0.3), "key")
    b.add("cube", "portal", "entrance portal", (0, -0.72, 0.52), (0.5, 0.1, 0.7), "dark")


def _columned_hall(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    count = int(_c(o.get("columns"), 4, 8, 6))
    b.add("cube", "stylobate", "stepped base", (0, 0, 0.07), (3.8, 1.8, 0.14), "neutral")
    span = 3.2
    for i in range(count):
        x = -span / 2 + span * i / (count - 1)
        b.add("cylinder", f"col_{i}", "column", (x, 0, 1.07), (0.17, 0.17, 0.93), "neutral")
        b.add("cube", f"cap_{i}", "column capital", (x, 0, 2.05), (0.42, 0.42, 0.1), "key")
    b.add("cube", "architrave", "entablature", (0, 0, 2.2), (3.6, 0.55, 0.22), "neutral")
    b.add("cone", "pediment", "pediment", (0, 0, 2.7), (1.9, 0.5, 0.45), "key")


_POSES: dict[str, dict[str, Vec]] = {
    "stand": {"elbow_l": (-0.34, 0, 1.22), "hand_l": (-0.36, 0, 0.95), "elbow_r": (0.34, 0, 1.22), "hand_r": (0.36, 0, 0.95),
              "knee_l": (-0.16, 0, 0.52), "foot_l": (-0.16, 0, 0.05), "knee_r": (0.16, 0, 0.52), "foot_r": (0.16, 0, 0.05)},
    "run": {"elbow_l": (0.25, 0, 1.25), "hand_l": (0.5, 0, 1.45), "elbow_r": (-0.3, 0, 1.2), "hand_r": (-0.55, 0, 1.4),
            "knee_l": (0.45, 0, 0.75), "foot_l": (0.2, 0, 0.3), "knee_r": (-0.3, 0, 0.6), "foot_r": (-0.7, 0, 0.35)},
    "wave": {"elbow_l": (-0.34, 0, 1.22), "hand_l": (-0.36, 0, 0.95), "elbow_r": (0.5, 0, 1.55), "hand_r": (0.55, 0, 2.0),
             "knee_l": (-0.16, 0, 0.52), "foot_l": (-0.16, 0, 0.05), "knee_r": (0.16, 0, 0.52), "foot_r": (0.16, 0, 0.05)},
    "arms_up": {"elbow_l": (-0.5, 0, 1.75), "hand_l": (-0.55, 0, 2.25), "elbow_r": (0.5, 0, 1.75), "hand_r": (0.55, 0, 2.25),
                "knee_l": (-0.2, 0, 0.52), "foot_l": (-0.25, 0, 0.05), "knee_r": (0.2, 0, 0.52), "foot_r": (0.25, 0, 0.05)},
    "kick": {"elbow_l": (-0.45, 0, 1.3), "hand_l": (-0.7, 0, 1.2), "elbow_r": (0.4, 0, 1.3), "hand_r": (0.65, 0, 1.4),
             "knee_l": (-0.12, 0, 0.5), "foot_l": (-0.15, 0, 0.05), "knee_r": (0.5, 0, 0.7), "foot_r": (1.0, 0, 0.55)},
    "sit": {"elbow_l": (-0.34, 0, 1.2), "hand_l": (-0.3, -0.3, 0.9), "elbow_r": (0.34, 0, 1.2), "hand_r": (0.3, -0.3, 0.9),
            "knee_l": (-0.16, -0.6, 0.55), "foot_l": (-0.16, -0.6, 0.05), "knee_r": (0.16, -0.6, 0.55), "foot_r": (0.16, -0.6, 0.05)},
}


def _figure(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    pose = _POSES.get(str(o.get("pose")), _POSES["stand"])
    shirt = "accent" if str(o.get("team")) == "accent" else "key"
    pelvis, chest, head = (0, 0, 1.0), (0, 0, 1.55), (0, 0, 1.97)
    sh = {"l": (-0.3, 0, 1.5), "r": (0.3, 0, 1.5)}
    hip = {"l": (-0.15, 0, 1.0), "r": (0.15, 0, 1.0)}
    if str(o.get("pose")) == "sit":
        pelvis = (0, 0, 0.62)
        hip = {"l": (-0.15, 0, 0.62), "r": (0.15, 0, 0.62)}
        chest, head = (0, 0, 1.17), (0, 0, 1.59)
        sh = {"l": (-0.3, 0, 1.12), "r": (0.3, 0, 1.12)}
    b.add("sphere", "head", "head", head, (0.22, 0.22, 0.22), "neutral")
    b.bar("torso", "torso", chest, pelvis, 0.17, shirt)
    b.add("sphere", "pelvis", "pelvis", pelvis, (0.18, 0.18, 0.18), "dark")
    for s in ("l", "r"):
        b.add("sphere", f"shoulder_{s}", "shoulder", sh[s], (0.1, 0.1, 0.1), shirt)
        b.bar(f"upper_arm_{s}", "upper arm", sh[s], pose[f"elbow_{s}"], 0.07, "neutral")
        b.add("sphere", f"elbow_{s}", "elbow", pose[f"elbow_{s}"], (0.08, 0.08, 0.08), "neutral")
        b.bar(f"forearm_{s}", "forearm", pose[f"elbow_{s}"], pose[f"hand_{s}"], 0.06, "neutral")
        b.add("sphere", f"hand_{s}", "hand", pose[f"hand_{s}"], (0.09, 0.09, 0.09), "accent")
        b.bar(f"thigh_{s}", "thigh", hip[s], pose[f"knee_{s}"], 0.085, "dark" if shirt == "key" else "neutral")
        b.add("sphere", f"knee_{s}", "knee", pose[f"knee_{s}"], (0.09, 0.09, 0.09), "neutral")
        b.bar(f"shin_{s}", "shin", pose[f"knee_{s}"], pose[f"foot_{s}"], 0.07, "neutral")
        b.add("sphere", f"foot_{s}", "foot", pose[f"foot_{s}"], (0.11, 0.11, 0.11), "accent")


_ATOM = {"H": (0.26, "neutral"), "C": (0.42, "key"), "O": (0.42, "accent"), "N": (0.4, "key")}


def _molecule_layout(formula: str) -> tuple[list[tuple[str, Vec]], list[tuple[int, int]]]:
    z0 = 1.4
    if formula == "co2":
        atoms = [("C", (0, 0, z0)), ("O", (-1.2, 0, z0)), ("O", (1.2, 0, z0))]
        return atoms, [(0, 1), (0, 2)]
    if formula == "methane":
        r = 1.0 / math.sqrt(3)
        atoms = [("C", (0, 0, z0))] + [("H", (sx * r * 1.1, sy * r * 1.1, z0 + sz * r * 1.1))
                                       for sx, sy, sz in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))]
        return atoms, [(0, i) for i in range(1, 5)]
    if formula == "ammonia":
        atoms = [("N", (0, 0, z0 + 0.35))] + [("H", (math.cos(a) * 0.95, math.sin(a) * 0.95, z0 - 0.3))
                                              for a in (0.3, 0.3 + 2.094, 0.3 + 4.189)]
        return atoms, [(0, i) for i in range(1, 4)]
    if formula == "benzene":
        atoms, bonds = [], []
        for i in range(6):
            a = i * math.pi / 3
            atoms.append(("C", (math.cos(a) * 1.0, 0, z0 + math.sin(a) * 1.0)))
        for i in range(6):
            a = i * math.pi / 3
            atoms.append(("H", (math.cos(a) * 1.75, 0, z0 + math.sin(a) * 1.75)))
        bonds = [(i, (i + 1) % 6) for i in range(6)] + [(i, i + 6) for i in range(6)]
        return atoms, bonds
    half = math.radians(104.5 / 2)  # water (default)
    atoms = [("O", (0, 0, z0 + 0.2)), ("H", (-math.sin(half) * 1.0, 0, z0 + 0.2 - math.cos(half) * 1.0)),
             ("H", (math.sin(half) * 1.0, 0, z0 + 0.2 - math.cos(half) * 1.0))]
    return atoms, [(0, 1), (0, 2)]


def _molecule(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    formula = str(o.get("formula", "water")).lower()
    atoms, bonds = _molecule_layout(formula if formula in {"water", "co2", "methane", "ammonia", "benzene"} else "water")
    for i, (el, pos) in enumerate(atoms):
        radius, mat = _ATOM[el]
        b.add("sphere", f"atom_{i}", f"{el} atom", pos, (radius, radius, radius), mat)
    for i, (p, q) in enumerate(bonds):
        b.bar(f"bond_{i}", "chemical bond", atoms[p][1], atoms[q][1], 0.06, "neutral")


def _ring_polygon(b: _Builder, tag: str, role: str, center: Vec, radius: float, segments: int,
                  material: str, plane: str = "xy", thick: float = 0.05) -> None:
    pts = []
    for i in range(segments):
        a = i * 2 * math.pi / segments
        if plane == "xy":
            pts.append((center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), center[2]))
        else:
            pts.append((center[0] + radius * math.cos(a), center[1], center[2] + radius * math.sin(a)))
    for i in range(segments):
        b.bar(f"{tag}_{i}", role, pts[i], pts[(i + 1) % segments], thick, material)


def _orbit_system(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    n = int(_c(o.get("planets"), 1, 3, 3))
    star = (0.0, 0.0, 1.3)
    b.add("sphere", "star", "central star", star, (0.62, 0.62, 0.62), "key", action="pulse")
    for k in range(n):
        radius = 1.2 + 0.85 * k
        _ring_polygon(b, f"path{k}", "orbit path", star, radius, 20, "neutral", "xy", 0.035)
        size = 0.17 + 0.05 * ((k * 7 + rng.randint(0, 3)) % 3)
        direction = 1 if k % 2 == 0 else -1
        b.add("sphere", f"planet_{k}", "orbiting planet", star, (size, size, size),
              "accent" if k % 2 == 0 else "neutral", action="orbit", amount=direction * radius)


def _wave_field(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    sources = ((-1.3, 0.0), (1.3, 0.0))
    rings = int(_c(o.get("rings"), 4, 8, 7))
    for si, (sx, sy) in enumerate(sources):
        for j in range(rings, 0, -1):
            r = 0.3 + 0.32 * j
            crest = 0.5 + 0.5 * math.cos(j * math.pi / 1.5)
            height = 0.15 + 0.6 * crest
            b.add("cylinder", f"s{si}_ring_{j}", "wavefront crest" if crest > 0.5 else "wavefront trough",
                  (sx, sy, 0.06 + 0.5 * height), (r, r, 0.04 + 0.5 * height),
                  "key" if crest > 0.5 else "accent")
        b.add("sphere", f"s{si}_src", "wave source", (sx, sy, 0.75), (0.17, 0.17, 0.17), "neutral", action="pulse")


def _ellipse_construction(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    a_, b_ = _c(o.get("a"), 1.4, 2.6, 2.2), _c(o.get("b"), 0.8, 1.8, 1.4)
    zc = 1.7
    pts = [(a_ * math.cos(i * 2 * math.pi / 28), 0.0, zc + b_ * math.sin(i * 2 * math.pi / 28)) for i in range(28)]
    for i in range(28):
        b.bar(f"curve_{i}", "ellipse curve", pts[i], pts[(i + 1) % 28], 0.05, "key")
    c = math.sqrt(max(a_ * a_ - b_ * b_, 0.01))
    f1, f2 = (-c, 0.0, zc), (c, 0.0, zc)
    p = (a_ * math.cos(0.7), 0.0, zc + b_ * math.sin(0.7))
    b.add("sphere", "focus_1", "focus", f1, (0.12, 0.12, 0.12), "accent")
    b.add("sphere", "focus_2", "focus", f2, (0.12, 0.12, 0.12), "accent")
    b.add("sphere", "point", "point on the ellipse", p, (0.13, 0.13, 0.13), "neutral")
    b.bar("ray_1", "distance to first focus", f1, p, 0.05, "accent")
    b.bar("ray_2", "distance to second focus", f2, p, 0.05, "accent")
    b.bar("axis_major", "major axis", (-a_, 0, zc), (a_, 0, zc), 0.05, "neutral")
    b.bar("axis_minor", "minor axis", (0, 0, zc - b_), (0, 0, zc + b_), 0.05, "neutral")


def _neural_network(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    layers = o.get("layers") if isinstance(o.get("layers"), list) else [3, 4, 4, 2]
    layers = [int(_c(n, 1, 5, 3)) for n in layers[:5]] or [3, 4, 2]
    nodes: list[list[Vec]] = []
    for li, count in enumerate(layers):
        x = -2.4 + 4.8 * li / max(1, len(layers) - 1)
        col = []
        for k in range(count):
            z = 1.6 + (k - (count - 1) / 2) * 0.8
            col.append((x, 0.0, z))
        nodes.append(col)
    edges = 0
    for li in range(len(nodes) - 1):
        for p in nodes[li]:
            for q in nodes[li + 1]:
                if edges >= 40:
                    break
                b.bar(f"edge_{edges}", "synaptic connection", p, q, 0.05, "neutral")
                edges += 1
    for li, col in enumerate(nodes):
        for k, p in enumerate(col):
            hot = rng.random() < 0.4
            b.add("sphere", f"node_{li}_{k}", "neuron", p, (0.2, 0.2, 0.2), "accent" if hot else "key",
                  action="pulse" if hot else "none")


def _football_pitch(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    b.add("cube", "turf", "pitch surface", (0, 0, 0.04), (5.6, 3.4, 0.08), "key")
    b.add("cube", "halfway", "halfway line", (0, 0, 0.1), (0.05, 3.3, 0.05), "neutral")
    b.add("torus", "circle", "centre circle", (0, 0, 0.1), (0.55, 0.55, 0.05), "neutral")
    for side, x in (("l", -2.75), ("r", 2.75)):
        for y in (-0.55, 0.55):
            b.add("cylinder", f"post_{side}_{'a' if y < 0 else 'b'}", "goal post", (x, y, 0.4), (0.05, 0.05, 0.4), "neutral")
        b.add("cube", f"bar_{side}", "crossbar", (x, 0, 0.8), (0.05, 1.15, 0.05), "neutral")
    b.add("sphere", "ball", "match ball", (-0.4, 0.0, 0.3), (0.2, 0.2, 0.2), "neutral", action="travel_x", amount=2.4)
    for team, mat, xs in (("a", "accent", (-1.6, -0.9, -2.3)), ("b", "dark", (1.2, 1.9, 0.6))):
        for i, x in enumerate(xs):
            y = -1.0 + 1.0 * i
            direction = rng.choice((-0.8, 0.8))
            b.add("cylinder", f"pl_{team}{i}", "player body", (x, y, 0.46), (0.12, 0.12, 0.36), mat, action="travel_x", amount=direction)
            b.add("sphere", f"hd_{team}{i}", "player head", (x, y, 0.95), (0.13, 0.13, 0.13), "neutral", action="travel_x", amount=direction)


def _bar_chart(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    raw = o.get("values") if isinstance(o.get("values"), list) else [3, 5, 4, 7, 6]
    values = [max(0.0, _c(v, 0, 1e9, 0.0)) for v in raw[:8]] or [1, 2, 3]
    top = max(values) or 1.0
    n = len(values)
    peak = values.index(max(values))
    b.add("cube", "baseline", "chart baseline", (0, 0, 0.04), (0.5 * n + 1.2, 0.8, 0.08), "neutral")
    for i, v in enumerate(values):
        h = max(0.15, 2.6 * v / top)
        x = (i - (n - 1) / 2) * 0.62
        b.add("cube", f"bar_{i}", "data bar", (x, 0, 0.08 + h / 2), (0.4, 0.4, h),
              "accent" if i == peak else "key", action="reveal")


def _milestone_path(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    n = int(_c(o.get("milestones"), 3, 6, 5))
    prev = None
    for i in range(n):
        x = -2.5 + 5.0 * i / (n - 1)
        h = 0.35 + 0.42 * i
        b.add("cube", f"step_{i}", "milestone step", (x, 0, h / 2), (0.8, 0.9, h), "neutral")
        beacon = (x, 0.0, h + 0.3)
        b.add("sphere", f"beacon_{i}", "milestone beacon", beacon, (0.17, 0.17, 0.17),
              "accent" if i == n - 1 else "key", action="pulse" if i == n - 1 else "none")
        if prev is not None:
            b.bar(f"link_{i}", "timeline link", prev, beacon, 0.05, "key")
        prev = beacon


def _terrain(b: _Builder, o: dict[str, Any], rng: random.Random) -> None:
    peaks = int(_c(o.get("peaks"), 2, 5, 4))
    trees = int(_c(o.get("trees"), 0, 5, 3))
    b.add("sphere", "sun", "sun", (-2.6, 3.5, 3.4), (0.45, 0.45, 0.45), "accent", action="pulse")
    for i in range(peaks):
        x = -3.0 + 6.0 * i / max(1, peaks - 1) + rng.uniform(-0.3, 0.3)
        s = rng.uniform(0.9, 1.5)
        y = rng.uniform(1.0, 2.8)
        b.add("cone", f"peak_{i}", "mountain", (x, y, s), (s * 1.1, s * 0.9, s), "neutral")
        b.add("cone", f"snow_{i}", "snow cap", (x, y, 1.76 * s), (s * 0.28, s * 0.24, s * 0.24), "key")
    for i in range(trees):
        x = -2.4 + 4.8 * i / max(1, trees - 1) + rng.uniform(-0.2, 0.2)
        y = rng.uniform(-0.8, 0.4)
        b.add("cylinder", f"trunk_{i}", "tree trunk", (x, y, 0.26), (0.07, 0.07, 0.26), "dark")
        b.add("cone", f"crown_{i}", "tree crown", (x, y, 0.85), (0.34, 0.34, 0.45), "key")


PROPS: dict[str, tuple[Callable[[_Builder, dict[str, Any], random.Random], None], str]] = {
    "domed_sanctuary": (_domed_sanctuary, "domed mosque/sanctuary with minarets; Islamic architecture, calm sacred scenes (no figures)"),
    "columned_hall": (_columned_hall, "classical columned temple/hall; ancient civilizations; option columns 4-8"),
    "figure": (_figure, "stylized human mannequin; options pose stand|run|wave|arms_up|kick|sit, team key|accent; use for stories, comedy, sports"),
    "molecule": (_molecule, "atoms and bonds; option formula water|co2|methane|ammonia|benzene"),
    "orbit_system": (_orbit_system, "star with orbiting planets on orbit paths; astronomy, atoms, gravity; option planets 1-3"),
    "wave_field": (_wave_field, "two sources with stepped crest/trough rings overlapping; wave interference; option rings 4-8"),
    "ellipse_construction": (_ellipse_construction, "ellipse with foci, point, distance rays and axes; math/orbits; options a, b"),
    "neural_network": (_neural_network, "layered neurons with connections; brain, AI; option layers [3,4,4,2]"),
    "football_pitch": (_football_pitch, "pitch with goals, ball and players; football and sports scenes"),
    "bar_chart": (_bar_chart, "animated data bars; statistics, records, news; option values [numbers up to 8]"),
    "milestone_path": (_milestone_path, "ascending steps with beacons and links; timelines, growth, progress; option milestones 3-6"),
    "terrain": (_terrain, "mountains, snow caps, trees and sun; nature, geography, journeys; options peaks 2-5, trees 0-5"),
}


# ----------------------------------------------------------------- expansion

def describe_props() -> str:
    return "\n".join(f"- {name}: {desc}" for name, (_, desc) in PROPS.items())


def validate_objects(objects: list[dict[str, Any]]) -> None:
    """Fail closed if any expanded object violates the renderer's scene grammar."""
    seen: set[str] = set()
    for obj in objects:
        oid = obj.get("id", "")
        if not _ID_RE.fullmatch(oid) or oid in seen:
            raise ValueError(f"invalid or duplicate object id: {oid!r}")
        seen.add(oid)
        if obj["kind"] not in ALLOWED_KINDS or obj["material"] not in ALLOWED_MATERIALS or obj["action"] not in ALLOWED_ACTIONS:
            raise ValueError(f"unsupported kind/material/action for {oid}")
        if not all(math.isfinite(v) and -6 <= v <= 6 for v in obj["position"]):
            raise ValueError(f"position out of range for {oid}")
        if not all(math.isfinite(v) and 0.05 <= v <= 4 for v in obj["scale"]):
            raise ValueError(f"scale out of range for {oid}")
        if not all(math.isfinite(v) and -6.28 <= v <= 6.28 for v in obj["rotation"]):
            raise ValueError(f"rotation out of range for {oid}")
        if not (math.isfinite(obj["action_amount"]) and -4 <= obj["action_amount"] <= 4):
            raise ValueError(f"action amount out of range for {oid}")


def expand_prop(spec: dict[str, Any], index: int) -> list[dict[str, Any]]:
    name = str(spec.get("prop", ""))
    if name not in PROPS:
        raise ValueError(f"unknown prop: {name!r}")
    at = spec.get("at") if isinstance(spec.get("at"), list) and len(spec.get("at")) == 3 else [0, 0, -0.1]
    ax, ay, az = (_c(v, -6, 6, 0.0) for v in at)
    size = _c(spec.get("size"), 0.4, 2.0, 1.0)
    options = spec.get("options") if isinstance(spec.get("options"), dict) else {}
    motion = str(spec.get("motion", "none"))
    motion = motion if motion in PROP_MOTIONS else "none"
    amount = _c(spec.get("motion_amount"), -4, 4, 1.0)
    seed = int(_c(spec.get("seed"), 0, 10**6, 0)) + index * 101
    builder = _Builder(f"p{index}")
    PROPS[name][0](builder, options, random.Random(seed))
    result = []
    for n, item in enumerate(builder.items):
        pos, scale = item["position"], item["scale"]
        action, act_amount = item["action"], item["action_amount"]
        if motion != "none" and action in {"none", "pulse"}:
            action, act_amount = motion, amount
        elif action == "orbit":
            act_amount = _c(act_amount * size, -4, 4, 1.0)
        elif action == "travel_x":
            act_amount = _c(act_amount * size, -4, 4, 0.0)
        tag = re.sub(r"[^a-z0-9_]", "", item["tag"].lower())
        suffix = f"_{n}"
        oid = (f"p{index}_{tag}")[: 31 - len(suffix)].rstrip("_") + suffix
        result.append({
            "id": oid, "kind": item["kind"], "role": item["role"],
            "position": [_c(ax + pos[0] * size, -6, 6, 0.0), _c(ay + pos[1] * size, -6, 6, 0.0), _c(az + pos[2] * size, -6, 6, 0.0)],
            "scale": [_c(v * size, 0.05, 4, 0.05) for v in scale],
            "rotation": item["rotation"], "material": item["material"],
            "action": action, "action_amount": float(act_amount),
        })
    return result


def expand_props(specs: list[dict[str, Any]], max_objects: int = MAX_OBJECTS_PER_SCENE) -> list[dict[str, Any]]:
    if not isinstance(specs, list) or not 1 <= len(specs) <= 3:
        raise ValueError("a scene needs 1-3 props")
    objects: list[dict[str, Any]] = []
    for i, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ValueError("prop spec must be an object")
        objects.extend(expand_prop(spec, i))
    if len(objects) > max_objects:
        raise ValueError(f"scene would contain {len(objects)} objects (limit {max_objects})")
    validate_objects(objects)
    return objects


# ----------------------------------------------------------------- set designer (LLM) wrapper

SET_DESIGNER_SYSTEM = (
    "You are BAMO's set designer. Choose 1-3 ready-made 3D props from the catalogue that literally depict the narration. "
    "Return ONLY JSON: {\"props\":[{\"prop\":name,\"at\":[x,y,z],\"size\":0.4-2.0,\"options\":{},\"motion\":\"none|reveal|rise|travel_x|travel_y\","
    "\"motion_amount\":-4..4,\"seed\":int}],\"reason\":\"one sentence\"}. Positions x,y,z within -6..6; ground is z=0. "
    "Spread multiple props apart (x offsets of 3+). Never depict prophets, Imams or holy figures. "
    "If no prop fits the meaning, return {\"props\":[],\"reason\":\"...\"}.\nCatalogue:\n" + describe_props()
)


def _direct_scene(**kwargs: Any) -> dict[str, Any]:
    from app.bamo_ai_director import direct_scene
    return direct_scene(**kwargs)


def _generate_text(system: str, prompt: str, **kwargs: Any) -> tuple[str, str]:
    from app.llm_provider import generate_text
    return generate_text(system, prompt, **kwargs)


def design_props(narration: str, visual_thesis: str, domain: str = "") -> list[dict[str, Any]]:
    prompt = json.dumps({"narration_exact": narration, "visual_thesis": visual_thesis, "domain": domain,
                         "task": "Pick props that make this exact sentence visually literal."}, ensure_ascii=False)
    raw, _provider = _generate_text(SET_DESIGNER_SYSTEM, prompt, max_tokens=700, temperature=0.2, json_mode=True, timeout=120)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("set designer returned no JSON")
    data = json.loads(raw[start:end + 1])
    props = data.get("props")
    if not isinstance(props, list):
        raise ValueError("set designer returned no props list")
    return props


def direct_scene_with_props(**kwargs: Any) -> dict[str, Any]:
    """Run the existing AI director, then upgrade the shot with kit props when they fit.

    Fail-safe: any kit error leaves the director's validated primitive plan untouched.
    """
    plan = _direct_scene(**kwargs)
    domain = str(kwargs.get("domain", ""))
    try:
        specs = design_props(str(kwargs.get("narration", "")), str(plan.get("visual_thesis", "")), domain)
        if not specs:
            plan["scene_kit"] = {"used": False, "reason": "no_fitting_prop"}
            return plan
        objects = expand_props(specs)
    except Exception as exc:  # noqa: BLE001 - deliberate: never break a render because of the kit
        plan["scene_kit"] = {"used": False, "error": type(exc).__name__}
        return plan
    plan["director_primitives"] = plan.get("objects", [])
    plan["objects"] = objects
    plan["relationships"] = []
    plan["props"] = specs
    plan["scene_kit"] = {"used": True, "object_count": len(objects), "props": [s.get("prop") for s in specs]}
    plan["provider"] = f"{plan.get('provider', 'unknown')}+scene-kit"
    return plan
