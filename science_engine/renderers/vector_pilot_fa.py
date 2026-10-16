"""Persian-language short visual pilot: vector addition, with clean math graphics."""
from manim import *


class VectorPilotFA(Scene):
    def construct(self):
        self.camera.background_color = "#070B18"
        title = Text("بردارها؛ زبان پنهان حرکت", font="Noto Sans Arabic", font_size=32, weight=BOLD, color="#F4F7FF")
        subtitle = Text("دو ویژگی مهم", font="Noto Sans Arabic", font_size=23, color="#AAB8D6")
        title.to_edge(UP, buff=0.42)
        subtitle.next_to(title, DOWN, buff=0.15)
        self.play(FadeIn(title, shift=DOWN * 0.15), FadeIn(subtitle), run_time=1.5)
        self.wait(1.4)

        axes = Axes(
            x_range=[-3, 3, 1], y_range=[-2, 2, 1],
            x_length=7.0, y_length=3.8,
            axis_config={"color": "#45516D", "stroke_width": 2, "include_ticks": False},
            tips=True,
        ).shift(DOWN * 0.55)
        grid = NumberPlane(
            x_range=[-3, 3, 1], y_range=[-2, 2, 1],
            x_length=7.0, y_length=3.8,
            background_line_style={"stroke_color": "#26324D", "stroke_opacity": 0.45, "stroke_width": 1},
            axis_config={"stroke_opacity": 0},
        ).shift(DOWN * 0.55)
        self.play(Create(grid), Create(axes), run_time=2.0)
        self.wait(0.8)

        origin = axes.c2p(0, 0)
        arrow_a = Arrow(origin, axes.c2p(2.2, 1.0), buff=0, color="#55D6FF", stroke_width=6, max_tip_length_to_length_ratio=0.12)
        arrow_b = Arrow(origin, axes.c2p(-0.8, 1.0), buff=0, color="#FFB86B", stroke_width=6, max_tip_length_to_length_ratio=0.15)
        label_a = MathTex(r"\vec{a}", color="#55D6FF", font_size=36).next_to(arrow_a.get_tip(), UR, buff=0.08)
        label_b = MathTex(r"\vec{b}", color="#FFB86B", font_size=36).next_to(arrow_b.get_tip(), UL, buff=0.08)
        self.play(GrowArrow(arrow_a), FadeIn(label_a), run_time=1.4)
        self.wait(0.8)
        self.play(GrowArrow(arrow_b), FadeIn(label_b), run_time=1.4)
        self.wait(1.0)

        sum_tip = axes.c2p(1.4, 2.0)
        ghost_a = DashedLine(axes.c2p(-0.8, 1.0), sum_tip, color="#FFB86B", dash_length=0.09, stroke_opacity=0.85)
        ghost_b = DashedLine(axes.c2p(2.2, 1.0), sum_tip, color="#55D6FF", dash_length=0.09, stroke_opacity=0.85)
        sum_arrow = Arrow(origin, sum_tip, buff=0, color="#B8F36B", stroke_width=7, max_tip_length_to_length_ratio=0.1)
        sum_label = MathTex(r"\vec{a}+\vec{b}", color="#B8F36B", font_size=32).next_to(sum_arrow.get_tip(), RIGHT, buff=0.12)
        self.play(Create(ghost_a), Create(ghost_b), run_time=1.0)
        self.play(GrowArrow(sum_arrow), FadeIn(sum_label), run_time=1.4)
        self.wait(1.8)

        formula = MathTex(r"\vec{a}=(a_x,a_y)", r"\qquad", r"\vec{b}=(b_x,b_y)", color="#F4F7FF", font_size=31)
        formula.to_edge(DOWN, buff=0.4)
        formula[0].set_color("#55D6FF")
        formula[2].set_color("#FFB86B")
        self.play(FadeIn(formula, shift=UP * 0.15), run_time=1.2)
        self.wait(2.2)

        final = Text("مؤلفه‌ها را جمع کن؛ نتیجه را پیش‌بینی کن", font="Noto Sans Arabic", font_size=25, weight=BOLD, color="#B8F36B")
        final.to_edge(DOWN, buff=0.35)
        self.play(FadeOut(formula), FadeIn(final, shift=UP * 0.12), run_time=1.2)
        self.wait(4.0)
