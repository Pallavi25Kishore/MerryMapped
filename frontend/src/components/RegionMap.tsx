"use client";

import type { Place } from "@/lib/api";
import { COUNTRIES, MAP, project } from "@/lib/mapShapes";

// The map on the trip form: our three countries, our market cities as glowing gold dots to tap, the
// chosen start and end marked, and big airports as faint landmarks (for orientation only). A train
// hub with no market (Brussels) is drawn faint grey like a landmark, but can still be tapped.

// Matched by name: Natural Earth stores France's code as "-99".
const OURS = new Set(["Germany", "France", "Belgium"]);

// Country names, placed by hand where they read well.
const COUNTRY_LABELS = [
  { name: "GERMANY", lat: 50.6, lon: 10.2 },
  { name: "FRANCE", lat: 47.6, lon: 4.0 },
  { name: "BELGIUM", lat: 49.95, lon: 5.15 },
  { name: "NETHERLANDS", lat: 52.75, lon: 5.6 },
];

// Big airports: landmarks only, not choices.
const AIRPORTS = [
  { name: "Frankfurt", lat: 50.038, lon: 8.562 },
  { name: "Munich", lat: 48.354, lon: 11.786 },
  { name: "Paris", lat: 49.01, lon: 2.548 },
  { name: "Amsterdam", lat: 52.31, lon: 4.768 },
  { name: "Zurich", lat: 47.458, lon: 8.556 },
  { name: "Berlin", lat: 52.367, lon: 13.503 },
];

// Where each city's name sits beside its dot, so close neighbours don't overlap.
const LABEL_SIDE: Record<string, "right" | "left" | "below" | "above"> = {
  "Rothenburg ob der Tauber": "left", Aachen: "above", Brussels: "below", Colmar: "below", Brugge: "above",
};

function labelAt(side: "right" | "left" | "below" | "above", x: number, y: number) {
  if (side === "left") return { x: x - 16, y: y + 8, anchor: "end" as const };
  if (side === "below") return { x, y: y + 34, anchor: "middle" as const };
  if (side === "above") return { x, y: y - 20, anchor: "middle" as const };
  return { x: x + 16, y: y + 8, anchor: "start" as const };
}

// The invisible area around each dot that takes a tap: about 44 px across on screen (a comfortable
// thumb), but never more than half the way to the nearest other city, so taps can't land on the
// wrong one.
const TAP_RADIUS = 38; // in map units

function tapRadii(places: Place[]): Map<string, number> {
  const points = places.map((p) => ({ city: p.city, ...project(p.lat, p.lon) }));
  return new Map(points.map((a) => {
    const nearest = Math.min(...points.filter((b) => b !== a).map((b) => Math.hypot(a.x - b.x, a.y - b.y)));
    return [a.city, Math.min(TAP_RADIUS, nearest / 2)];
  }));
}

type Props = {
  places: Place[];
  start?: string;
  end?: string;
  onPick: (city: string) => void;
};

export default function RegionMap({ places, start, end, onPick }: Props) {
  const radii = tapRadii(places);
  return (
    // The map has spare land above and below our cities: it fills its box, trimming only that spare
    // land (slice), so it can be as tall as the space beside it. On narrow screens it keeps one shape.
    <svg viewBox={`0 0 ${MAP.width} ${MAP.height}`} preserveAspectRatio="xMidYMid slice"
         className="aspect-[1000/760] w-full border border-snow/15 bg-night-deep/60 xl:absolute xl:inset-0 xl:aspect-auto xl:h-full"
         role="img" aria-label="Map of the cities: tap one to choose it">
      <defs>
        <radialGradient id="city-glow">
          <stop offset="0" stopColor="rgb(244 195 90)" stopOpacity="0.55" />
          <stop offset="1" stopColor="rgb(244 195 90)" stopOpacity="0" />
        </radialGradient>
      </defs>

      {COUNTRIES.map((country) => (
        <path key={country.iso + country.name} d={country.path}
              className={OURS.has(country.name) ? "fill-pine/70 stroke-snow/30" : "fill-night/70 stroke-snow/15"}
              strokeWidth={1.2} />
      ))}
      {COUNTRY_LABELS.map(({ name, lat, lon }) => {
        const { x, y } = project(lat, lon);
        return <text key={name} x={x} y={y} textAnchor="middle" className="fill-snow/25 text-[20px] tracking-[0.35em]">{name}</text>;
      })}

      {AIRPORTS.map(({ name, lat, lon }) => {
        const { x, y } = project(lat, lon);
        return (
          <g key={name} className="fill-frost/60" aria-hidden>
            <text x={x} y={y + 7} textAnchor="middle" className="text-[21px]">✈</text>
            <text x={x} y={y + 30} textAnchor="middle" className="text-[17px] italic">{name}</text>
          </g>
        );
      })}

      {places.map((place) => {
        const { x, y } = project(place.lat, place.lon);
        const label = labelAt(LABEL_SIDE[place.city] ?? "right", x, y);
        const marks = [place.city === start && "Start", place.city === end && "End"].filter(Boolean).join(" & ");
        const hub = !place.market_city;
        return (
          <g key={place.city} role="button" tabIndex={0} aria-label={`${place.city}${marks ? `, ${marks}` : ""}`}
             onClick={() => onPick(place.city)}
             onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && (event.preventDefault(), onPick(place.city))}
             className="group cursor-pointer outline-none">
            <circle cx={x} cy={y} r={radii.get(place.city)} fill="transparent" />
            {(!hub || marks) && (
              <circle cx={x} cy={y} r={marks ? 26 : 18} fill="url(#city-glow)" className="transition-all duration-300" />
            )}
            <circle cx={x} cy={y} r={marks ? 8 : hub ? 5 : 6} strokeWidth={2}
                    className={`transition-all duration-300 group-hover:stroke-snow group-focus-visible:stroke-snow
                                ${marks ? "fill-gold stroke-gold" : hub ? "fill-frost/60 stroke-frost/60" : "fill-gold stroke-gold"}`} />
            <text x={label.x} y={label.y} textAnchor={label.anchor}
                  className={`transition-colors group-hover:fill-gold ${marks ? "fill-gold font-semibold text-[24px]"
                              : hub ? "fill-frost/70 text-[19px] italic" : "fill-snow text-[24px]"}`}>
              {place.city === "Rothenburg ob der Tauber" ? "Rothenburg" : place.city}
              {hub && !marks && " · train hub"}
              {marks && <tspan className="fill-gold text-[18px] not-italic uppercase tracking-widest"> · {marks}</tspan>}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
