#!/usr/bin/env python3
"""Render a BAMO hybrid motion-graphics project on a CPU runner."""
import argparse
from app.bamo_motion_engine import load_project, render_project

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project",required=True)
    parser.add_argument("--output",default="output/bamo/final.mp4")
    parser.add_argument("--audio",default=None)
    args=parser.parse_args()
    result=render_project(load_project(args.project),args.output,args.audio)
    print(f"[BAMO_RENDER_OK] {result} ({result.stat().st_size} bytes)",flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
