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
  audio ??= new AudioContext();
  if (audio.state === "suspended") void audio.resume();
  return audio;
}

// A soft bell: a few tones that ring together and fade, like a small hand bell.
function chime(ctx: AudioContext): void {
  const now = ctx.currentTime;
  const notes = [{ at: 0, pitch: 1046.5 }, { at: 0.12, pitch: 1568 }]; // C6, then G6
  for (const { at, pitch } of notes) {
    for (const [ratio, loudness, ring] of [[1, 0.18, 1.6], [2.76, 0.06, 0.8], [5.4, 0.025, 0.4]]) {
      const tone = ctx.createOscillator();
      const volume = ctx.createGain();
      tone.type = "sine";
      tone.frequency.value = pitch * ratio;
      volume.gain.setValueAtTime(0, now + at);
      volume.gain.linearRampToValueAtTime(loudness, now + at + 0.008); // a quick strike
      volume.gain.exponentialRampToValueAtTime(0.0001, now + at + ring); // then it rings away
      tone.connect(volume).connect(ctx.destination);
      tone.start(now + at);
      tone.stop(now + at + ring);
    }
  }
}

const SOUNDS = { chime };
export type SoundName = keyof typeof SOUNDS;

// Play a sound, if sound is on. Set force to play it even so (used right after turning sound on).
export function play(name: SoundName, force = false): void {
  if (!force && !soundOn()) return;
  try {
    SOUNDS[name](context());
  } catch {
    // no Web Audio in this browser: stay silent
  }
}
