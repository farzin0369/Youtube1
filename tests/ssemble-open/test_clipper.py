import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).parents[2] / "ssemble-open" / "clipper.py"
spec = importlib.util.spec_from_file_location("clipper", MODULE)
clipper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clipper)

class ClipInputTests(unittest.TestCase):
    def test_module_has_main(self):
        self.assertTrue(callable(clipper.main))

if __name__ == "__main__":
    unittest.main()
