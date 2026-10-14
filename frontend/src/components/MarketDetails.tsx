"use client";

import { useState } from "react";
import WhyPanel from "@/components/WhyPanel";
import type { Visit } from "@/lib/api";
import { play } from "@/lib/sound";

// The description box: one market's story. Its name, the day it is visited, its vibe tiles, why it
// suits this traveller, its description, the "Don't miss" items (from its checked details), and its
// official website, and "Why can I see this?", which opens the proof behind every fact.

export default function MarketDetails({ visit, when }: { visit: Visit; when: string }) {
  const [why, setWhy] = useState(false);
  return (
    <div key={visit.market_id} className="panel snow-cap rise-in relative p-5 text-left
                                          shadow-[0_0_40px_rgb(244_195_90/0.12)] sm:p-6">
      <p className="text-xs uppercase tracking-[0.25em] text-gold">{when}</p>
      <h3 className="mt-1 font-display text-2xl font-semibold [font-variation-settings:'SOFT'_100]">{visit.name}</h3>

      {visit.tiles.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {visit.tiles.map((tile) => (
            <span key={tile} className="border border-gold/40 bg-gold/10 px-2.5 py-0.5 text-xs text-snow">{tile}</span>
          ))}
        </div>
      )}

      {visit.why && <p className="mt-4 text-snow"><span className="text-gold">Why you&apos;ll love it · </span>{visit.why}</p>}
      {visit.description && <p className="mt-3 text-sm leading-relaxed text-snow/85">{visit.description}</p>}

      {visit.dont_miss.length > 0 && (
        <div className="mt-4">
          <p className="text-xs uppercase tracking-[0.25em] text-gold">Don&apos;t miss</p>
          <ul className="mt-2 space-y-1.5 text-sm text-snow/90">
            {visit.dont_miss.map((item) => (
              <li key={item} className="flex gap-2">
                <span aria-hidden className="text-gold">✦</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        {visit.website && (
          <a href={visit.website} target="_blank" rel="noopener noreferrer"
             className="text-gold underline underline-offset-4 hover:text-snow">
            Official website ↗
          </a>
        )}
        <button type="button" onClick={() => { play("reveal"); setWhy(true); }}
                className="text-frost underline decoration-dotted underline-offset-4 hover:text-gold">
          Why can I see this?
        </button>
      </div>
      {why && <WhyPanel marketId={visit.market_id} name={visit.name} onClose={() => setWhy(false)} />}
    </div>
  );
}
