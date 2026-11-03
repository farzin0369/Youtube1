"""CPU-only Blender scene builder for BAMO's cinematic 3D motion engine.

Invoked by Blender's bundled Python, not the repository's system Python.
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector


def material(name, color, metallic=0.35, roughness=0.28, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    for key in ("Emission Color", "Emission"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = (*color, 1.0)
            break
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat
