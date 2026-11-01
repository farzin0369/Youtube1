# BAMO specialist render architecture

## Decision flow

The eleven BAMO production roles hand a structured decision to the visual
director: `genre`, `visual_brief`, `narration`, scene plan, aspect ratio,
duration and factual constraints. The director calls
`app.bamo_engine_router.validate_agent_decision` and routes the job to the
genre's specialist renderer.

| Content | Primary renderer | Supporting engines |
|---|---|---|
| Mathematics / proofs | Manim Community | Motion Canvas, HyperFrames |
| Geometry | Manim Community | Three.js, Blender |
| Physics | Manim Community | PyVista, Blender |
| Chemistry / molecules | RDKit | Blender, Three.js |
| General science | PyVista | Three.js, Manim |
| Humor / comedy / characters | Blender | Motion Canvas, HyperFrames |
| Cinematic 3D / history / symbolic scenes | Blender | Three.js, Motion Canvas |
| Sports | Blender | Three.js, Motion Canvas |
| Data / infographic / typography | Three.js or Motion Canvas | HyperFrames |

FFmpeg is the final encoder and audio/video muxer. HyperFrames is intended for
HTML/CSS-based composition and overlays; it is not a replacement for a
scientific or 3D scene renderer.

## Important execution rules

1. Detect the primary renderer before scene production.
2. Never route a math brief to a generic stock-footage template or a comedy
   brief to a scientific visualization.
3. If the primary renderer is missing, stop that render job with a clear
   install/readiness error. A supporting engine may be used only when the
   director explicitly approves that alternative for the scene.
4. Every scene carries its own subject, action, camera, style and narration
   alignment metadata. Run semantic and technical QA before accepting output.
5. Keep renderers optional and lazily installed. Do not install every large
   graphics stack on every daily GitHub Actions CPU run.
6. GitHub Actions CPU is for tests and lightweight previews. Full Blender and
   specialist production renders may require a separately available Colab GPU
   session; this design does not claim GitHub CPU can deliver fast cinematic
   renders.
7. The workflow remains preview-only. No YouTube upload, merge, or activation
   is performed by this change.

## Engine repositories

- Blender: https://github.com/blender/blender
- Manim Community: https://github.com/ManimCommunity/manim
- Three.js: https://github.com/mrdoob/three.js
- Motion Canvas: https://github.com/motion-canvas/motion-canvas
- HyperFrames: https://github.com/heygen-com/hyperframes
- PyVista: https://github.com/pyvista/pyvista
- RDKit: https://github.com/rdkit/rdkit

The router performs runtime availability detection. Adding a repository to this
registry does not mean the package has been installed or that a production
adapter has already been implemented. Each engine adapter must be exercised by
a real render test before it is marked production-ready.
