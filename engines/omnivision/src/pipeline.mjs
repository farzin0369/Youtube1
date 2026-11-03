import { planVideo } from "./planner.mjs";
import { compileSceneGraph, validateSceneGraph } from "./scene-graph.mjs";
import { compileTimeline, validateTimeline } from "./timeline.mjs";

/**
 * Joins the approved narration plan to provider-measured Persian TTS timings.
 * Scene timing comes from TTS metadata; no equal-duration or guessed word timing.
 */
export function compileAudioVisualPipeline(script, ttsResult, { aspect = "9:16" } = {}) {
  if (!ttsResult || ttsResult.ok !== true) throw new Error("A successful TTS result is required");
  const audioDuration = Number(ttsResult.duration_seconds);
  const sceneTimings = ttsResult.scene_timings;
  if (!Array.isArray(sceneTimings) || !sceneTimings.length) throw new Error("TTS scene timings are required");
  if (!Array.isArray(ttsResult.word_events) || !ttsResult.word_events.length) throw new Error("Measured TTS word events are required");
  const plan = planVideo(script, { duration: audioDuration, aspect });
  if (plan.scenes.length !== sceneTimings.length) throw new Error("TTS scene count does not match approved narration segmentation");
  const scenes = plan.scenes.map((scene, index) => ({
    ...scene,
    start: Number(sceneTimings[index].start_seconds),
    end: Number(sceneTimings[index].end_seconds)
  }));
  for (let i = 0; i < scenes.length; i++) {
    if (!Number.isFinite(scenes[i].start) || !Number.isFinite(scenes[i].end) || scenes[i].end <= scenes[i].start) {
      throw new Error("TTS returned invalid scene boundaries");
    }
    if (i && Math.abs(scenes[i].start - scenes[i - 1].end) > 0.02) {
      throw new Error("TTS scene boundaries contain an unmodelled pause; preserve the pause explicitly before rendering");
    }
  }
  const alignedPlan = { ...plan, scenes };
  const graph = compileSceneGraph(alignedPlan);
  const graphCheck = validateSceneGraph(graph);
  if (!graphCheck.ok) throw new Error("Scene graph validation failed: " + graphCheck.errors.join("; "));
  graph.duration = audioDuration;
  const timeline = compileTimeline(graph, ttsResult.word_events, audioDuration);
  const timelineCheck = validateTimeline(timeline);
  if (!timelineCheck.ok) throw new Error("Audio-visual timeline validation failed: " + timelineCheck.errors.join("; "));
  return {
    schema: "bamo.omnivision-pipeline/1.0",
    audio: { path: ttsResult.path, provider: ttsResult.provider, duration: audioDuration },
    graph,
    timeline,
    validation: { ok: true, sceneCount: graph.scenes.length, wordCount: timeline.validation.wordCount, captionCount: timeline.validation.captionCount }
  };
}
