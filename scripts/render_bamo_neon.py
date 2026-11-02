from pathlib import Path
import sys

# Running a script by path places scripts/ first on sys.path; add the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bamo_neon_engine import main

if __name__ == "__main__":
    main()
