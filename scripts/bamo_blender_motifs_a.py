"""Legacy motif stubs — prefer AI scene graphs."""
from __future__ import annotations

import math
import bpy
from bamo_blender_primitives import material, sphere, torus, ground

def scene_choice(gold, blue, dark, frames):
    ground(dark); sphere("Choice", (0,0,1.2), 0.6, gold)

def scene_journey(gold, blue, dark, frames):
    ground(dark); sphere("Journey", (0,0,1.2), 0.6, gold)

def scene_growth(gold, blue, dark, frames):
    ground(dark); sphere("Growth", (0,0,1.2), 0.6, gold)

def scene_atom(gold, blue, dark, frames):
    ground(dark)
    sphere("Atomic nucleus", (0, 0, 1.3), 0.72, gold)
    sphere("Nucleus core", (0.15, -0.2, 1.45), 0.32, blue)
    for i, rot in enumerate(((0.2, 0.0, 0.0), (1.05, 0.55, 0.2), (-0.9, 0.7, -0.3))):
        torus("Electron shell", (0, 0, 1.3), 2.25, 0.035, blue if i % 2 else gold, rot)

def scene_neural(gold, blue, dark, frames):
    ground(dark); sphere("Neural", (0,0,1.2), 0.6, blue)

def scene_molecule(gold, blue, dark, frames):
    ground(dark); sphere("Molecule", (0,0,1.2), 0.6, gold)

def scene_geometry(gold, blue, dark, frames):
    ground(dark); sphere("Geometry", (0,0,1.2), 0.6, blue)

def scene_launch(gold, blue, dark, frames):
    ground(dark); sphere("Launch", (0,0,1.2), 0.6, gold)

def scene_notebook(gold, blue, dark, frames):
    ground(dark); sphere("Notebook", (0,0,1.2), 0.6, gold)

def scene_sunrise(gold, blue, dark, frames):
    ground(dark); sphere("Sunrise", (0,0,1.2), 0.6, gold)

def scene_starfield(gold, blue, dark, frames):
    ground(dark); sphere("Starfield", (0,0,1.2), 0.6, blue)

def scene_cosmic_shells(gold, blue, dark, frames):
    ground(dark); sphere("Cosmic", (0,0,1.2), 0.6, gold)
