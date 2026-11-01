"""Caption-aware deterministic scene director for BAMO's CPU 3D renderer.

Maps authored captions to visual metaphors and camera moves. Explicit visual_prompt
adds direction; captions are never rewritten by this module.
"""
from __future__ import annotations

def plan_scene(caption: str, visual_prompt: str = "") -> dict[str, str]:
    text = f"{caption} {visual_prompt}".lower()
    rules = [
        (("شروع", "آغاز", "همین حالا", "start", "begin"), "launch", "push_in",
         "A luminous three-dimensional portal opens and a rising arrow signals the first decisive action."),
        (("انتخاب", "تصمیم", "دو راه", "choice", "decision"), "choice_paths", "sweep",
         "Two distinct three-dimensional paths diverge; camera tracks the chosen route."),
        (("قدم", "مسیر", "راه", "سفر", "journey", "step"), "journey", "tracking",
         "A dimensional pathway advances toward a visible destination; camera follows it."),
        (("رشد", "پیشرفت", "ساخت", "آینده", "موفق", "growth", "progress", "future"), "growth_steps", "push_in",
         "A rising sequence of solid 3D steps builds upward as the camera cranes forward."),
        (("مغز", "عصب", "نورون", "سیناپس", "brain", "neural", "neuron", "synapse"), "neural_network", "orbit",
         "A living neural network forms from linked glowing synapses; the camera dives through the branching connections."),
        (("اتم", "الکترون", "فیزیک", "ذره", "atom", "physics"), "atom", "orbit",
         "Scientific orbital geometry with a controlled camera orbit."),
        (("مولکول", "شیمی", "پیوند", "ماده", "molecule", "chemistry"), "molecule", "tracking",
         "A connected molecular structure forms from linked 3D nodes; camera travels along bonds."),
        (("هندسه", "زاویه", "دایره", "مکعب", "ریاضی", "geometry", "math", "number", "shape"), "geometry", "sweep",
         "A geometric construction assembles in 3D with a sweeping camera reveal."),
        (("فکر", "ذهن", "باران", "پنجره", "thinking", "mind", "rain", "window", "decision"), "choice_paths", "sweep",
         "Two dimensional routes separate and converge as the camera sweeps along the selected direction."),
        (("دفتر", "نوشتن", "یادداشت", "ژورنال", "notebook", "journal", "writing", "task"), "growth_steps", "tracking",
         "A sequence of solid steps assembles from a written intention; camera tracks forward."),
        (("طلوع", "سپیده", "خورشید", "نور", "امید", "sunrise", "sun", "light", "hope", "prayer", "quran", "faith"), "launch", "push_in",
         "A luminous portal and rising light form a hopeful three-dimensional reveal."),
        (("کوه", "جنگل", "تاریخ", "باستان", "امپراتوری", "mountain", "forest", "history", "ancient", "empire"), "journey", "tracking",
         "A dimensional path advances toward a distant horizon; camera follows the route."),
    ]
    for words, motif, camera, description in rules:
        if any(word in text for word in words):
            return {"motif": motif, "camera": camera, "description": description}
    return {"motif": "abstract", "camera": "orbit",
            "description": "A restrained 3D metaphor derived from the caption, with a cinematic orbit."}
