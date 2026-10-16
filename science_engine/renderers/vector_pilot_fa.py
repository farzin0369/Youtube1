"""Cinematic 3D educational black-hole scene; narration beats align to SRT."""
from manim import *
import numpy as np


class VectorPilotFA(ThreeDScene):
    def construct(self):
        self.camera.background_color = "#02040B"
        self.set_camera_orientation(phi=67 * DEGREES, theta=-52 * DEGREES, zoom=0.92)

        # Deep-space star field in 3D, fixed for the whole journey.
        stars = VGroup()
        for i in range(110):
            x = ((i * 37) % 101 - 50) / 7
            y = ((i * 23) % 67 - 33) / 8
            z = ((i * 13) % 29 - 14) / 5
            stars.add(Dot3D(point=[x, y, z], radius=0.018, color="#8FA9E8"))
        self.add(stars)

        title = Text("سیاه‌چاله؛ مرزِ بی‌بازگشت", font="Noto Sans Arabic",
                     font_size=29, weight=BOLD, color="#F5F7FF")
        subtitle = Text("سفر به افق رویداد", font="Noto Sans Arabic",
                        font_size=19, color="#B8C7E8")
        title.to_edge(UP, buff=0.25)
        subtitle.next_to(title, DOWN, buff=0.08)
        self.add_fixed_in_frame_mobjects(title, subtitle)
        self.play(FadeIn(title), FadeIn(subtitle), run_time=0.8)

        # A genuinely volumetric black core, glowing photon rim, and tilted
        # accretion rings. Colors and relative scale are explanatory, not literal.
        core = Sphere(radius=1.0, resolution=(32, 64))
        core.set_color("#010207").set_opacity(1)
        core.set_shade_in_3d(True)
        photon = Torus(major_radius=1.18, minor_radius=0.035,
                       resolution=(16, 80), color="#FFC16A")
        photon.rotate(68 * DEGREES, axis=RIGHT)
        photon.set_shade_in_3d(True)
        horizon = Torus(major_radius=1.01, minor_radius=0.055,
                        resolution=(16, 80), color="#8C75FF")
        horizon.rotate(68 * DEGREES, axis=RIGHT)
        horizon.set_opacity(0.65)
        disk = VGroup()
        for radius, minor, color, opacity in [
            (1.52, 0.12, "#FF5B35", 0.82),
            (1.82, 0.085, "#FFB44A", 0.72),
            (2.13, 0.045, "#6C42FF", 0.55),
        ]:
            ring = Torus(major_radius=radius, minor_radius=minor,
                         resolution=(12, 72), color=color)
            ring.rotate(68 * DEGREES, axis=RIGHT)
            ring.set_opacity(opacity).set_shade_in_3d(True)
            disk.add(ring)

        self.play(FadeIn(core), Create(horizon), Create(photon), run_time=2.0)
        self.play(LaggedStart(*[Create(r) for r in disk], lag_ratio=0.18), run_time=2.0)
        self.begin_ambient_camera_rotation(rate=0.035)
        self.wait(1.2)  # 0-4.5s: hook — a boundary light cannot cross back.

        # 4.5-8s: identify the event horizon with a stable screen label.
        label1 = Text("افق رویداد: مرزِ بازگشت‌ناپذیر", font="Noto Sans Arabic",
                      font_size=21, color="#FFFFFF", weight=BOLD)
        label1.to_edge(DOWN, buff=0.42)
        self.add_fixed_in_frame_mobjects(label1)
        self.play(FadeIn(label1), run_time=0.5)
        self.wait(2.2)
        self.play(FadeOut(label1), run_time=0.35)

        # 8-14s: distinguish the horizon from a solid surface.
        label2 = Text("این یک سطحِ جامد نیست؛ مرزی در فضا-زمان است", 
                      font="Noto Sans Arabic", font_size=19, color="#BFEAFF")
        label2.to_edge(DOWN, buff=0.42)
        self.add_fixed_in_frame_mobjects(label2)
        self.play(FadeIn(label2), run_time=1.0)
        self.move_camera(zoom=1.02, run_time=1.0)
        self.wait(3.2)
        self.play(FadeOut(label2), run_time=0.35)

        # 14-20s: show a light path outside the horizon bending around the core.
        path = ParametricFunction(
            lambda t: np.array([-3.2 + 5.0*t, 1.35 + 0.32*np.sin(t*PI*1.2), 0.45]),
            t_range=[0, 1], color="#58D9FF", stroke_width=5)
        raydot = Dot3D(point=path.get_start(), radius=0.075, color="#A8F4FF")
        label3 = Text("بیرون از افق، نور می‌تواند دور شود", font="Noto Sans Arabic",
                      font_size=19, color="#8BE8FF")
        label3.to_edge(DOWN, buff=0.42)
        self.add_fixed_in_frame_mobjects(label3)
        self.play(Create(path), FadeIn(raydot), FadeIn(label3), run_time=2.0)
        self.play(MoveAlongPath(raydot, path), run_time=2.4, rate_func=linear)
        self.wait(1.0)
        self.play(FadeOut(path), FadeOut(raydot), FadeOut(label3), run_time=0.4)

        # 20-25s: a second ray crosses the boundary; the camera continues moving.
        inward = ParametricFunction(
            lambda t: np.array([3.1 - 2.55*t, -1.2 + 0.55*t, 0.2 + 0.12*t]),
            t_range=[0, 1], color="#FF6A59", stroke_width=5)
        inward_dot = Dot3D(point=inward.get_start(), radius=0.075, color="#FF9B8C")
        label4 = Text("پس از عبور از افق، راهِ بازگشت به بیرون نیست", 
                      font="Noto Sans Arabic", font_size=18, color="#FFB0A4")
        label4.to_edge(DOWN, buff=0.42)
        self.add_fixed_in_frame_mobjects(label4)
        self.play(Create(inward), FadeIn(inward_dot), FadeIn(label4), run_time=1.5)
        self.play(MoveAlongPath(inward_dot, inward), run_time=2.2, rate_func=linear)
        self.wait(0.8)
        self.play(FadeOut(inward), FadeOut(inward_dot), FadeOut(label4), run_time=0.4)

        # 25-31s: pull back and make the misconception correction visual.
        self.move_camera(zoom=0.94, run_time=1.0)
        label5 = Text("سیاه‌چاله از دور، جاروبرقیِ کیهانی نیست", 
                      font="Noto Sans Arabic", font_size=22, color="#F5F7FF", weight=BOLD)
        label5.to_edge(DOWN, buff=0.42)
        self.add_fixed_in_frame_mobjects(label5)
        self.play(FadeIn(label5), run_time=0.5)
        self.wait(4.2)
        self.play(FadeOut(label5), run_time=0.4)

        # 31-38s: concluding image remains alive while the final narration finishes.
        ending = Text("شگفتیِ آن، هندسهٔ فضا و زمان است", font="Noto Sans Arabic",
                      font_size=23, color="#FFC16A", weight=BOLD)
        ending.to_edge(DOWN, buff=0.42)
        self.add_fixed_in_frame_mobjects(ending)
        self.play(FadeIn(ending), run_time=0.7)
        self.wait(7.0)
        self.stop_ambient_camera_rotation()
