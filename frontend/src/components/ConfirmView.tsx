"use client";

import { longDate } from "@/components/DatePicker";
import TicketButton from "@/components/TicketButton";
import type { Settings, TripForm, Understood } from "@/lib/api";

// The confirm screen: "Here's what I understood". The trip in plain words, settings picked up from the
// typed wishes marked in gold, the wishes and the tags we'll look out for, the backend's notes, and
// what MerryMapped can't arrange. Edit returns to the form; Plan my trip starts planning.

function hhmm(minutes: number): string {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function hours(minutes: number): string {
  const h = Math.floor(minutes / 60), m = minutes % 60;
  return h && m ? `${h} h ${m} min` : h ? `${h} h` : `${m} min`;
}

const PACE: { key: keyof Settings; say: (value: never) => string }[] = [
  { key: "earliest_train", say: (m: number) => `No trains before ${hhmm(m)}` },
  { key: "min_market_minutes", say: (m: number) => `At least ${hours(m)} at each market` },
  { key: "max_travel_minutes", say: (m: number) => `At most ${hours(m)} of train travel a day` },
  { key: "max_markets_per_day", say: (n: number) => `Up to ${n} ${n === 1 ? "market" : "markets"} a day` },
  { key: "day_trips", say: (on: boolean) => (on ? "Day trips welcome" : "No day trips") },
];

function tagLabel(tag: string): string {
  const words = tag.replace(/-/g, " ");
  return words[0].toUpperCase() + words.slice(1);
}

function Row({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 border-b border-snow/10 py-4 sm:grid-cols-[10rem_1fr] sm:gap-6">
      <div className="text-sm uppercase tracking-[0.25em] text-gold">{title}</div>
      <div className="text-snow">{children}</div>
    </div>
  );
}

type Props = {
  understood: Understood;
  form: TripForm; // what was chosen on the form, to tell apart settings that came from the typed wishes
  defaults: Settings;
  onEdit: () => void;
  onPlan?: () => void;
};

export default function ConfirmView({ understood, form, defaults, onEdit, onPlan }: Props) {
  const { request, notes, not_covered } = understood;

  return (
    <div className="rise-in mt-6 text-left">
      <p className="text-center text-snow/80">Here&apos;s what we understood. Have a look before we plan.</p>

      {request && (
        <div className="mt-4">
          <Row title="When">
            {longDate(request.first_day)} to {longDate(request.last_day)}
            <span className="text-frost"> · {(Date.parse(request.last_day) - Date.parse(request.first_day)) / 86_400_000 + 1} days</span>
          </Row>
          <Row title="Where">
            {request.start_city ? `Start in ${request.start_city}` : "Start anywhere"}
            <span className="text-frost"> · </span>
            {request.end_city ? `finish in ${request.end_city}` : "finish anywhere"}
          </Row>
          <Row title="Your pace">
            <ul className="space-y-1">
              {PACE.map(({ key, say }) => {
                const value = request.settings[key];
                const fromWishes = value !== (form.settings?.[key] ?? defaults[key]);
                return (
                  <li key={key} className={fromWishes ? "text-gold" : undefined}>
                    {(say as (v: typeof value) => string)(value)}
                    {fromWishes && <span className="text-sm italic text-gold/80"> · from your wishes</span>}
                  </li>
                );
              })}
            </ul>
          </Row>
          <Row title="Your wishes">
            {request.wishes.length ? (
              <div className="flex flex-wrap gap-2">
                {request.wishes.map((wish) => (
                  <span key={wish} className="border border-snow/20 bg-night-deep/40 px-3 py-1 text-sm">{wish}</span>
                ))}
              </div>
            ) : (
              <span className="text-frost">None given: we&apos;ll simply plan a lovely trip.</span>
            )}
            {request.tags.length > 0 && (
              <p className="mt-3 text-sm text-frost">
                We&apos;ll look out for: <span className="text-gold">{request.tags.map(tagLabel).join(" · ")}</span>
              </p>
            )}
          </Row>
        </div>
      )}

      {(notes.length > 0 || not_covered.length > 0) && (
        <div className="mt-6 space-y-2 border border-gold/25 bg-night-deep/40 px-5 py-4 text-sm text-snow/90">
          {notes.map((note) => <p key={note}><span aria-hidden className="mr-2 text-gold">✦</span>{note}</p>)}
          {not_covered.length > 0 && (
            <p>
              <span aria-hidden className="mr-2 text-gold">✦</span>
              A few things MerryMapped can&apos;t arrange: {not_covered.join(", ")}. We&apos;ll plan everything else.
            </p>
          )}
        </div>
      )}

      <div className="mt-8 flex flex-wrap items-center justify-end gap-3">
        <TicketButton kind="quiet" onClick={onEdit}>Edit</TicketButton>
        {request && <TicketButton onClick={onPlan}>Plan my trip</TicketButton>}
      </div>
    </div>
  );
}
