/**
 * Voice Navigation & Intent Recognition Service
 * PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
 * Dev 2 Voice-Only Accessibility Engine
 */

export const VOICE_INTENTS = {
  CONFIRM: 'CONFIRM',
  DENY: 'DENY',
  NEXT: 'NEXT',
  BACK: 'BACK',
  STOP: 'STOP',
  REPEAT: 'REPEAT',
  HELP: 'HELP',
  UNKNOWN: 'UNKNOWN',
};

// Multilingual intent lexicons for Hindi, Hinglish, and English
const INTENT_RULES = [
  {
    intent: VOICE_INTENTS.CONFIRM,
    patterns: [
      'haan', 'han', 'ha', 'yes', 'sahi', 'theek', 'thik', 'thik hai',
      'theek hai', 'ok', 'okay', 'sure', 'confirm', 'agreed', 'manzoor',
      'हाँ', 'सही', 'ठीक है', 'स्वीकार', 'हो'
    ],
  },
  {
    intent: VOICE_INTENTS.DENY,
    patterns: [
      'nahi', 'nahin', 'na', 'no', 'nope', 'mat karo', 'cancel',
      'गलत', 'नहीं', 'ना', 'रद्द'
    ],
  },
  {
    intent: VOICE_INTENTS.NEXT,
    patterns: [
      'aage', 'aage badho', 'next', 'forward', 'proceed', 'chalo',
      'आगे', 'आगे बढ़ो', 'अगला'
    ],
  },
  {
    intent: VOICE_INTENTS.BACK,
    patterns: [
      'peeche', 'piche', 'back', 'previous', 'wapas', 'piche jao',
      'पीछे', 'वापस', 'पिछला'
    ],
  },
  {
    intent: VOICE_INTENTS.STOP,
    patterns: [
      'ruko', 'ruk jao', 'stop', 'pause', 'hold', 'wait', 'thahro',
      'रुको', 'ठहरो', 'रोकें'
    ],
  },
  {
    intent: VOICE_INTENTS.REPEAT,
    patterns: [
      'dobara', 'fir se', 'repeat', 'again', 'kya bola', 'samajh nahi aaya',
      'दोबारा', 'फिर से बोलो'
    ],
  },
];

/**
 * Classifies a transcribed voice statement into a navigation intent.
 * @param {string} text - The transcribed speech text.
 * @returns {string} - One of VOICE_INTENTS.
 */
export function classifyVoiceIntent(text) {
  if (!text || typeof text !== 'string') return VOICE_INTENTS.UNKNOWN;
  const clean = text.trim().toLowerCase();

  for (const rule of INTENT_RULES) {
    for (const pat of rule.patterns) {
      if (clean === pat || clean.startsWith(pat + ' ') || clean.endsWith(' ' + pat) || clean.includes(pat)) {
        return rule.intent;
      }
    }
  }

  return VOICE_INTENTS.UNKNOWN;
}

/**
 * Speaks a screen prompt aloud using Web Speech API SpeechSynthesis.
 * Falls back gracefully if SpeechSynthesis is unavailable.
 * @param {string} text - Message to read aloud.
 * @param {string} lang - 'hi-IN' or 'en-IN'.
 * @returns {Promise<void>}
 */
export function speakPrompt(text, lang = 'hi-IN') {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      resolve();
      return;
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === 'en' ? 'en-IN' : 'hi-IN';
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();

    window.speechSynthesis.speak(utterance);
  });
}

/**
 * Registers a spacebar keyboard listener as a physical fallback for CONFIRM.
 * @param {Function} onConfirm - Callback triggered when spacebar is pressed.
 * @returns {Function} - Cleanup function to unbind listener.
 */
export function registerSpacebarFallback(onConfirm) {
  if (typeof window === 'undefined') return () => {};

  const handleKeyDown = (e) => {
    // Only trigger if user is not actively typing in an input/textarea
    const tag = e.target?.tagName?.toLowerCase();
    if (tag === 'input' || tag === 'textarea') return;

    if (e.code === 'Space' || e.key === ' ') {
      e.preventDefault();
      if (typeof onConfirm === 'function') {
        onConfirm();
      }
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}
