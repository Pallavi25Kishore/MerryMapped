"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { longDate } from "@/components/DatePicker";
import { ApiError, openTrip, type Trip } from "@/lib/api";

// A saved trip, loaded in the browser (it needs the access code). For now a simple day-by-day list;
// the day cards, the map with train lines and the wish review come next.

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
  return (
    <div className="rise-in w-full max-w-3xl space-y-4">
      <h1 className="text-center font-display text-4xl font-semibold [font-variation-settings:'SOFT'_100]">Your trip</h1>
      {itinerary.days.map((day, n) => (
        <div key={day.date} className="border border-snow/15 bg-night/55 p-5 backdrop-blur-md">
          <div className="text-sm uppercase tracking-[0.25em] text-gold">Day {n + 1} · {longDate(day.date)}</div>
          {day.travel?.train && (
            <p className="mt-2 text-snow/90">
              {day.travel.from} {day.travel.train.depart} → {day.travel.to} {day.travel.train.arrive}
            </p>
          )}
          <ul className="mt-2 text-snow">
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
  );
}
