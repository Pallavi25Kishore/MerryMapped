"use client";

import { useEffect, useRef, useState } from "react";
import { HOME_EVENT } from "@/components/Header";
import PlanForm from "@/components/PlanForm";
import TicketButton from "@/components/TicketButton";
import { castMagic } from "@/lib/magic";
import { play } from "@/lib/sound";

// The home page's two moods. "welcome": the title, tagline and Start planning on the night sky.
// "planning": the title glides up and shrinks, the night turns slightly glassy, and the trip form
// rises in on a frosted panel. Start planning tips forward until it vanishes edge-on, with sparkles
// lifting off its edges and a magical sound, all starting at the click and flowing together. Back
// (or Esc) returns to welcome.

// Every move eases in and out gently, so the welcome dissolves into the planner.
const GLIDE = "transition-all duration-[1400ms] ease-[cubic-bezier(0.45,0,0.25,1)] motion-reduce:transition-none";
const TIP_MS = 900; // how long Start planning takes to tip forward and vanish

export default function HomeFlow() {
  const [planning, setPlanning] = useState(false);
  const [tipped, setTipped] = useState(false); // Start planning has tipped forward, edge-on
  const [opened, setOpened] = useState(false); // the form stays (with what was entered) once opened
  const panelHeading = useRef<HTMLHeadingElement>(null);

  const start = (event: React.MouseEvent<HTMLButtonElement>) => {
    const button = event.currentTarget;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setPlanning(true);
      setOpened(true);
      return;
    }
    // Everything starts at the click: the tip, the sparkles, the bells and the planner opening.
    castMagic(button); // sparkles lift off its edges
    play("magic");
    setTipped(true); // a quarter turn, top over bottom, until it is edge-on and gone
    setPlanning(true);
    setOpened(true);
  };

  const back = () => {
    setPlanning(false);
    setTipped(false); // Start planning tips back up into view
  };

  // Home in the header returns to the welcome view, like Back.
  useEffect(() => {
    const home = () => {
      setPlanning(false);
      setTipped(false);
    };
    window.addEventListener(HOME_EVENT, home);
    return () => window.removeEventListener(HOME_EVENT, home);
  }, []);

  useEffect(() => {
    if (!planning) return;
    panelHeading.current?.focus({ preventScroll: true }); // keyboard and screen-reader users land on the form
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && back();
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
          <TicketButton className="mt-4" onClick={start}
                        style={{ transform: `perspective(700px) rotateX(${tipped ? 90 : 0}deg)`,
                                 transition: `transform ${TIP_MS}ms cubic-bezier(0.45, 0, 0.25, 1), box-shadow 300ms, border-color 300ms, background-color 300ms` }}>
            Start planning
          </TicketButton>
        </div>
      </div>

      {/* The trip form's panel: rises in from below. */}
      <section aria-label="Plan your trip" inert={!planning}
               className={`absolute inset-x-4 top-[18%] mx-auto max-h-[calc(82%-1rem)] max-w-2xl overflow-y-auto xl:max-w-[1312px] border border-snow/15 bg-night/55 p-8
                           shadow-2xl shadow-black/40 backdrop-blur-xl sm:p-10 ${GLIDE}
                           ${planning ? "translate-y-0 opacity-100 delay-150" : "pointer-events-none translate-y-16 opacity-0"}`}>
        <h2 ref={panelHeading} tabIndex={-1} className="font-display text-3xl font-semibold outline-none">
          Plan your trip
        </h2>
        {opened && <PlanForm onBack={back} />}
      </section>
    </main>
  );
}
