# First visual pilot

The pilot uses Manim Community Edition for deterministic, mathematically accurate motion graphics. Manim is an open-source animation framework and can be used in Jupyter/Google Colab as well as local environments: https://docs.manim.community/en/stable/

## Render locally or in a separate Colab cell

Install Manim and its system dependencies according to the official guide, then run from the repository root:

```bash
manim -pql science_engine/renderers/vector_pilot.py VectorPilot
```

- `-pql` renders a low-quality draft and opens it in a local preview-capable environment.
- For a sharper final, use `-pqh` only after the draft is visually checked.
- This scene is deliberately not wired to YouTube upload, scheduled publishing, or any existing pipeline.
- Review typography, timing, color contrast, and scientific narration before production use.

This is an English visual proof-of-concept. The final channel language and Persian RTL typography need to be chosen and tested explicitly before a public-quality episode.
