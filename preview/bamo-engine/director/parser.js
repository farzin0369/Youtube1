/**
 * BAMO Director — Text Parser (Persian + English)
 */
function normalizeText(text) {
  return String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
}

function splitBlocks(text) {
  const t = normalizeText(text);
  if (!t) return [];
  if (/^\s*صحنه\s*\d+/im.test(t) || /^\s*Scene\s*\d+/im.test(t)) {
    return t.split(/(?=^\s*(?:صحنه|Scene)\s*\d+)/im).map(s => s.trim()).filter(Boolean);
  }
  let blocks = t.split(/\n\s*\n+/).map(s => s.trim()).filter(Boolean);
  if (blocks.length >= 2) return blocks;
  const parts = t.split(/(?<=[.!?؟۔…])\s+|\n+/).map(s => s.trim()).filter(s => s.length > 3);
  if (parts.length >= 2) return parts;
  return [t];
}

function extractKeywords(text, max = 8) {
  const words = text.replace(/[^\p{L}\p{N}\s]/gu, ' ').split(/\s+/).filter(w => w.length > 2);
  const freq = {};
  words.forEach(w => { freq[w] = (freq[w] || 0) + 1; });
  return Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, max).map(([w]) => w);
}

function guessMotif(text) {
  const t = text.toLowerCase();
  if (/بیضی|کانون|ellipse|focus|foci/.test(t)) return 'ellipse';
  if (/موج|تداخل|wave|interference|phase/.test(t)) return 'wave';
  if (/مسیر|قدم|راه|path|step|journey|road/.test(t)) return 'path';
  if (/نور|طلوع|light|sun|dawn|glow|hope/.test(t)) return 'light';
  if (/انتخاب|دو راه|choice|decision|fork/.test(t)) return 'choice';
  if (/ستاره|فضا|کیهان|star|cosmic|space|galaxy/.test(t)) return 'cosmic';
  if (/قلب|عشق|heart|love/.test(t)) return 'heart';
  if (/رشد|درخت|growth|tree|plant/.test(t)) return 'growth';
  return 'abstract';
}

function parseTextToScenes(text, options = {}) {
  const maxScenes = options.maxScenes || 6;
  const minDuration = options.minDuration || 2.5;
  const maxDuration = options.maxDuration || 6.0;
  const targetTotal = options.targetTotal || 15;
  const blocks = splitBlocks(text);
  if (!blocks.length) {
    return [{ text: '…', narration: text || '', keywords: [], motif: 'abstract', duration: 4 }];
  }
  let scenes = blocks.slice(0, maxScenes);
  if (blocks.length > maxScenes) {
    const mid = blocks.slice(1, -1).join(' ');
    scenes = [blocks[0], mid, blocks[blocks.length - 1]].filter(Boolean).slice(0, maxScenes);
  }
  const weights = scenes.map(s => Math.max(20, s.length));
  const totalW = weights.reduce((a, b) => a + b, 0) || 1;
  let durations = weights.map(w => {
    const d = (w / totalW) * targetTotal;
    return Math.max(minDuration, Math.min(maxDuration, d));
  });
  const sumD = durations.reduce((a, b) => a + b, 0);
  if (sumD > 0) {
    const scale = targetTotal / sumD;
    durations = durations.map(d => Math.max(minDuration, Math.min(maxDuration, d * scale)));
  }
  return scenes.map((block, i) => {
    const lines = block.split('\n').map(l => l.trim()).filter(Boolean);
    const onScreen = lines[0].length > 60 ? lines[0].slice(0, 48) + '…' : lines[0];
    return {
      index: i,
      text: onScreen || block.slice(0, 50),
      narration: block,
      keywords: extractKeywords(block),
      motif: guessMotif(block),
      duration: Math.round(durations[i] * 10) / 10
    };
  });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { parseTextToScenes, splitBlocks, extractKeywords, guessMotif };
} else {
  window.BAMO_PARSER = { parseTextToScenes, splitBlocks, extractKeywords, guessMotif };
}
