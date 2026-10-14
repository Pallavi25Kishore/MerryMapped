"use client";

import type { ItineraryDay, Place } from "@/lib/api";
import { COUNTRIES, project } from "@/lib/mapShapes";

// The holiday map: zoomed to the trip, the countries, each night's city once in order (a little
// white-and-gold tree where markets are visited, a small house otherwise) with its name and number,
// the route as a dotted gold railway that draws itself in, and the red and green train travelling it.
// The chosen day's city glows and the line arriving there turns solid gold.

const OURS = new Set(["Germany", "France", "Belgium"]);
const ASPECT = 4 / 3;
const MARGIN = 70; // map units around the route

type Stop = { city: string; x: number; y: number; markets: boolean; days: number[] };

// The cities slept in, in order, each once in a row (staying on adds days to the same stop).
function stops(days: ItineraryDay[], places: Place[]): Stop[] {
  const where = new Map(places.map((p) => [p.city, project(p.lat, p.lon)]));
  const list: Stop[] = [];
  const add = (city: string, day: number, markets: boolean) => {
    const last = list[list.length - 1];
    if (last?.city === city) {
      last.days.push(day);
      last.markets ||= markets;
      return;
    }
    const point = where.get(city);
    if (point) list.push({ city, ...point, markets, days: [day] });
  };
  if (days[0]?.travel) add(days[0].travel.from, -1, false);
  days.forEach((day, n) => add(day.travel?.to ?? day.sleep_in, n, day.visits.length > 0));
  return list;
}

// Where a stop's name goes: below it, unless another stop is close, then on the side away from it.
function labelPlace(stop: Stop, all: Stop[]): { x: number; y: number; anchor: "start" | "middle" | "end" } {
  const others = all.filter((s) => s.city !== stop.city);
  const near = others.reduce<Stop | null>((best, s) =>
    !best || Math.hypot(s.x - stop.x, s.y - stop.y) < Math.hypot(best.x - stop.x, best.y - stop.y) ? s : best, null);
  if (!near || Math.hypot(near.x - stop.x, near.y - stop.y) > 110) return { x: 0, y: 22, anchor: "middle" };
  const dx = near.x - stop.x, dy = near.y - stop.y;
  if (Math.abs(dx) >= Math.abs(dy)) return dx > 0 ? { x: -16, y: -6, anchor: "end" } : { x: 16, y: -6, anchor: "start" };
  return dy > 0 ? { x: 0, y: -42, anchor: "middle" } : { x: 0, y: 22, anchor: "middle" };
}

// Frame the route with a margin, in the map's 4:3 shape.
function frame(points: Stop[]): string {
  const xs = points.map((p) => p.x), ys = points.map((p) => p.y);
  let x0 = Math.min(...xs) - MARGIN, x1 = Math.max(...xs) + MARGIN;
  let y0 = Math.min(...ys) - MARGIN, y1 = Math.max(...ys) + MARGIN;
  const w = x1 - x0, h = y1 - y0;
  if (w / h < ASPECT) { const grow = (h * ASPECT - w) / 2; x0 -= grow; x1 += grow; }
  else { const grow = (w / ASPECT - h) / 2; y0 -= grow; y1 += grow; }
  return `${x0} ${y0} ${x1 - x0} ${y1 - y0}`;
}

function Tree({ glow }: { glow: boolean }) {
  return (
    <g className="stroke-gold" strokeWidth={2} strokeLinejoin="round">
      <path d="M 0 -30 L 9 -15 L 5 -15 L 12 -3 L -12 -3 L -5 -15 L -9 -15 Z" className="fill-snow" />
      <path d="M 0 -3 V 2" />
      <path d="M 0 -37 l 1.6 3.2 3.4 0.4 -2.5 2.4 0.7 3.4 -3.2 -1.7 -3.2 1.7 0.7 -3.4 -2.5 -2.4 3.4 -0.4 z"
            className={glow ? "fill-gold" : "fill-gold/80"} stroke="none" />
    </g>
  );
}

