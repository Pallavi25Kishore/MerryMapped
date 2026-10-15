"use client";

import { useSyncExternalStore } from "react";
import { play, setSoundOn, soundOn, subscribe } from "@/lib/sound";

// The speaker in the header: turns MerryMapped's sounds on or off. Off: a snow-white speaker with a
// cross. On: a glowing gold speaker with sound waves, and a chime to show it works.
export default function SoundButton() {
  const on = useSyncExternalStore(subscribe, soundOn, () => false);

  const toggle = () => {
    setSoundOn(!on);
    play("chime"); // heard only when sound has just been turned on
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
        <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" />
        {on ? (
          <>
            <path d="M15.5 9.5a3.5 3.5 0 0 1 0 5" />
            <path d="M18 7a7 7 0 0 1 0 10" />
          </>
        ) : (
          <path d="M16 10l4.5 4.5M20.5 10L16 14.5" />
        )}
      </svg>
    </button>
  );
}
