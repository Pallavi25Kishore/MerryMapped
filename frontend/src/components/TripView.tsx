"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { longDate } from "@/components/DatePicker";
import StringLights from "@/components/StringLights";
import TrainJourney from "@/components/TrainJourney";
import { ApiError, openTrip, type Itinerary, type Trip } from "@/lib/api";
import { numberWord } from "@/lib/words";

// A saved trip, loaded in the browser (it needs the access code): string lights across the top, a
// headline, the map's place on the left (staying in view) and the days on the right. The advent
// doors, the holiday map and the wish review come next.

// "Ten days of Christmas markets, from Köln to Dresden".
function headline(itinerary: Itinerary): string {
  const { days } = itinerary;
  const first = days[0].travel?.from ?? days[0].sleep_in, last = days[days.length - 1].sleep_in;
  const route = first === last ? `, starting and ending in ${first}` : `, from ${first} to ${last}`;
  return `${numberWord(days.length)} ${days.length === 1 ? "day" : "days"} of Christmas markets${route}`;
}

type Load = { state: "loading" } | { state: "missing" } | { state: "error" } | { state: "ready"; trip: Trip };

export default function TripView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [load, setLoad] = useState<Load>({ state: "loading" });

  useEffect(() => {
    let current = true;
    openTrip(id)
      .then((trip) => current && setLoad({ state: "ready", trip }))
      .catch((error) => current && setLoad({ state: error instanceof ApiError && error.status === 404 ? "missing" : "error" }));
    return () => {
      current = false;
    };
  }, [id]);

  if (load.state === "loading") return <p className="text-frost">Opening your trip…</p>;
  if (load.state !== "ready") {
    return (
      <div className="text-center">
        <p className="text-snow/85">
          {load.state === "missing" ? "We couldn't find this trip. It may have been deleted."
                                    : "Your trip can't be opened right now. Please try again in a moment."}
        </p>
        <Link href="/" className="mt-4 inline-block text-gold underline underline-offset-4">Back to the start</Link>
      </div>
    );
  }

  const { itinerary } = load.trip;
  const { days } = itinerary;
  return (
    <div className="w-full">
      <StringLights />
      <div className="rise-in mx-auto max-w-[1312px] px-4 text-center">
        <p className="text-sm uppercase tracking-[0.3em] text-gold">✦ Your trip ✦</p>
        <h1 className="mt-3 font-display text-3xl font-semibold sm:text-5xl [font-variation-settings:'SOFT'_100]">
          {headline(itinerary)}
        </h1>
        <p className="mt-3 text-lg text-gold">{longDate(days[0].date)} to {longDate(days[days.length - 1].date)}</p>
      </div>

      <div className="mx-auto mt-10 grid max-w-[1312px] gap-8 px-4 xl:grid-cols-[5fr_7fr]">
        {/* The holiday map comes here (piece 3); it stays in view while the days scroll. */}
        <div className="hidden xl:block">
          <div className="sticky top-6 flex aspect-[4/5] items-center justify-center border border-gold/20 bg-night/40
                          text-frost backdrop-blur-sm">
            Your holiday map is on its way
          </div>
        </div>

        <div className="space-y-4">
          {days.map((day, n) => (
            <div key={day.date} className="border border-snow/15 bg-night/55 p-5 text-left backdrop-blur-md">
              <div className="text-sm uppercase tracking-[0.25em] text-gold">
                Day {n + 1} · {longDate(day.date)} · {day.sleep_in}
              </div>
              {day.travel && <div className="mt-3"><TrainJourney travel={day.travel} /></div>}
              <ul className="mt-3 text-snow">
                {day.visits.map((visit) => <li key={visit.market_id}>✦ {visit.name}</li>)}
                {day.free_day && (
                  <li>
                    <span className="text-gold">Free day in {day.free_day.city}</span>
                    <span className="italic text-snow/85"> · a lovely day for sightseeing.</span>
                    {day.free_day.reason === "closed" && <span className="text-frost"> The Christmas market is closed today.</span>}
                  </li>
                )}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
