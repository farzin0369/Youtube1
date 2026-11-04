#!/usr/bin/env python3
from pathlib import Path
path = Path("app/spiritual_video.py")
text = path.read_text(encoding="utf-8")
old = """PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Noto Naskh Arabic,48,&H00FFFFFF,&H0000FFFF,&H99000000,&HAA111924,-1,0,0,0,100,100,0,0,3,10,0,2,50,50,220,1
Style: Hook,Noto Naskh Arabic,56,&H003EC9FF,&H0000FFFF,&H99000000,&HAA111924,-1,0,0,0,100,100,0,0,3,10,0,8,46,46,300,1
"""
new = """PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Noto Naskh Arabic,54,&H00FFFFFF,&H0000FFFF,&H99000000,&HAA111924,-1,0,0,0,100,100,0,0,3,12,1,2,64,64,260,1
Style: Hook,Noto Naskh Arabic,64,&H003EC9FF,&H0000FFFF,&H99000000,&HAA111924,-1,0,0,0,100,100,0,0,3,12,1,8,56,56,340,1
Style: Emphasis,Noto Naskh Arabic,58,&H00D5A64B,&H0000FFFF,&H99000000,&HAA111924,-1,0,0,0,100,100,0,0,3,12,1,2,64,64,260,1
"""
if old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("ASS PlayRes patched to 1080x1920")
elif "PlayResX: 1080" in text:
    print("already patched")
else:
    raise SystemExit("PlayRes block not found")
compile(path.read_text(encoding="utf-8"), str(path), "exec")
