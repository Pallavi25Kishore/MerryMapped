"use client";

import { longDate } from "@/components/DatePicker";
import RegionMap from "@/components/RegionMap";
import TicketButton from "@/components/TicketButton";
import type { Place, Settings, TripForm, Understood } from "@/lib/api";
import { hhmm, hours, numberWord } from "@/lib/words";

// The confirm screen, like a Christmas card: a headline about the trip, then three cards (where, with
// a small map; the pace, marking what was asked for in the wishes; every wish, in the traveller's own
// words, as a tile), a little note with the backend's notes and what MerryMapped can't include, and
// Back (to the form) or Plan my trip.

const PACE: { key: keyof Settings; say: (value: never) => string }[] = [
  { key: "earliest_train", say: (m: number) => `No trains before ${hhmm(m)}` },
  { key: "min_market_minutes", say: (m: number) => `At least ${hours(m)} at each market` },
  { key: "max_travel_minutes", say: (m: number) => `At most ${hours(m)} of train travel a day` },
  { key: "max_markets_per_day", say: (n: number) => `Up to ${n} ${n === 1 ? "market" : "markets"} a day` },
  { key: "day_trips", say: (on: boolean) => (on ? "Day trips welcome" : "No day trips") },
];

// Thin gold line icons, drawn in code so they stay crisp and classy.
const ICONS = {
  where: <path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21zm0-9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z" />,
  pace: <path d="M7 15V7a5 5 0 0 1 10 0v8a3 3 0 0 1-3 3h-4a3 3 0 0 1-3-3zm0-4h10M9.5 14.5h.01M14.5 14.5h.01M9 18l-2 3M15 18l2 3" />,
  wishes: <path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z" />,
};

function Card({ icon, title, delay, children }: { icon: keyof typeof ICONS; title: string; delay: number; children: React.ReactNode }) {
  return (
    <div className="rise-in border border-gold/25 bg-night-deep/45 p-5 shadow-[0_0_30px_rgb(0_0_0/0.25)]"
         style={{ animationDelay: `${delay}ms` }}>
      <div className="mb-4 flex items-center gap-3">
        <svg viewBox="0 0 24 24" className="h-6 w-6 text-gold" fill="none" stroke="currentColor" strokeWidth="1.4"
             strokeLinecap="round" strokeLinejoin="round" aria-hidden>{ICONS[icon]}</svg>
        <h3 className="text-sm uppercase tracking-[0.25em] text-gold">{title}</h3>
      </div>
      {children}
    </div>
  );
}

type Props = {
  understood: Understood;
  form: TripForm; // what was chosen on the form, to tell apart settings that came from the typed wishes
  defaults: Settings;
  places: Place[];
  onEdit: () => void;
  onPlan?: (event: React.MouseEvent<HTMLButtonElement>) => void;
};

export default function ConfirmView({ understood, form, defaults, places, onEdit, onPlan }: Props) {
  const { request, notes, not_covered } = understood;
  const days = request ? (Date.parse(request.last_day) - Date.parse(request.first_day)) / 86_400_000 + 1 : 0;
  const route = request?.start_city && request?.end_city
    ? request.start_city === request.end_city ? `, starting and ending in ${request.start_city}`
                                              : `, from ${request.start_city} to ${request.end_city}`
    : request?.start_city ? `, starting in ${request.start_city}`
    : request?.end_city ? `, ending in ${request.end_city}` : "";
  const tiles = request?.wishes ?? []; // only the traveller's own words (tags stay in the background)

  return (
    <div className="mt-2 text-center">
      {request && (
        <div className="rise-in">
          <p className="text-sm uppercase tracking-[0.3em] text-gold">✦ Here&apos;s your trip, in a nutshell ✦</p>
          <p className="mt-4 font-display text-3xl font-semibold text-snow sm:text-4xl [font-variation-settings:'SOFT'_100]">
            {numberWord(days)} {days === 1 ? "day" : "days"} of Christmas markets{route}
          </p>
          <p className="mt-2 text-lg text-gold">{longDate(request.first_day)} to {longDate(request.last_day)}</p>
          <div aria-hidden className="mx-auto mt-5 flex max-w-sm items-center gap-4 text-gold/70">
            <span className="h-px flex-1 bg-gradient-to-r from-transparent to-gold/50" />❄
            <span className="h-px flex-1 bg-gradient-to-l from-transparent to-gold/50" />
          </div>
        </div>
      )}

      {request && (
        <div className="mt-8 grid gap-5 text-left lg:grid-cols-3">
          <Card icon="where" title="Where" delay={150}>
            <RegionMap places={places} start={request.start_city ?? undefined} end={request.end_city ?? undefined} compact />
            <p className="mt-3 text-snow">
              {request.start_city ? `Start in ${request.start_city}` : "Start anywhere"}
              <span className="text-frost"> · </span>
              {request.end_city ? `finish in ${request.end_city}` : "finish anywhere"}
            </p>
          </Card>

          <Card icon="pace" title="Your pace" delay={300}>
            <ul className="space-y-2">
              {PACE.map(({ key, say }) => {
                const value = request.settings[key];
                const asked = value !== (form.settings?.[key] ?? defaults[key]);
                return (
                  <li key={key} className={asked ? "text-gold" : "text-snow"}>
                    {(say as (v: typeof value) => string)(value)}
                    {asked && <span className="ml-2 text-xs italic text-gold/80">✦ you asked</span>}
                  </li>
                );
              })}
            </ul>
          </Card>

          <Card icon="wishes" title="Your wishes" delay={450}>
            {tiles.length ? (
              <div className="flex flex-wrap gap-2">
                {tiles.map((tile) => (
                  <span key={tile} className="border border-gold/40 bg-gold/10 px-3 py-1.5 text-sm text-snow
                                              shadow-[0_0_12px_rgb(244_195_90/0.18)]">
                    {tile}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-frost">No wishes given, so we&apos;ll simply plan you a lovely trip.</p>
            )}
          </Card>
        </div>
      )}

      {(notes.length > 0 || not_covered.length > 0) && (
        <div className="rise-in mt-6 space-y-2 border border-gold/25 bg-night-deep/40 px-5 py-4 text-left text-sm text-snow/90"
             style={{ animationDelay: "600ms" }}>
          <p className="text-xs uppercase tracking-[0.25em] text-gold">A little note</p>
          {notes.map((note) => <p key={note}><span aria-hidden className="mr-2 text-gold">✦</span>{note}</p>)}
          {not_covered.length > 0 && (
            <p>
              <span aria-hidden className="mr-2 text-gold">✦</span>
              MerryMapped can&apos;t include {not_covered.join(", ")}, so we&apos;ll plan everything else.
            </p>
          )}
        </div>
      )}

      <div className="mt-8 flex flex-wrap items-center justify-end gap-3">
        <TicketButton kind="quiet" onClick={onEdit}>Back</TicketButton>
        {request && <TicketButton onClick={onPlan}>Plan my trip</TicketButton>}
      </div>
    </div>
  );
}
