"use client";

import { useEffect, useRef, useState } from "react";

// While the trip is planned (about half a minute): a wide winter scene across the screen. Little
// trees, gift boxes and a market stall in white and gold stand along a dotted track, under a star and
// faint snowflakes, and the one splash of red and green is the train gliding past (a red locomotive
// pulling green wagons, with a red gift and a green tree). A line
// below says what MerryMapped is doing; it describes the steps in general (the website can't see
// the backend's progress).

const LINES = [
  "Checking which markets are open on your days…",
  "Finding the best trains between them…",
  "Making sure every connection works…",
  "Matching markets to your wishes…",
  "Wrapping it all up with a bow…",
];
const LINE_SECONDS = 4;
const WIDTH = 1400;
const TRACK = "M -20 150 C 200 100, 350 175, 560 140 S 900 95, 1080 135 S 1300 165, 1420 125";
const LAP = 10; // seconds for the train to cross the screen
const CARS = ["engine", "gift", "tree"] as const;
const GAP = 0.25; // seconds between one car and the next (close coupled)

// Things standing along the track, by how far along it they are (0 to 1).
const SCENERY: { at: number; kind: "tree" | "gift" | "stall"; size: number }[] = [
  { at: 0.08, kind: "tree", size: 1 }, { at: 0.11, kind: "tree", size: 0.7 }, { at: 0.24, kind: "gift", size: 1 },
  { at: 0.38, kind: "tree", size: 1.2 }, { at: 0.52, kind: "stall", size: 1 }, { at: 0.66, kind: "tree", size: 0.8 },
  { at: 0.7, kind: "gift", size: 0.8 }, { at: 0.83, kind: "tree", size: 1.1 }, { at: 0.86, kind: "tree", size: 0.75 },
];

function Tree({ size }: { size: number }) {
  return (
    <g transform={`scale(${size})`} className="stroke-gold" fill="none" strokeWidth={1.6} strokeLinejoin="round">
      <path d="M 0 -46 L 13 -24 L 7 -24 L 18 -6 L -18 -6 L -7 -24 L -13 -24 Z" className="fill-snow" />
      <path d="M 0 -6 V 0" />
      <path d="M 0 -54 l 2 4 4 0.5 -3 3 1 4 -4 -2 -4 2 1 -4 -3 -3 4 -0.5 z" className="fill-gold stroke-none" />
    </g>
  );
}

function Gift({ size }: { size: number }) {
  return (
    <g transform={`scale(${size})`} strokeWidth={1.6} className="stroke-gold">
      <rect x="-11" y="-18" width="22" height="18" className="fill-snow" />
      <path d="M 0 -18 V 0 M -11 -10 H 11" fill="none" />
      <path d="M 0 -18 c -6 -8 -12 -2 0 0 c 6 -8 12 -2 0 0" fill="none" />
    </g>
  );
}

function Stall() {
  return (
    <g strokeWidth={1.6} className="stroke-gold">
      <path d="M -26 -30 L 0 -48 L 26 -30 Z" className="fill-snow" />
      <path d="M -13 -39 L 0 -30 M 13 -39 L 0 -30" fill="none" />
      <rect x="-22" y="-30" width="44" height="30" className="fill-snow/90" />
      <path d="M -22 -14 H 22" fill="none" />
      {[-15, -5, 5, 15].map((x) => <circle key={x} cx={x} cy={-26} r={1.8} className="fill-gold stroke-none" />)}
    </g>
  );
}

function Car({ kind }: { kind: (typeof CARS)[number] }) {
  if (kind === "engine") {
    return (
      <g transform="translate(-16 -20)" className="fill-cranberry stroke-gold" strokeWidth={1.2}>
        <rect x="0" y="8" width="26" height="12" rx="2" />
        <rect x="18" y="0" width="11" height="13" rx="1.5" />
        <rect x="4" y="2" width="5" height="7" />
        <circle cx="7" cy="22" r="3.5" className="fill-night stroke-gold" strokeWidth="1.6" />
        <circle cx="20" cy="22" r="3.5" className="fill-night stroke-gold" strokeWidth="1.6" />
      </g>
    );
  }
  return (
    <g transform="translate(-12 -16)">
      <rect x="0" y="6" width="24" height="10" rx="1.5" className="fill-[#2f7d4f] stroke-gold" strokeWidth="1.2" />
      {kind === "gift"
        ? <><rect x="6" y="-4" width="12" height="10" className="fill-cranberry stroke-gold" strokeWidth="1.2" />
            <path d="M 12 -4 V 6" className="stroke-gold" strokeWidth="1.2" /></>
        : <path d="M 12 -10 L 19 6 L 5 6 Z" className="fill-[#2f7d4f] stroke-gold" strokeWidth="1.2" />}
      <circle cx="6" cy="18" r="3" className="fill-night stroke-gold" strokeWidth="1.5" />
      <circle cx="18" cy="18" r="3" className="fill-night stroke-gold" strokeWidth="1.5" />
    </g>
  );
}

export default function PlanningWait() {
  const [line, setLine] = useState(0);
  const track = useRef<SVGPathElement>(null);
  const [spots, setSpots] = useState<{ x: number; y: number }[]>([]);

  useEffect(() => {
    const timer = setInterval(() => setLine((n) => Math.min(n + 1, LINES.length - 1)), LINE_SECONDS * 1000);
    return () => clearInterval(timer);
  }, []);

  // Stand the scenery on the track: find each thing's point along the curve once it is drawn.
  useEffect(() => {
    const path = track.current;
    if (!path) return;
    const length = path.getTotalLength();
    setSpots(SCENERY.map(({ at }) => {
      const point = path.getPointAtLength(at * length);
      return { x: point.x, y: point.y };
    }));
  }, []);

  return (
    <div className="rise-in py-4 text-center" role="status" aria-live="polite" aria-label="Planning your trip">
      <svg viewBox={`0 0 ${WIDTH} 230`} className="w-full" aria-hidden>
        {/* A star and faint snowflakes in the sky. */}
        <path d="M 700 18 l 3 9 9 1 -7 6 2 9 -7 -5 -7 5 2 -9 -7 -6 9 -1 z" className="fill-gold/80" />
        {[[160, 40], [420, 28], [620, 60], [880, 34], [1110, 52], [1290, 30], [300, 70], [1000, 74]].map(([x, y]) => (
          <text key={`${x}-${y}`} x={x} y={y} className="fill-snow/30 text-[16px]">❄</text>
        ))}

        <path ref={track} d={TRACK} fill="none" className="stroke-gold/35" strokeWidth={2} strokeDasharray="2 9"
              strokeLinecap="round" />
        {spots.map((spot, i) => (
          <g key={i} transform={`translate(${spot.x} ${spot.y - 4})`}>
            {SCENERY[i].kind === "tree" ? <Tree size={SCENERY[i].size} />
              : SCENERY[i].kind === "gift" ? <Gift size={SCENERY[i].size} /> : <Stall />}
          </g>
        ))}

        {CARS.map((kind, i) => (
          <g key={kind} className="motion-reduce:hidden">
            <Car kind={kind} />
            <animateMotion dur={`${LAP}s`} repeatCount="indefinite" path={TRACK} rotate="auto"
                           begin={`-${LAP - i * GAP}s`} />
          </g>
        ))}
      </svg>
      <p key={line} className="rise-in mt-4 min-h-6 text-snow/85">{LINES[line]}</p>
      <p className="mt-2 text-sm text-frost">This usually takes about half a minute.</p>
    </div>
  );
}
