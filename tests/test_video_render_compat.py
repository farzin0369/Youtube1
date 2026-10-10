from PIL import Image

# Importing the renderer applies the compatibility alias required by MoviePy 1.x.
import app.video_render  # noqa: F401


def test_moviepy_legacy_antialias_alias_is_available():
    assert Image.ANTIALIAS == Image.Resampling.LANCZOS
