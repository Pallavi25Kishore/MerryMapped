"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import MarketDetails from "@/components/MarketDetails";
import TripMap from "@/components/TripMap";
import TripTimeline, { type Chosen } from "@/components/TripTimeline";
import { longDate } from "@/components/DatePicker";
import StringLights from "@/components/StringLights";
import { ApiError, getOptions, openTrip, type Itinerary, type Place, type Trip } from "@/lib/api";
import { play } from "@/lib/sound";
import { numberWord } from "@/lib/words";

// A saved trip, loaded in the browser (it needs the access code): string lights across the top, a
// headline, the whole itinerary flowing down the left, and on the right (staying in view) the map's
// place and one description box for the chosen market. On phones the description slides up from the
// bottom. The holiday map and the wish review come next.

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
  const [chosen, setChosen] = useState<Chosen>(null); // the market in the description box
  const [sheet, setSheet] = useState(false); // phones: the description slid up from the bottom
  const [places, setPlaces] = useState<Place[] | null>(null); // the cities' positions, for the map

  useEffect(() => {
    getOptions().then((options) => setPlaces(options.places ?? null)).catch(() => setPlaces(null));
  }, []);

  useEffect(() => {
    let current = true;
    openTrip(id)
      .then((trip) => {
        if (!current) return;
        setLoad({ state: "ready", trip });
        // Start with the first market, so the description box is never empty.
        const first = trip.itinerary.days.findIndex((day) => day.visits.length > 0);
        if (first >= 0) setChosen({ day: first, market: 0 });
      })
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
  const visit = chosen ? days[chosen.day].visits[chosen.market] : undefined;
  const when = chosen ? `Day ${chosen.day + 1} · ${longDate(days[chosen.day].date)}` : "";

  function choose(day: number, market: number) {
    if (chosen?.day !== day || chosen.market !== market) play("reveal");
    setChosen({ day, market });
    setSheet(true);
  }
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

      <div className="mx-auto mt-10 grid max-w-[1312px] gap-10 px-4 xl:grid-cols-[7fr_5fr]">
        <div className="space-y-6">
          {/* Phones and narrower screens: the map sits above the itinerary. */}
          {places && <div className="xl:hidden"><TripMap days={days} places={places} chosenDay={chosen?.day ?? null} /></div>}
          <TripTimeline days={days} chosen={chosen} onChoose={choose} />
        </div>

        {/* Staying in view: the map's place, and the description box. */}
        <aside className="hidden xl:block">
          {/* Scrolls inside itself when a long description is taller than the screen. */}
          <div className="sticky top-6 max-h-[calc(100vh-3rem)] space-y-5 overflow-y-auto">
            {places ? <TripMap days={days} places={places} chosenDay={chosen?.day ?? null} />
                    : <div className="panel aspect-[4/3]" />}
            {visit && <MarketDetails visit={visit} when={when} />}
          </div>
        </aside>
      </div>

      {/* Phones: the description slides up from the bottom. */}
      {sheet && visit && (
        <div className="fixed inset-x-0 bottom-0 z-40 max-h-[75vh] overflow-y-auto xl:hidden">
          <div className="relative">
            <button type="button" onClick={() => setSheet(false)} aria-label="Close"
                    className="absolute right-3 top-3 z-10 px-2 py-1 text-frost hover:text-gold">✕</button>
            <MarketDetails visit={visit} when={when} />
          </div>
        </div>
      )}
    </div>
  );
}
