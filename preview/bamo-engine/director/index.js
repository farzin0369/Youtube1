/**
 * BAMO Smart Director — public API
 */
const { buildTimeline } = (typeof window !== 'undefined' && window.BAMO_TIMELINE)
  ? window.BAMO_TIMELINE
  : require('./timeline');

function createProject(text, options = {}) {
  if (!text || !String(text).trim()) {
    throw new Error('متن خالی است. لطفاً یک متن یا سناریو وارد کنید.');
  }
  const timeline = buildTimeline(String(text), {
    maxScenes: options.maxScenes || 4,
    targetTotal: options.targetTotal || (options.format === 'long' ? 45 : 14),
    minDuration: options.minDuration || 2.8,
    maxDuration: options.maxDuration || 5.5,
    format: options.format || 'short',
    fps: options.fps || 24,
    width: options.width || 720,
    height: options.height || 1280
  });
  return {
    format: timeline.format,
    fps: timeline.fps,
    width: timeline.width,
    height: timeline.height,
    globalMood: timeline.globalMood,
    totalDuration: timeline.totalDuration,
    scenes: timeline.scenes.map(sc => ({
      duration: sc.duration,
      text: sc.text,
      narration: sc.narration,
      visual_prompt: sc.keywords.join(' ') + ' ' + sc.motif,
      motif: sc.motif,
      mood: sc.mood,
      palette: sc.palette,
      camera: sc.camera,
      particles: sc.particles,
      light: sc.light,
      transition: sc.transition,
      textAnim: sc.textAnim
    })),
    meta: timeline.meta
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { createProject, buildTimeline };
} else {
  window.BAMO_DIRECTOR = { createProject, buildTimeline };
}
