"""Pure-Python prefab geometry for BAMO's 3D scene grammar (no bpy imports).

Each prefab expands into primitive parts in the prefab's local space (about 2 units
tall at scale 1, origin on the ground plane). The Blender executor turns parts into
meshes; this module is unit-testable without Blender.

Part: {"shape": sphere|cube|cylinder|cone|torus|icosphere,
       "pos": (x,y,z), "scale": (sx,sy,sz), "rot": (rx,ry,rz),
       "role": primary|accent|neutral|dark, "vertices": optional int}
Scale semantics match the Blender executor: sphere/icosphere = radii; cube = full
dimensions; cylinder/cone = (radius_x, radius_y, half_height); torus = (R, R, thickness).
"""
from __future__ import annotations

import math
import zlib

PREFAB_KINDS = frozenset({
    "figure", "column", "dome", "arch", "tower", "pyramid", "planet", "lattice",
    "wave_field", "particle_cloud", "pitch", "open_book", "tree", "house", "mountain",
})

PREFAB_ALIASES = {
    "person": "figure", "human": "figure", "character": "figure", "man": "figure",
    "woman": "figure", "player": "figure", "athlete": "figure", "humanoid": "figure",
    "pillar": "column", "colonnade": "column",
    "cupola": "dome", "mosque_dome": "dome",
    "gate": "arch", "archway": "arch",
    "minaret": "tower", "lighthouse": "tower", "castle_tower": "tower",
    "world": "planet", "earth": "planet", "moon": "planet",
    "crystal": "lattice", "crystal_lattice": "lattice", "grid_atoms": "lattice",
    "interference": "wave_field", "waves": "wave_field", "wave_surface": "wave_field",
    "particles": "particle_cloud", "dust": "particle_cloud", "stars": "particle_cloud",
    "field": "pitch", "football_pitch": "pitch", "stadium_floor": "pitch",
    "book": "open_book", "scripture": "open_book",
    "forest_tree": "tree", "palm": "tree",
    "building": "house", "hut": "house",
    "hill": "mountain", "peak": "mountain",
}


def seed_for(object_id: str) -> int:
    return zlib.crc32(str(object_id).encode("utf-8")) & 0xFFFFFFFF


class _Rng:
    """Tiny deterministic LCG so output is identical across Python/Blender builds."""
    def __init__(self, seed: int):
        self.state = (seed or 1) & 0x7FFFFFFF

    def next(self) -> float:
        self.state = (1103515245 * self.state + 12345) & 0x7FFFFFFF
        return self.state / 0x7FFFFFFF


def _p(shape, pos, scale, rot=(0, 0, 0), role="primary", vertices=None):
    part = {"shape": shape, "pos": tuple(float(v) for v in pos),
            "scale": tuple(float(v) for v in scale),
            "rot": tuple(float(v) for v in rot), "role": role}
    if vertices:
        part["vertices"] = int(vertices)
    return part


def _figure(rng):
    arm = 0.22 + 0.1 * rng.next()
    return [
        _p("sphere", (0, 0, 1.78), (0.22, 0.22, 0.24), role="neutral"),
        _p("cylinder", (0, 0, 1.52), (0.08, 0.08, 0.08), role="neutral"),
        _p("cube", (0, 0, 1.15), (0.62, 0.3, 0.72), role="primary"),
        _p("cylinder", (-0.4, 0, 1.15), (0.08, 0.08, 0.36), (0, -arm, 0), "primary"),
        _p("cylinder", (0.4, 0, 1.15), (0.08, 0.08, 0.36), (0, arm, 0), "primary"),
        _p("cylinder", (-0.15, 0, 0.38), (0.1, 0.1, 0.38), role="dark"),
        _p("cylinder", (0.15, 0, 0.38), (0.1, 0.1, 0.38), role="dark"),
        _p("cube", (-0.15, -0.06, 0.04), (0.2, 0.34, 0.1), role="accent"),
        _p("cube", (0.15, -0.06, 0.04), (0.2, 0.34, 0.1), role="accent"),
    ]


def _column(rng):
    return [
        _p("cube", (0, 0, 0.1), (0.9, 0.9, 0.2), role="neutral"),
        _p("cylinder", (0, 0, 1.1), (0.28, 0.28, 0.9), role="primary"),
        _p("torus", (0, 0, 0.3), (0.3, 0.3, 0.35), role="accent"),
        _p("cube", (0, 0, 2.1), (0.85, 0.85, 0.2), role="neutral"),
        _p("cube", (0, 0, 2.28), (1.0, 1.0, 0.16), role="primary"),
    ]


