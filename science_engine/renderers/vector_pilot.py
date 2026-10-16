"""Short, self-contained Manim pilot: vectors as the language of 3D space.

Render from the repository root with:
    manim -pql science_engine/renderers/vector_pilot.py VectorPilot

This is a preview scene, not part of the existing upload pipeline.
"""
from manim import *


class VectorPilot(Scene):
    def construct(self):
        self.camera.background_color = "#070B18"

        title = Text("THE HIDDEN LANGUAGE OF 3D", font_size=30, weight=BOLD, color="#F4F7FF")
        subtitle = Text("One idea can describe direction and magnitude", font_size=17, color="#AAB8D6")
        title.to_edge(UP, buff=0.42)
        subtitle.next_to(title, DOWN, buff=0.12)
        self.play(FadeIn(title, shift=DOWN * 0.15), FadeIn(subtitle), run_time=1.1)

        axes = Axes(
            x_range=[-3, 3, 1], y_range=[-2, 2, 1],
            x_length=7.0, y_length=4.0,
            axis_config={"color": "#45516D", "stroke_width": 2, "include_ticks": False},
            tips=True,
        ).shift(DOWN * 0.45)
        grid = NumberPlane(
            x_range=[-3, 3, 1], y_range=[-2, 2, 1],
            x_length=7.0, y_length=4.0,
            background_line_style={"stroke_color": "#26324D", "stroke_opacity": 0.45, "stroke_width": 1},
            axis_config={"stroke_opacity": 0},
        ).shift(DOWN * 0.45)
        self.play(Create(grid), Create(axes), run_time=1.0)

        origin = axes.c2p(0, 0)
        tip_a = axes.c2p(2.2, 1.2)
        tip_b = axes.c2p(-0.8, 1.1)
        a = Arrow(origin, tip_a, buff=0, color="#55D6FF", stroke_width=6, max_tip_length_to_length_ratio=0.12)
        b = Arrow(origin, tip_b, buff=0, color="#FFB86B", stroke_width=6, max_tip_length_to_length_ratio=0.15)
        label_a = MathTex(r"\vec{a}", color="#55D6FF", font_size=36).next_to(a.get_tip(), UR, buff=0.08)
        label_b = MathTex(r"\vec{b}", color="#FFB86B", font_size=36).next_to(b.get_tip(), UL, buff=0.08)
        self.play(GrowArrow(a), FadeIn(label_a), run_time=0.8)
        self.play(GrowArrow(b), FadeIn(label_b), run_time=0.8)

        tip_sum = axes.c2p(1.4, 2.3)
        sum_arrow = Arrow(origin, tip_sum, buff=0, color="#B8F36B", stroke_width=7, max_tip_length_to_length_ratio=0.1)
        ghost_a = DashedLine(axes.c2p(-0.8, 1.1), tip_sum, color="#FFB86B", dash_length=0.09, stroke_opacity=0.85)
        ghost_b = DashedLine(axes.c2p(2.2, 1.2), tip_sum, color="#55D6FF", dash_length=0.09, stroke_opacity=0.85)
        sum_label = MathTex(r"\vec{a}+\vec{b}", color="#B8F36B", font_size=32).next_to(sum_arrow.get_tip(), RIGHT, buff=0.12)
        self.play(Create(ghost_a), Create(ghost_b), run_time=0.55)
        self.play(GrowArrow(sum_arrow), FadeIn(sum_label), run_time=0.9)

        formula = MathTex(r"\vec{a}=(a_x,a_y)", r"\qquad", r"\vec{b}=(b_x,b_y)", color="#F4F7FF", font_size=32)
        formula.to_edge(DOWN, buff=0.42)
        formula[0].set_color("#55D6FF")
        formula[2].set_color("#FFB86B")
        self.play(FadeIn(formula, shift=UP * 0.15), run_time=0.8)
        self.wait(0.7)

        final = Text("Add the components. Predict the motion.", font_size=23, weight=BOLD, color="#B8F36B")
        final.to_edge(DOWN, buff=0.38)
        self.play(FadeOut(formula), FadeIn(final, shift=UP * 0.12), run_time=0.7)
        self.wait(1.2)
