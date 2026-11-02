"""BAMO Neon Manim prototype: procedural geometry, luminous trails and camera motion."""
from manim import *
import numpy as np

class NeonGeometryReference(MovingCameraScene):
    def construct(self):
        self.camera.background_color = "#030611"
        cyan, violet, gold, pink = "#62E8FF", "#B477FF", "#FFC66E", "#FF72C6"
        ellipse = Ellipse(width=4.4, height=7.2).set_stroke(cyan, width=2.8)
        self.add(ellipse.copy().set_stroke(cyan, width=12, opacity=0.10),
                 ellipse.copy().set_stroke(cyan, width=6, opacity=0.20), ellipse)
        orbit = Ellipse(width=3.65, height=6.1)
        dots = VGroup(*[
            Dot(orbit.point_from_proportion(k / 7), radius=0.065,
                color=[cyan, violet, gold, pink][k % 4]) for k in range(7)
        ])
        self.play(LaggedStart(*[FadeIn(d, scale=1.8) for d in dots], lag_ratio=0.12), run_time=1.2)
        rays = VGroup(*[
            Line(orbit.point_from_proportion(i / 7),
                 orbit.point_from_proportion((i + 3) / 7),
                 stroke_color=[violet, gold, pink][i % 3], stroke_width=2.0)
            for i in range(7)
        ])
        self.play(LaggedStart(*[Create(r) for r in rays], lag_ratio=0.10), run_time=2.2)
        dense = VGroup(*[
            Line(orbit.point_from_proportion(i / 7), orbit.point_from_proportion(j / 7),
                 stroke_color=violet if (i+j)%2 else cyan, stroke_width=1.1, stroke_opacity=0.52)
            for i in range(7) for j in range(i + 2, 7)
        ])
        self.play(Transform(rays, dense), run_time=2.0)
        focus = Dot(ORIGIN, radius=0.09, color=WHITE)
        spokes = VGroup(*[
            Line(ORIGIN, 2.75 * np.array([np.cos(a), np.sin(a), 0]),
                 stroke_color=gold, stroke_width=1.5, stroke_opacity=0.72)
            for a in np.linspace(0, TAU, 48, endpoint=False)
        ])
        self.play(FadeIn(focus), Create(spokes), run_time=2.0)
        self.play(self.camera.frame.animate.scale(0.88).move_to(UP * 0.15), run_time=2.5)
        self.play(Rotate(dots, angle=PI/3), Rotate(spokes, angle=-PI/8), run_time=3.0)
        self.wait(0.8)
