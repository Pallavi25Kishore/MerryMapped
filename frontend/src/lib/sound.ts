// MerryMapped's sounds, made in code with the browser's Web Audio (no sound files). Sound is off
// until the traveller turns it on; the choice is remembered in this browser.

const SOUND_KEY = "merrymapped-sound";
const listeners = new Set<() => void>();

export function soundOn(): boolean {
  try {
    return localStorage.getItem(SOUND_KEY) === "on";
  } catch {
    return false;
  }
}

export function setSoundOn(on: boolean): void {
  try {
    localStorage.setItem(SOUND_KEY, on ? "on" : "off");
  } catch {
    // storage blocked: the choice lasts until the page is closed
  }
  listeners.forEach((listener) => listener());
}

// For React's useSyncExternalStore: lets the sound button follow the setting.
export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

let audio: AudioContext | null = null;

// Browsers allow sound only after a click, so the audio is started on the first sound played.
function context(): AudioContext {
  if (!audio) {
    audio = new AudioContext();
    reverb(audio); // prepare the hall echo now, so the first magic sound starts without a pause
  }
  if (audio.state === "suspended") void audio.resume();
  return audio;
}

// A soft hall echo (reverb), made once from fading noise. Magic sounds go through it, so they ring
// out as if in a large, glowing room instead of sounding dry like a toy.
let hall: AudioNode | null = null;
function reverb(ctx: AudioContext): AudioNode {
  if (hall) return hall;
  const seconds = 2.8;
  const echo = ctx.createBuffer(2, ctx.sampleRate * seconds, ctx.sampleRate);
  for (let side = 0; side < 2; side++) {
    const samples = echo.getChannelData(side);
    for (let i = 0; i < samples.length; i++) samples[i] = (Math.random() * 2 - 1) * (1 - i / samples.length) ** 3;
  }
  const convolver = ctx.createConvolver();
  convolver.buffer = echo;
  const wet = ctx.createGain();
  wet.gain.value = 0.6;
  convolver.connect(wet).connect(ctx.destination);
  hall = convolver;
  return hall;
}

// Where a note goes: straight out, and (for magic) also into the hall echo; pan places it from left
// (-1) to right (1).
function output(ctx: AudioContext, echo: boolean, pan = 0): AudioNode {
  const place = ctx.createStereoPanner();
  place.pan.value = pan;
  place.connect(ctx.destination);
  if (echo) place.connect(reverb(ctx));
  return place;
}

// One small bell note: a few tones that strike together and ring away, like a hand bell or celesta.
function bell(ctx: AudioContext, at: number, pitch: number, loudness = 1, ring = 1, to?: AudioNode): void {
  const start = ctx.currentTime + at;
  const destination = to ?? ctx.destination;
  for (const [ratio, level, length] of [[1, 0.18, 1.6], [2.76, 0.06, 0.8], [5.4, 0.025, 0.4]]) {
    const tone = ctx.createOscillator();
    const volume = ctx.createGain();
    tone.type = "sine";
    tone.frequency.value = pitch * ratio;
    volume.gain.setValueAtTime(0, start);
    volume.gain.linearRampToValueAtTime(level * loudness, start + 0.008); // a quick strike
    volume.gain.exponentialRampToValueAtTime(0.0001, start + length * ring); // then it rings away
    tone.connect(volume).connect(destination);
    tone.start(start);
    tone.stop(start + length * ring);
  }
}

// A soft two-note chime: C6, then G6.
function chime(ctx: AudioContext): void {
  bell(ctx, 0, 1046.5);
  bell(ctx, 0.12, 1568);
}

// A warm, airy chord that swells up from nothing and melts away.
function swell(ctx: AudioContext, pitches: number[], length: number, loudness: number): void {
  const start = ctx.currentTime;
  const soften = ctx.createBiquadFilter();
  soften.type = "lowpass";
  soften.frequency.value = 2400;
  const volume = ctx.createGain();
  volume.gain.setValueAtTime(0, start);
  volume.gain.linearRampToValueAtTime(loudness, start + length * 0.3);
  volume.gain.exponentialRampToValueAtTime(0.0001, start + length);
  soften.connect(volume).connect(output(ctx, true));
  for (const pitch of pitches) {
    for (const detune of [-6, 6]) { // two slightly apart tones per note: a gentle shimmer
      const tone = ctx.createOscillator();
      tone.type = "triangle";
      tone.frequency.value = pitch;
      tone.detune.value = detune;
      tone.connect(soften);
      tone.start(start);
      tone.stop(start + length);
    }
  }
}

// Magic: a soft swell, a scatter of fairy-dust twinkles drifting upward and around you (left to
// right), and a gentle final sparkle, all ringing out in the hall echo. Notes come from a pentatonic
// scale, so they always sound sweet together.
function magic(ctx: AudioContext): void {
  swell(ctx, [523.3, 659.3, 784], 2.4, 0.05); // C5, E5, G5
  const dust = [2093, 2349.3, 2637, 3136, 3520, 4186, 4698.6, 5274];
  for (let i = 0; i < 16; i++) {
    const rising = Math.min(dust.length - 1, Math.floor((i / 16) * dust.length + Math.random() * 2));
    const at = 0.05 + i * 0.055 + Math.random() * 0.03;
    bell(ctx, at, dust[rising], 0.12 + Math.random() * 0.08, 0.35, output(ctx, true, Math.random() * 1.6 - 0.8));
  }
  [3136, 4186, 5274].forEach((pitch, i) => bell(ctx, 1.0 + i * 0.09, pitch, 0.18, 0.9, output(ctx, true, (i - 1) * 0.4)));
}

// Something revealed (a market's story in the description box): a soft little sparkle of three high
// bells, in the hall echo.
function reveal(ctx: AudioContext): void {
  [2637, 3136, 3951].forEach((pitch, i) => bell(ctx, i * 0.07, pitch, 0.18, 0.5, output(ctx, true, (i - 1) * 0.3)));
}

const SOUNDS = { chime, magic, reveal };
export type SoundName = keyof typeof SOUNDS;

// Play a sound. Every sound goes through here, and plays only when the bell is on.
export function play(name: SoundName): void {
  if (!soundOn()) return;
  try {
    SOUNDS[name](context());
  } catch {
    // no Web Audio in this browser: stay silent
  }
}
