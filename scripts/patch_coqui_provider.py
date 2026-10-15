#!/usr/bin/env python3
"""Force Coqui-first synthesis even if env TTS_PROVIDER=piper."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "app" / "spiritual_tts.py"
t = p.read_text(encoding="utf-8")

if "coqui-first-v2" in t:
    print("NOOP")
else:
    # After provider resolved, remap piper -> coqui (natural male)
    anchor = "    if provider not in {\"edge-tts\", \"elevenlabs\", \"piper\", \"coqui\", \"vits\"}:  # coqui-vits-v1"
    if anchor not in t:
        anchor = "    if provider not in {\"edge-tts\", \"elevenlabs\", \"piper\", \"coqui\", \"vits\"}:"
    inject_after = """    if provider not in {"edge-tts", "elevenlabs", "piper", "coqui", "vits"}:  # coqui-vits-v1
        raise ValueError(f"unsupported TTS_PROVIDER: {provider}")
    # coqui-first-v2: env may still say piper; upgrade to natural male VITS
    if provider == "piper" and __import__("os").getenv("FORCE_PIPER", "").lower() not in {"1", "true", "yes"}:
        provider = "coqui"
    return provider
"""
    # Replace whole end of _provider function carefully
    import re
    t2, n = re.subn(
        r"    if provider not in \{[^}]+\}:.*?\n        raise ValueError\(f\"unsupported TTS_PROVIDER: \{provider\}\"\)\n    return provider\n",
        inject_after,
        t,
        count=1,
        flags=re.S,
    )
    if n:
        t = t2
        print("REMAP_OK")
    else:
        # fallback insert before return provider in _provider
        if "return provider" in t and "coqui-first-v2" not in t:
            t = t.replace(
                "    return provider\n",
                "    # coqui-first-v2\n"
                "    if provider == \"piper\" and __import__(\"os\").getenv(\"FORCE_PIPER\", \"\").lower() not in {\"1\", \"true\", \"yes\"}:\n"
                "        provider = \"coqui\"\n"
                "    return provider\n",
                1,
            )
            print("REMAP_FALLBACK")
        else:
            print("REMAP_FAIL")

    # ensure coqui branch exists
    if "synthesize_coqui" not in t:
        needle = '                elif provider == "piper":'
        inject = '''                elif provider in {"coqui", "vits"}:
                    from app.coqui_tts import synthesize_coqui
                    try:
                        synthesize_coqui(chunk_text, chunk_wav, mood=str(mood or "calm"))
                    except Exception as coqui_exc:
                        logger.warning("coqui failed (%s); falling back to piper", type(coqui_exc).__name__)
                        from app.piper_tts import synthesize_piper
                        synthesize_piper(chunk_text, chunk_wav, mood=str(mood or "calm"))
                elif provider == "piper":'''
        if needle in t:
            t = t.replace(needle, inject, 1)
            print("BRANCH_OK")

    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("DONE")

# requirements
req = ROOT / "requirements.txt"
rt = req.read_text(encoding="utf-8")
if "TTS" not in rt:
    req.write_text(rt.rstrip() + "\nTTS>=0.22.0\n", encoding="utf-8")
    print("REQ")