def _dome(rng):
    return [
        _p("cylinder", (0, 0, 0.6), (1.2, 1.2, 0.6), role="neutral"),
        _p("sphere", (0, 0, 1.2), (1.2, 1.2, 1.1), role="primary"),
        _p("cylinder", (0, 0, 2.5), (0.05, 0.05, 0.35), role="accent"),
        _p("sphere", (0, 0, 2.9), (0.12, 0.12, 0.12), role="accent"),
        _p("torus", (0, 0, 1.2), (1.22, 1.22, 0.1), role="accent"),
    ]


def _arch(rng):
    parts = [
        _p("cube", (-1.4, 0, 0.9), (0.45, 0.6, 1.8), role="neutral"),
        _p("cube", (1.4, 0, 0.9), (0.45, 0.6, 1.8), role="neutral"),
    ]
    n = 9
    for i in range(n):
        a = math.pi * i / (n - 1)
        parts.append(_p("cube", (-1.4 * math.cos(a), 0, 1.8 + 1.4 * math.sin(a)),
                        (0.45, 0.6, 0.62), (0, a - math.pi / 2, 0),
                        "primary" if i % 2 == 0 else "accent"))
    return parts


def _tower(rng):
    h = 3.4 + 0.8 * rng.next()
    return [
        _p("cylinder", (0, 0, 0.15), (0.65, 0.65, 0.15), role="neutral"),
        _p("cylinder", (0, 0, h / 2), (0.36, 0.36, h / 2), role="primary"),
        _p("torus", (0, 0, h * 0.72), (0.52, 0.52, 0.12), role="accent"),
        _p("cylinder", (0, 0, h + 0.2), (0.3, 0.3, 0.2), role="neutral"),
        _p("cone", (0, 0, h + 0.9), (0.34, 0.34, 0.7), role="accent"),
    ]


def _pyramid(rng):
    return [
        _p("cone", (0, 0, 1.0), (1.6, 1.6, 1.0), (0, 0, math.pi / 4), "primary", vertices=4),
        _p("cone", (0, 0, 0.55), (2.1, 2.1, 0.55), (0, 0, math.pi / 4), "neutral", vertices=4),
    ]


def _planet(rng):
    tilt = 0.35 + 0.5 * rng.next()
    return [
        _p("sphere", (0, 0, 1.0), (1.0, 1.0, 1.0), role="primary"),
        _p("torus", (0, 0, 1.0), (1.7, 1.7, 0.05), (tilt, 0.15, 0), "accent"),
        _p("sphere", (1.9, 0.0, 1.6), (0.18, 0.18, 0.18), role="neutral"),
    ]


def _lattice(rng):
    n, gap = 3, 0.9
    parts, off = [], gap * (n - 1) / 2
    for i in range(n):
        for j in range(n):
            for k in range(n):
                x, y, z = i * gap - off, j * gap - off, k * gap + 0.6
                parts.append(_p("sphere", (x, y, z), (0.2, 0.2, 0.2),
                                role="primary" if (i + j + k) % 2 == 0 else "accent"))
                if i < n - 1:
                    parts.append(_p("cylinder", (x + gap / 2, y, z), (0.04, 0.04, gap / 2),
                                    (0, math.pi / 2, 0), "neutral"))
                if j < n - 1:
                    parts.append(_p("cylinder", (x, y + gap / 2, z), (0.04, 0.04, gap / 2),
                                    (math.pi / 2, 0, 0), "neutral"))
                if k < n - 1:
                    parts.append(_p("cylinder", (x, y, z + gap / 2), (0.04, 0.04, gap / 2),
                                    role="neutral"))
    return parts


def _wave_field(rng):
    n, span = 15, 3.6
    k = 2.2 + 1.2 * rng.next()
    sep = 0.9 + 0.5 * rng.next()
    parts = []
    for i in range(n):
        for j in range(n):
            x = (i / (n - 1) - 0.5) * 2 * span
            y = (j / (n - 1) - 0.5) * 2 * span
            d1 = math.hypot(x + sep, y)
            d2 = math.hypot(x - sep, y)
            z = (math.sin(k * d1) + math.sin(k * d2)) * 0.5  # -1..1
            h = 0.55 + 0.5 * z
            parts.append(_p("cylinder", (x, y, h / 2), (0.14, 0.14, h / 2),
                            role="primary" if z > 0 else "accent"))
    return parts


def _particle_cloud(rng):
    parts = []
    for _ in range(70):
        u, v, w = rng.next(), rng.next(), rng.next()
        theta, phi = 2 * math.pi * u, math.acos(2 * v - 1)
        r = 2.8 * (w ** (1 / 3))
        size = 0.04 + 0.1 * rng.next()
        parts.append(_p("icosphere", (r * math.sin(phi) * math.cos(theta),
                                      r * math.sin(phi) * math.sin(theta),
                                      1.6 + r * math.cos(phi)), (size, size, size),
                        role="accent" if rng.next() > 0.6 else "primary"))
    return parts


