"use client";

import { useEffect, useRef, useState } from "react";
import TicketButton from "@/components/TicketButton";
import { play } from "@/lib/sound";

// The home page's two moods. "welcome": the title, tagline and Start planning on the night sky.
// "planning": the title glides up and shrinks, the night turns slightly glassy, and the trip form
// rises in on a frosted panel. Back (or Esc) returns to welcome.

const GLIDE = "transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none";

export default function HomeFlow() {
  const [planning, setPlanning] = useState(false);
  const panelHeading = useRef<HTMLHeadingElement>(null);

  const start = () => {
    setPlanning(true);
    play("chime");
  };

  useEffect(() => {
    if (!planning) return;
    panelHeading.current?.focus({ preventScroll: true }); // keyboard and screen-reader users land on the form
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setPlanning(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [planning]);

  return (
    <main className="relative flex flex-1 flex-col items-center justify-center px-4 pb-[20vh] text-center">
      {/* The glass: fades in over the night while the form is open. */}
      <div aria-hidden className={`pointer-events-none fixed inset-0 bg-night/30 backdrop-blur-md ${GLIDE}
                                   ${planning ? "opacity-100" : "opacity-0"}`} />

      <div className={`relative flex flex-col items-center gap-6 ${GLIDE}
                       ${planning ? "-translate-y-[24vh] scale-[0.6]" : ""}`}>
        <p className="text-sm uppercase tracking-[0.3em] text-gold">Germany · Belgium · France</p>
        <h1 className="font-display text-5xl font-semibold sm:text-7xl [font-variation-settings:'SOFT'_100]">
          Merry<span className="text-gold">Mapped</span>
        </h1>
        <div className={`flex flex-col items-center gap-6 ${GLIDE} ${planning ? "invisible opacity-0" : "opacity-100"}`}>
          <p className="max-w-md text-lg text-snow/90">
            Your Christmas markets trip, planned reliably around accurate opening hours and train schedules.
          </p>
          <TicketButton className="mt-4" onClick={start}>Start planning</TicketButton>
        </div>
      </div>

      {/* The trip form's panel: rises in from below. */}
      <section aria-label="Plan your trip" inert={!planning}
               className={`absolute inset-x-4 top-[18%] mx-auto max-w-2xl border border-snow/15 bg-night/55 p-8
                           shadow-2xl shadow-black/40 backdrop-blur-xl sm:p-10 ${GLIDE}
                           ${planning ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-16 opacity-0"}`}>
        <h2 ref={panelHeading} tabIndex={-1} className="font-display text-3xl font-semibold outline-none">
          Plan your trip
        </h2>
        <p className="mt-4 text-snow/80">Your trip form comes here.</p>
        <TicketButton kind="quiet" className="mt-8" onClick={() => setPlanning(false)}>Back</TicketButton>
      </section>
    </main>
  );
}
