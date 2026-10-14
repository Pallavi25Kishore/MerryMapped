"use client";

import { useSyncExternalStore } from "react";
import { play, setSoundOn, soundOn, subscribe } from "@/lib/sound";

// The bell in the header: turns MerryMapped's sounds on or off. Off: a snow-white bell with a line
// through it. On: a glowing gold bell, and a chime to show it works.
export default function SoundButton() {
  const on = useSyncExternalStore(subscribe, soundOn, () => false);

  const toggle = () => {
    setSoundOn(!on);
    if (!on) play("chime", true);
  };

  return (
    <button type="button" onClick={toggle} aria-pressed={on} aria-label="Sound"
            title={on ? "Sound is on" : "Sound is off"}
            className={`rounded-sm p-1 transition duration-300 hover:text-gold
                        hover:drop-shadow-[0_0_8px_rgb(244_195_90/0.7)] focus-visible:outline-2
                        focus-visible:outline-offset-2 focus-visible:outline-snow
                        ${on ? "text-gold drop-shadow-[0_0_6px_rgb(244_195_90/0.6)]" : "text-snow/85"}`}>
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6"
           strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z" />
        <path d="M10 20.5a2 2 0 0 0 4 0" />
        {!on && <path d="M4 4l16 16" />}
      </svg>
    </button>
  );
}
