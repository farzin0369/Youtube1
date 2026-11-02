        "scene_timings": scene_timings,
        "delivery_profiles": delivery_log,
        "ok": True,
        "scene_timings": scene_timings,
        # Preserve provider-measured boundaries so the renderer can synchronize
        # emphasis and scene events against the actual spoken audio clock.
        "word_events": [
            {
                "text": str(event.get("text") or "").strip(),
                "start": round(int(event.get("offset") or 0) / TICKS_PER_SECOND, 4),
                "end": round((int(event.get("offset") or 0) + int(event.get("duration") or 0)) / TICKS_PER_SECOND, 4),
            }
            for event in all_events
            if str(event.get("text") or "").strip()
        ],
        "delivery_profiles": delivery_log,
        "ok": True,
