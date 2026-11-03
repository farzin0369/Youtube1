"""Caption-aware topic director for BAMO's CPU motion renderer."""
from __future__ import annotations

def plan_scene(caption: str, visual_prompt: str = "") -> dict[str, str]:
    text = f"{caption} {visual_prompt}".lower()
    # Specific subjects come first; generic metaphor rules must never steal them.
    rules = [
        (("دفتر", "نوشتن", "یادداشت", "ژورنال", "قلم", "کتاب", "notebook", "journal", "writing", "pen", "book"), "writing", "tracking",
         "An open three-dimensional notebook with turning pages and a luminous pen writing the key idea."),
        (("طلوع", "سپیده", "خورشید", "صبح", "آفتاب", "sunrise", "sun", "dawn"), "sunrise", "push_in",
         "A cinematic sunrise emerges over a layered horizon; rays spread as the camera pushes toward the light."),
        (("اتم", "الکترون", "پروتون", "نوترون", "atom", "electron", "proton", "neutron"), "atom", "orbit",
         "A scientific atomic model with a nucleus and distinct electron paths."),
        (("مولکول", "شیمی", "پیوند", "واکنش", "ماده", "molecule", "chemistry", "bond", "reaction"), "molecule", "tracking",
         "A molecular structure assembles from linked atoms; camera travels along the bonds."),
        (("انتخاب", "تصمیم", "دو راه", "دوراهی", "choice", "decision", "fork"), "choice_paths", "sweep",
         "Two clearly separated three-dimensional routes diverge toward different destinations; camera follows one route."),
        (("رشد", "پیشرفت", "ساخت", "آینده", "موفق", "growth", "progress", "future"), "growth_steps", "push_in",
         "A rising sequence of solid architectural steps builds upward as the camera cranes forward."),
        (("فیزیک", "موج", "نیرو", "ذره", "physics", "wave", "force", "particle"), "science", "tracking",
         "A physical wavefront and force vectors move through a measurable field."),
        (("هندسه", "زاویه", "دایره", "مکعب", "ریاضی", "geometry", "math", "number", "shape"), "geometry", "sweep",
         "A geometric construction assembles in three dimensions with a sweeping camera reveal."),
        (("مسیر", "راه", "سفر", "کوه", "جنگل", "تاریخ", "باستان", "journey", "mountain", "forest", "history", "ancient"), "journey", "tracking",
         "A dimensional pathway advances through a layered environment toward a visible destination."),
        (("امید", "نور", "ایمان", "قرآن", "دعا", "hope", "light", "faith", "quran", "prayer"), "sunrise", "push_in",
         "Warm light breaks across a cinematic horizon, revealing a hopeful destination."),
    ]
    for words, motif, camera, description in rules:
        if any(word in text for word in words):
            return {"motif": motif, "camera": camera, "description": description}
    return {"motif": "abstract", "camera": "orbit",
            "description": "A restrained abstract 3D transition; use only when no concrete subject can be identified."}
