# BAMO 3D visual-review gate

A scene plan is not proof that the rendered image matches the narration. BAMO therefore
keeps 3D Shorts non-publishable until a reviewer inspects one real rendered frame from
each of the four authored scenes and records a review manifest.

## Required manifest

Place `visual-review.json` in the render output directory. Each `frame_path` is
relative to that directory or an absolute path to the actual rendered PNG frame.

```json
{
  "version": 1,
  "reviewer": "reviewer identity",
  "reviewed_at": "2026-11-02T10:00:00+03:30",
  "scenes": [
    {
      "scene_id": "scene-1",
      "visual_query": "the exact scene brief",
      "motif": "the Blender motif rendered",
      "camera_motion": "orbit",
      "frame_path": ".bamo-3d-silent_render/frames_000/frame_0001.png",
      "reviewed": true,
      "review_method": "human_frame_review",
      "alignment_score": 0.96
    }
  ]
}
```

The manifest must contain exactly four distinct scene IDs and four distinct valid image
frames. Every scene must be explicitly reviewed, have a score of at least 0.90, and
include its prompt, motif and camera motion. This is a human attestation, not an
automatically generated confidence score. Never manufacture or pre-fill approval.

The production environment variable `BAMO_PRODUCTION_VISUALS_APPROVED=true` is only
an additional opt-in. It cannot override a missing or invalid review manifest. A
successful Blender render, unit test or CI smoke run never constitutes visual approval.

For fully unattended publication, replace the human attestation with a separately
validated vision-based QA service that compares actual sampled frames against the
scene brief and narration. Until such a service is integrated and independently
validated, the safe behavior is to keep uploads blocked.
