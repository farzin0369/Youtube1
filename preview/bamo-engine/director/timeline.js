/**
 * BAMO Director — Timeline Builder
 */
function buildTimeline(text, options = {}) {
  const parser = (typeof window !== 'undefined' && window.BAMO_PARSER) ? window.BAMO_PARSER : require('./parser');
  const moodLib = (typeof window !== 'undefined' && window.BAMO_MOOD) ? window.BAMO_MOOD : require('./mood');

  const scenesDraft = parser.parseTextToScenes(text, options);
  const globalMood = moodLib.detectMood(text);

  const scenes = scenesDraft.map((draft, i) => {
    const localMood = moodLib.detectMood(draft.narration) || globalMood;
    const mood = localMood.id !== globalMood.id && i > 0 ? localMood : globalMood;
    return {
      index: i,
      duration: draft.duration,
      text: draft.text,
      narration: draft.narration,
      keywords: draft.keywords,
      motif: draft.motif,
      mood: mood.id,
      palette: mood.palette,
      camera: { ...mood.camera },
      particles: { ...mood.particles },
      light: { ...mood.light },
      transition: i === 0 ? 'fade' : mood.transition,
      textAnim: { type: 'fade-up', delay: 0.15, duration: 0.6 },
      audioCues: { pad: mood.audio.pad, impactAt: i === 0 ? 0.1 : 0.05, riser: i === scenesDraft.length - 1 }
    };
  });

  const totalDuration = scenes.reduce((s, sc) => s + sc.duration, 0);
  return {
    version: '1.0',
    format: options.format || 'short',
    fps: options.fps || 24,
    width: options.width || 720,
    height: options.height || 1280,
    totalDuration: Math.round(totalDuration * 10) / 10,
    globalMood: globalMood.id,
    scenes,
    meta: { sourceTextLength: (text || '').length, sceneCount: scenes.length, generatedAt: new Date().toISOString() }
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { buildTimeline };
} else {
  window.BAMO_TIMELINE = { buildTimeline };
}
