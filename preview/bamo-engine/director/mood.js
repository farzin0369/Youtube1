/**
 * BAMO Director — Mood & Style Mapping
 */
const MOODS = {
  calm: {
    id: 'calm',
    palette: { bg: '#0c0a09', primary: '#f5d0a9', secondary: '#a78bfa', accent: '#67e8f9', particle: 'rgba(245,208,169,0.5)', glow: 'rgba(245,208,169,0.2)' },
    camera: { type: 'slow-dolly', intensity: 0.3 },
    particles: { density: 0.4, type: 'dust' },
    light: { rays: 0.3, bloom: 0.5 },
    transition: 'fade',
    audio: { pad: 'warm', tempo: 0.6 }
  },
  epic: {
    id: 'epic',
    palette: { bg: '#0a0a12', primary: '#fbbf24', secondary: '#f472b6', accent: '#38bdf8', particle: 'rgba(251,191,36,0.6)', glow: 'rgba(251,191,36,0.28)' },
    camera: { type: 'orbit', intensity: 0.7 },
    particles: { density: 0.8, type: 'golden' },
    light: { rays: 0.9, bloom: 0.85 },
    transition: 'light-leak',
    audio: { pad: 'cinematic', tempo: 0.9 }
  },
  mysterious: {
    id: 'mysterious',
    palette: { bg: '#0b0c15', primary: '#818cf8', secondary: '#c084fc', accent: '#22d3ee', particle: 'rgba(129,140,248,0.45)', glow: 'rgba(129,140,248,0.22)' },
    camera: { type: 'parallax', intensity: 0.5 },
    particles: { density: 0.55, type: 'stars' },
    light: { rays: 0.4, bloom: 0.6 },
    transition: 'particle-dissolve',
    audio: { pad: 'dark', tempo: 0.55 }
  },
  energetic: {
    id: 'energetic',
    palette: { bg: '#0f172a', primary: '#22d3ee', secondary: '#f472b6', accent: '#a3e635', particle: 'rgba(34,211,238,0.55)', glow: 'rgba(34,211,238,0.25)' },
    camera: { type: 'shake-zoom', intensity: 0.85 },
    particles: { density: 0.9, type: 'sparks' },
    light: { rays: 0.7, bloom: 0.75 },
    transition: 'whip',
    audio: { pad: 'pulse', tempo: 1.2 }
  },
  sad: {
    id: 'sad',
    palette: { bg: '#0c1220', primary: '#94a3b8', secondary: '#64748b', accent: '#7dd3fc', particle: 'rgba(148,163,184,0.35)', glow: 'rgba(125,211,252,0.15)' },
    camera: { type: 'slow-zoom', intensity: 0.25 },
    particles: { density: 0.3, type: 'rain' },
    light: { rays: 0.15, bloom: 0.35 },
    transition: 'fade',
    audio: { pad: 'melancholy', tempo: 0.45 }
  },
  futuristic: {
    id: 'futuristic',
    palette: { bg: '#020617', primary: '#22d3ee', secondary: '#a78bfa', accent: '#e879f9', particle: 'rgba(34,211,238,0.5)', glow: 'rgba(167,139,250,0.25)' },
    camera: { type: 'dolly', intensity: 0.6 },
    particles: { density: 0.7, type: 'grid' },
    light: { rays: 0.6, bloom: 0.8 },
    transition: 'morph',
    audio: { pad: 'synth', tempo: 1.0 }
  },
  hopeful: {
    id: 'hopeful',
    palette: { bg: '#052e16', primary: '#4ade80', secondary: '#2dd4bf', accent: '#facc15', particle: 'rgba(74,222,128,0.5)', glow: 'rgba(74,222,128,0.22)' },
    camera: { type: 'slow-dolly', intensity: 0.4 },
    particles: { density: 0.6, type: 'golden' },
    light: { rays: 0.65, bloom: 0.7 },
    transition: 'fade',
    audio: { pad: 'warm', tempo: 0.75 }
  },
  spiritual: {
    id: 'spiritual',
    palette: { bg: '#0c0a09', primary: '#fbbf24', secondary: '#f472b6', accent: '#38bdf8', particle: 'rgba(251,191,36,0.5)', glow: 'rgba(251,191,36,0.22)' },
    camera: { type: 'orbit', intensity: 0.35 },
    particles: { density: 0.5, type: 'dust' },
    light: { rays: 0.55, bloom: 0.65 },
    transition: 'light-leak',
    audio: { pad: 'warm', tempo: 0.65 }
  }
};

const KEYWORD_MOOD = [
  { re: /صبر|آرامش|سکوت|آرام|صلح|peaceful|calm|gentle|soft/i, mood: 'calm' },
  { re: /حماسی|قهرمان|پیروزی|قدرت|عظیم|epic|hero|victory|power|glory/i, mood: 'epic' },
  { re: /رمز|مرموز|تاریک|پنهان|راز|mystery|dark|secret|shadow/i, mood: 'mysterious' },
  { re: /انرژی|سریع|هیجان|پرش|حرکت|energy|fast|excited|dynamic/i, mood: 'energetic' },
  { re: /غم|اندوه|فقدان|تنهایی|اشک|sad|grief|lonely|tear/i, mood: 'sad' },
  { re: /آینده|فناوری|فضا|سایبر|neon|future|cyber|space|tech/i, mood: 'futuristic' },
  { re: /امید|رشد|پیشرفت|نور|طلوع|hope|growth|light|dawn|rise/i, mood: 'hopeful' },
  { re: /توکل|دعا|قلب|معنویت|ایمان|روح|spiritual|faith|soul|prayer/i, mood: 'spiritual' }
];

function detectMood(text) {
  if (!text || typeof text !== 'string') return MOODS.spiritual;
  for (const rule of KEYWORD_MOOD) {
    if (rule.re.test(text)) return MOODS[rule.mood];
  }
  return MOODS.spiritual;
}

function getMoodById(id) {
  return MOODS[id] || MOODS.spiritual;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MOODS, detectMood, getMoodById };
} else {
  window.BAMO_MOOD = { MOODS, detectMood, getMoodById };
}