function House() {
  return (
    <g className="stroke-gold" strokeWidth={2} strokeLinejoin="round">
      <path d="M -10 -12 L 0 -22 L 10 -12 Z" className="fill-snow" />
      <rect x="-8" y="-12" width="16" height="12" className="fill-snow" />
      <rect x="-2.5" y="-7" width="5" height="7" className="fill-gold" stroke="none" />
    </g>
  );
}

type Props = { days: ItineraryDay[]; places: Place[]; chosenDay: number | null };

export default function TripMap({ days, places, chosenDay }: Props) {
  const route = stops(days, places);
  if (route.length === 0) return null;
  const path = route.map((s, i) => `${i ? "L" : "M"} ${s.x} ${s.y}`).join(" ");
  const chosenStop = route.findIndex((s) => chosenDay !== null && s.days.includes(chosenDay));
  const length = route.slice(1).reduce((sum, s, i) => sum + Math.hypot(s.x - route[i].x, s.y - route[i].y), 0);
  const lap = Math.max(6, route.length * 2.5); // seconds for the train to travel the whole route

  return (
    <svg viewBox={frame(route)} className="panel block aspect-[4/3] w-full" role="img"
         aria-label={`Map of the route: ${route.map((s) => s.city).join(", then ")}`}>
      <defs>
        <radialGradient id="stop-glow">
          <stop offset="0" stopColor="rgb(244 195 90)" stopOpacity="0.6" />
          <stop offset="1" stopColor="rgb(244 195 90)" stopOpacity="0" />
        </radialGradient>
        {/* The railway draws itself in: a mask revealing the dotted line from start to end. */}
        <mask id="draw-route">
          <path d={path} fill="none" stroke="white" strokeWidth={14} strokeLinecap="round"
                strokeDasharray={length} strokeDashoffset={length} className="draw-in" />
        </mask>
      </defs>

      {COUNTRIES.map((country) => (
        <path key={country.iso + country.name} d={country.path} strokeWidth={1.5}
              className={OURS.has(country.name) ? "fill-pine/60 stroke-snow/25" : "fill-night/60 stroke-snow/10"} />
      ))}

      <g mask="url(#draw-route)">
        <path d={path} fill="none" className="stroke-gold/70" strokeWidth={3} strokeDasharray="2 7" strokeLinecap="round" />
        {chosenStop > 0 && (
          <line x1={route[chosenStop - 1].x} y1={route[chosenStop - 1].y} x2={route[chosenStop].x} y2={route[chosenStop].y}
                className="stroke-gold" strokeWidth={4} strokeLinecap="round" />
        )}
      </g>

      {route.map((stop, i) => {
        const glow = i === chosenStop;
        const label = labelPlace(stop, route);
        return (
          <g key={`${stop.city}-${i}`} transform={`translate(${stop.x} ${stop.y})`}>
            <circle r={glow ? 46 : 26} fill="url(#stop-glow)" className="transition-all duration-500" />
            {stop.markets ? <Tree glow={glow} /> : <House />}
            <text x={label.x} y={label.y} textAnchor={label.anchor}
                  className={`text-[18px] ${glow ? "fill-gold font-semibold" : "fill-snow"}`}>
              {stop.city === "Rothenburg ob der Tauber" ? "Rothenburg" : stop.city}
            </text>
            <text x={16} y={-26} className="fill-gold/80 text-[12px]">{i + 1}</text>
          </g>
        );
      })}

      {/* The little train: a red engine with a green wagon, travelling the route. */}
      {route.length > 1 && (
        <g className="motion-reduce:hidden">
          <g transform="translate(-12 -16)">
            <rect x="0" y="6" width="20" height="9" rx="1.5" className="fill-cranberry stroke-gold" strokeWidth={1.2} />
            <rect x="13" y="0" width="8" height="10" rx="1" className="fill-cranberry stroke-gold" strokeWidth={1.2} />
            <circle cx="5" cy="17" r="2.6" className="fill-night stroke-gold" strokeWidth={1.2} />
            <circle cx="15" cy="17" r="2.6" className="fill-night stroke-gold" strokeWidth={1.2} />
          </g>
          <animateMotion dur={`${lap}s`} repeatCount="indefinite" path={path} rotate="auto" />
        </g>
      )}
    </svg>
  );
}