def _pitch(rng):
    parts = [
        _p("cube", (0, 0, 0.03), (8.0, 5.0, 0.06), role="primary"),
        _p("cube", (0, 0, 0.07), (0.06, 5.0, 0.03), role="neutral"),
        _p("torus", (0, 0, 0.08), (0.9, 0.9, 0.03), role="neutral"),
        _p("cube", (-4.0, 0, 0.5), (0.1, 1.6, 1.0), role="neutral"),
        _p("cube", (4.0, 0, 0.5), (0.1, 1.6, 1.0), role="neutral"),
        _p("sphere", (0.0, 0.0, 0.3), (0.22, 0.22, 0.22), role="accent"),
    ]
    return parts


def _open_book(rng):
    return [
        _p("cube", (-0.55, 0, 0.45), (1.0, 1.4, 0.06), (0, 0.2, 0), "primary"),
        _p("cube", (0.55, 0, 0.45), (1.0, 1.4, 0.06), (0, -0.2, 0), "primary"),
        _p("cube", (0, 0, 0.3), (0.12, 1.45, 0.14), role="accent"),
        _p("cube", (0, 0, 0.12), (2.3, 1.6, 0.1), role="neutral"),
    ]


def _tree(rng):
    s = 0.85 + 0.4 * rng.next()
    return [
        _p("cylinder", (0, 0, 0.7 * s), (0.14 * s, 0.14 * s, 0.7 * s), role="dark"),
        _p("icosphere", (0, 0, 1.8 * s), (0.9 * s, 0.9 * s, 0.8 * s), role="primary"),
        _p("icosphere", (0.4 * s, 0.2, 1.4 * s), (0.6 * s, 0.6 * s, 0.55 * s), role="accent"),
        _p("icosphere", (-0.4 * s, -0.2, 1.5 * s), (0.65 * s, 0.65 * s, 0.6 * s), role="primary"),
    ]


def _house(rng):
    return [
        _p("cube", (0, 0, 0.6), (1.8, 1.4, 1.2), role="neutral"),
        _p("cone", (0, 0, 1.6), (1.35, 1.35, 0.6), (0, 0, math.pi / 4), "primary", vertices=4),
        _p("cube", (0, -0.71, 0.45), (0.4, 0.04, 0.8), role="dark"),
        _p("cube", (0.55, -0.71, 0.75), (0.3, 0.04, 0.3), role="accent"),
    ]


def _mountain(rng):
    return [
        _p("cone", (0, 0, 1.2), (2.0, 2.0, 1.2), role="neutral", vertices=7),
        _p("cone", (1.4, 0.4, 0.8), (1.2, 1.2, 0.8), role="dark", vertices=6),
        _p("cone", (0, 0, 2.2), (0.55, 0.55, 0.3), role="accent", vertices=7),
    ]


_BUILDERS = {
    "figure": _figure, "column": _column, "dome": _dome, "arch": _arch, "tower": _tower,
    "pyramid": _pyramid, "planet": _planet, "lattice": _lattice, "wave_field": _wave_field,
    "particle_cloud": _particle_cloud, "pitch": _pitch, "open_book": _open_book,
    "tree": _tree, "house": _house, "mountain": _mountain,
}


def canonical_kind(kind: str) -> str:
    k = str(kind or "").strip().lower()
    return PREFAB_ALIASES.get(k, k)


def build_parts(kind: str, object_id: str = "obj") -> list[dict]:
    kind = canonical_kind(kind)
    if kind not in _BUILDERS:
        raise ValueError(f"unknown prefab kind: {kind}")
    return _BUILDERS[kind](_Rng(seed_for(f"{kind}:{object_id}")))


PROMPT_SECTION = """
Compound prefab kinds (each is a ready-made multi-part 3D model; use them instead of
approximating real things with bare primitives; scale 1 is about 2 units tall):
 figure (stylized human, for characters/athletes/people), column, dome, arch, tower,
 pyramid, house, mountain, tree, planet (with ring + moon), lattice (3x3x3 atomic
 crystal with bonds), wave_field (two-source interference bars), particle_cloud,
 pitch (football pitch with goals and ball), open_book.
Prefabs use the same fields (id, kind, role, position, scale, rotation, material, action).
Never depict prophets, Imams or holy figures with a figure; use symbolic architecture,
light, calligraphic geometry, an open_book, a dome, columns or an arch instead.
""".strip()
