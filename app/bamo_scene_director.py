"""Strict prompt-led scene director for BAMO's CPU 3D renderer.

The authored visual query has priority over narration keywords. Unknown or generic
queries fail closed instead of silently producing the same abstract scene.
"""
from __future__ import annotations


# Specific visual-query vocabulary is deliberately evaluated before narration.
# Each entry maps to a real Blender scene builder in scripts/bamo_blender_scene.py.
VISUAL_RULES = [
    (("wave interference", "interference pattern", "two wave sources", "constructive interference", "destructive interference", "تداخل موج", "تداخل دو موج", "موج های هم‌پوشان", "موج‌های همپوشان"),
     "wave_interference", "orbit",
     "Two distinct animated wave sources produce expanding wavefronts and a physically readable 3D interference field."),
    (("neon ellipse", "elliptical orbit", "orbiting particles", "geometric web", "luminous ellipse", "ellipse mesh", "بیضی نئونی", "مدار بیضوی", "نقاط نورانی", "شبکه هندسی"),
     "neon_ellipse_mesh", "orbit",
     "A luminous three-dimensional ellipse with orbiting particles, persistent curved light trails and a progressively denser chord mesh."),
    (("starfield", "night sky", "starry sky", "stars", "stellar", "آسمان شب", "ستاره", "ستارگان"),
     "starfield", "sweep",
     "A deep three-dimensional starfield above a curved planetary night horizon, with individually animated stars."),
    (("olbers", "cosmic shells", "star distribution", "astronomical shells", "پوسته های کیهانی", "پارادوکس اولبرس"),
     "cosmic_shells", "orbit",
     "Nested rotating three-dimensional shells populated by stars around a visible observer."),
    (("expanding spacetime", "expanding space", "redshift", "light rays", "انبساط فضا", "انتقال به سرخ"),
     "expanding_spacetime", "tracking",
     "An animated spacetime grid expands while luminous photon paths travel across it."),
    (("cosmic web", "galaxy clusters", "deep universe", "galaxies", "شبکه کیهانی", "کهکشان"),
     "cosmic_web", "orbit",
     "A volumetric cosmic web links glowing galaxy clusters with animated filaments."),
    (("diverging road", "two roads", "forked path", "two paths", "choice path"),
     "choice_paths", "sweep",
     "Two physically distinct roads split in opposite directions; the camera follows the fork."),
    (("neural", "synapse", "brain network", "neuronal"),
     "neural_network", "orbit",
     "A branching three-dimensional neural structure with linked synapses fills the frame."),
    (("writing in notebook", "open notebook", "hand writing", "notebook", "journal", "دفتر", "نوشتن", "یادداشت"),
     "notebook", "push_in",
     "An open three-dimensional notebook with visible pages, ruled lines and a moving pen."),
    (("ascending step", "golden steps", "staircase", "rising steps", "growth steps"),
     "growth_steps", "push_in",
     "A sequence of individually rising solid steps builds toward a higher platform."),
    (("sunrise", "sun rise", "dawn horizon", "radiant horizon", "sunset", "طلوع", "سپیده", "خورشید"),
     "sunrise", "push_in",
     "A luminous sun rises over a layered horizon with atmospheric rays and moving clouds."),
    (("atomic", "atom", "electron orbit", "atomic nucleus"),
     "atom", "orbit",
     "An atomic nucleus with animated electron orbits and distinct orbital planes."),
    (("molecule", "chemical bond", "molecular", "chemical structure"),
     "molecule", "tracking",
     "A molecular structure assembled from distinct atoms and visible chemical bonds."),
    (("geometric solid", "polyhedron", "icosphere", "geometric construction"),
     "geometry", "sweep",
     "A rotating precision geometric solid with visible wireframe and construction rings."),
    (("winding road", "mountain road", "journey path", "mountain trail"),
     "journey", "tracking",
     "A winding three-dimensional road travels through a mountainous environment toward a horizon."),
]

NARRATION_RULES = [
    (("اتم", "الکترون", "فیزیک", "ذره", "atom", "electron", "physics"), "atom", "orbit",
     "An atomic nucleus and animated electron orbits visualize the narrated physics concept."),
    (("مولکول", "شیمی", "پیوند شیمیایی", "molecule", "chemistry", "chemical bond"), "molecule", "tracking",
     "Distinct atoms connect through visible three-dimensional chemical bonds."),
    (("نورون", "سیناپس", "شبکه عصبی", "مغز", "neuron", "synapse", "neural"), "neural_network", "orbit",
     "A branching neural network forms as linked synapses pulse in sequence."),
    (("انتخاب", "تصمیم", "دو راه", "choice", "decision"), "choice_paths", "sweep",
     "Two physically separate paths diverge to represent the narrated decision."),
    (("نوشتن", "دفتر", "یادداشت", "writing", "notebook", "journal"), "notebook", "push_in",
     "An open notebook with visible pages, ruled lines and a moving pen visualizes writing."),
    (("رشد", "پیشرفت", "پله", "قدم کوچک", "عادت", "growth", "progress", "ascending", "habit"), "growth_steps", "push_in",
     "Solid three-dimensional steps rise one by one to represent progress."),
    (("طلوع", "سپیده", "خورشید", "sunrise", "dawn", "horizon"), "sunrise", "push_in",
     "A luminous sun rises over a layered horizon with atmospheric rays."),
    (("آغاز", "امید", "launch", "hope"), "launch", "push_in",
     "A cinematic energy portal opens to represent a new beginning."),
    (("کوه", "جنگل", "تاریخ", "باستان", "امپراتوری", "mountain", "forest", "ancient", "empire"), "journey", "tracking",
     "A winding path moves through a distinct ancient or natural environment."),
    (("هندسه", "زاویه", "دایره", "مکعب", "ریاضی", "geometry", "math", "polyhedron"), "geometry", "sweep",
     "A precision geometric solid rotates while construction rings reveal its structure."),
]


def _match(text: str, rules):
    normalized = " ".join(str(text or "").lower().replace("-", " ").split())
    for words, motif, camera, description in rules:
        if any(word in normalized for word in words):
            return {"motif": motif, "camera": camera, "description": description}
    return None


def plan_scene(caption: str, visual_prompt: str = "") -> dict[str, str]:
    prompt = str(visual_prompt or "").strip()
    if not prompt:
        raise ValueError("A specific per-scene visual_query is required; generic scenes are forbidden.")
    plan = _match(prompt, VISUAL_RULES)
    if plan:
        plan["matched_by"] = "visual_query"
        return plan
    plan = _match(caption, NARRATION_RULES)
    if plan:
        plan["matched_by"] = "narration"
        return plan
    raise ValueError(
        "No subject-specific 3D scene builder matches this visual_query/narration. "
        "Do not reuse an abstract template; author a matching Blender motif first."
    )
