"""Persian science short: why a black hole's event horizon is not a solid surface."""
from manim import *


class VectorPilotFA(Scene):
    def construct(self):
        self.camera.background_color = "#050711"
        title = Text("سیاه‌چاله؛ مرزِ بی‌بازگشت", font="Noto Sans Arabic", font_size=31, weight=BOLD, color="#F4F7FF")
        subtitle = Text("افق رویداد چیست؟", font="Noto Sans Arabic", font_size=23, color="#AAB8D6")
        title.to_edge(UP, buff=0.42)
        subtitle.next_to(title, DOWN, buff=0.15)
        self.play(FadeIn(title, shift=DOWN * 0.15), FadeIn(subtitle), run_time=1.2)

        stars = VGroup(*[
            Dot([((i * 17) % 13 - 6) * 0.72, ((i * 11) % 9 - 4) * 0.48, 0],
                radius=0.018, color="#AAB8D6")
            for i in range(45)
        ])
        self.play(FadeIn(stars), run_time=0.7)

        glow = Circle(radius=1.45, color="#6A5CFF", stroke_width=10).set_stroke(opacity=0.20)
        ring = Circle(radius=1.18, color="#FFB86B", stroke_width=5)
        inner_ring = Circle(radius=0.94, color="#55D6FF", stroke_width=2).set_stroke(opacity=0.55)
        hole = Circle(radius=0.78, color="#000000", fill_opacity=1, stroke_color="#0A0B16", stroke_width=3)
        hole.move_to(DOWN * 0.35)
        glow.move_to(hole.get_center())
        ring.move_to(hole.get_center())
        inner_ring.move_to(hole.get_center())
        self.play(FadeIn(glow), Create(ring), Create(inner_ring), run_time=1.6)
        self.play(FadeIn(hole), run_time=0.8)

        orbit = Circle(radius=1.8, color="#AAB8D6", stroke_width=1.5).set_stroke(opacity=0.35)
        orbit.move_to(hole.get_center())
        dot = Dot(orbit.point_from_proportion(0.08), radius=0.075, color="#F4F7FF")
        self.play(Create(orbit), FadeIn(dot), run_time=0.7)
        self.play(MoveAlongPath(dot, orbit), run_time=3.0, rate_func=linear)
        self.play(FadeOut(orbit), FadeOut(dot), run_time=0.4)

        arrow = Arrow(UP * 2.35 + RIGHT * 2.9, DOWN * 0.2 + RIGHT * 0.65, color="#FFB86B", stroke_width=5, buff=0.05)
        label = Text("مرزِ گریزناپذیر", font="Noto Sans Arabic", font_size=22, color="#FFB86B")
        label.next_to(arrow, RIGHT, buff=0.12)
        self.play(GrowArrow(arrow), FadeIn(label), run_time=1.0)

        note = Text("حتی نور هم از درون آن بیرون نمی‌آید", font="Noto Sans Arabic", font_size=23, color="#F4F7FF")
        note.to_edge(DOWN, buff=0.45)
        self.play(FadeIn(note, shift=UP * 0.12), run_time=0.8)
        self.wait(2.0)
