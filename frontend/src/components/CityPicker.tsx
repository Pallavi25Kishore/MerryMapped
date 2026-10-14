"use client";

import { useState } from "react";
import RegionMap from "@/components/RegionMap";
import type { Place } from "@/lib/api";

// Where: two tabs (Start in, End in) showing the choices, and the map to tap a city on. An empty tab
// reads "Anywhere" (the planner decides); a chosen city can be cleared with its ✕.

type Props = {
  places: Place[];
  start?: string;
  end?: string;
  onChange: (start: string | undefined, end: string | undefined) => void;
};

export default function CityPicker({ places, start, end, onChange }: Props) {
  const [choosing, setChoosing] = useState<"start" | "end">("start");
  const set = (which: "start" | "end", city: string | undefined) =>
    which === "start" ? onChange(city, end) : onChange(start, city);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3" role="tablist" aria-label="Choose where the trip starts or ends">
        {([["start", "Start in", start], ["end", "End in", end]] as const).map(([key, label, city]) => (
          <div key={key} className={`relative border transition duration-200
                                     ${choosing === key ? "border-gold bg-night-deep/60" : "border-snow/20 bg-night-deep/30 hover:border-snow/50"}`}>
            <button type="button" role="tab" aria-selected={choosing === key} onClick={() => setChoosing(key)}
                    className="w-full px-4 py-2.5 text-left focus-visible:outline-2 focus-visible:outline-snow">
              <div className={`text-xs uppercase tracking-[0.2em] ${choosing === key ? "text-gold" : "text-frost"}`}>{label}</div>
              {city ? <div className="pr-6 text-snow">{city}</div>
                    : <div className="text-snow/45">Anywhere <span className="text-xs italic">· tap a city on the map</span></div>}
            </button>
            {city && (
              <button type="button" aria-label={`Clear ${label.toLowerCase()}: back to Anywhere`}
                      onClick={() => set(key, undefined)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-frost transition hover:text-gold
                                 focus-visible:outline-2 focus-visible:outline-snow">
                ✕
              </button>
            )}
          </div>
        ))}
      </div>

      <RegionMap places={places} start={start} end={end} onPick={(city) => set(choosing, city)} />
    </div>
  );
}
