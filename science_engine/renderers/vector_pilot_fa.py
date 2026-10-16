"""Educational black-hole visualization with layered pseudo-3D geometry."""
from manim import *


class VectorPilotFA(Scene):
    def construct(self):
        self.camera.background_color = "#030610"

        # Consistent typography and clear teaching hierarchy.
        title = Text("سیاه‌چاله؛ مرزِ بی‌بازگشت", font="Noto Sans Arabic",
                     font_size=30, weight=BOLD, color="#F5F7FF")
        subtitle = Text("افق رویداد چیست؟", font="Noto Sans Arabic",
                        font_size=21, color="#B8C7E8")
        title.to_edge(UP, buff=0.32)
        subtitle.next_to(title, DOWN, buff=0.10)
        self.play(FadeIn(title, shift=DOWN * 0.12), FadeIn(subtitle), run_time=0.8)

        # Deep-space background with restrained stars.
        stars = VGroup(*[
            Dot([((i * 17) % 17 - 8) * 0.72, ((i * 11) % 11 - 5) * 0.47, 0],
                radius=0.012 + (i % 3) * 0.004, color="#91A7D8")
            for i in range(72)
        ])
        self.add(stars)

        center = DOWN * 0.28
        # Accretion disk: stacked, tilted ellipses create a clear 3D perspective.
        disk_back = VGroup()
        for j, (w, h, col, sw) in enumerate([
            (4.35, 1.22, "#6C42FF", 12),
            (3.85, 1.04, "#FF5B35", 9),
            (3.28, 0.83, "#FFB44A", 7),
            (2.65, 0.62, "#FFF0B0", 3),
        ]):
            e = Ellipse(width=w, height=h, color=col, stroke_width=sw)
            e.set_stroke(opacity=0.24 if j == 0 else 0.82)
            e.move_to(center + UP * (0.12 + j * 0.015))
            disk_back.add(e)
        self.play(LaggedStart(*[Create(e) for e in disk_back], lag_ratio=0.12), run_time=1.3)

        # Event horizon and black core; nested rims make the boundary legible.
        outer_glow = Circle(radius=0.94, color="#7E67FF", stroke_width=18)
        outer_glow.set_stroke(opacity=0.22).move_to(center)
        photon_rim = Circle(radius=0.79, color="#FFC16A", stroke_width=3.5).move_to(center)
        horizon = Circle(radius=0.68, color="#11182A", stroke_width=5,
                         fill_color="#010207", fill_opacity=1).move_to(center)
        core = Circle(radius=0.59, color="#000000", stroke_width=1,
                      fill_color="#000000", fill_opacity=1).move_to(center)
        self.play(FadeIn(outer_glow), Create(photon_rim), FadeIn(horizon), FadeIn(core), run_time=1.0)

        # A labelled callout points to the horizon, not to a physical surface.
        pointer = Arrow(RIGHT * 3.0 + UP * 1.18, RIGHT * 0.60 + UP * 0.18,
                        color="#F5F7FF", stroke_width=2.5, buff=0.06)
        callout = Text("افق رویداد", font="Noto Sans Arabic", font_size=21,
                       color="#FFFFFF", weight=BOLD)
        callout.move_to(RIGHT * 3.02 + UP * 1.48)
        self.play(GrowArrow(pointer), FadeIn(callout), run_time=0.7)

        # Show a light ray escaping from outside, then a ray unable to escape
        # after crossing the horizon. Distinct colors reinforce the comparison.
        outside_start = LEFT * 3.15 + UP * 1.28
        outside_end = LEFT * 1.05 + UP * 0.62
        ray_out = Arrow(outside_start, outside_end, color="#58D9FF",
                        stroke_width=4, buff=0.05, max_tip_length_to_length_ratio=0.14)
        ray_label = Text("بیرون از افق: نور می‌تواند دور شود", font="Noto Sans Arabic",
                         font_size=17, color="#8BE8FF")
        ray_label.to_edge(DOWN, buff=0.54)
        self.play(GrowArrow(ray_out), FadeIn(ray_label), run_time=1.0)
        self.wait(0.6)

        inward_start = RIGHT * 2.45 + DOWN * 1.22
        inward_end = RIGHT * 0.38 + DOWN * 0.52
        ray_in = Arrow(inward_start, inward_end, color="#FF6A59",
                       stroke_width=4, buff=0.05, max_tip_length_to_length_ratio=0.14)
        crossed = Text("پس از عبور: راهِ بازگشت نیست", font="Noto Sans Arabic",
                       font_size=17, color="#FF9B8C")
        crossed.to_edge(DOWN, buff=0.54)
        self.play(GrowArrow(ray_in), Transform(ray_label, crossed), run_time=1.0)
        self.wait(1.0)

        # Final, memorable correction to a common misconception.
        myth = Text("سیاه‌چاله جاروبرقیِ کیهانی نیست", font="Noto Sans Arabic",
                    font_size=22, color="#F5F7FF", weight=BOLD)
        myth.to_edge(DOWN, buff=0.48)
        self.play(FadeOut(ray_in), FadeOut(pointer), FadeOut(callout),
                  FadeOut(ray_label), FadeIn(myth), run_time=0.8)
        self.wait(1.8)
