"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { longDate } from "@/components/DatePicker";
import { AccessCode } from "@/components/PlanForm";
import TicketButton from "@/components/TicketButton";
import { ApiError, deleteTrip, myTrips, setAccessCode, type Receipt, type TripSummary } from "@/lib/api";
import { play } from "@/lib/sound";

// Your trips: every saved trip as a card, newest first, with its dates, its cities in order and when it
// was planned. A card opens its trip; Delete asks first, then the card becomes the receipt. Without a
// valid access code it asks for one, like the planner.

type Load = { state: "loading" } | { state: "code"; wrong: boolean } | { state: "error" }
  | { state: "ready"; trips: TripSummary[] };

// A moment the backend gives in UTC, in the traveller's own time: "Thu, 15 Oct 2026, 18:30".
function moment(utc: string): string {
  return new Date(`${utc}Z`).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short",
                                                        year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function TripList() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [tries, setTries] = useState(0); // codes entered: after one, a refusal means it was wrong

  const fetchTrips = useCallback(() => {
    setLoad({ state: "loading" });
    myTrips()
      .then((trips) => setLoad({ state: "ready", trips }))
      .catch((error) => setLoad(error instanceof ApiError && error.needsAccessCode
                                  ? { state: "code", wrong: tries > 0 } : { state: "error" }));
  }, [tries]);

  useEffect(fetchTrips, [fetchTrips]);

  if (load.state === "loading") return <p className="text-frost">Gathering your trips…</p>;
  if (load.state === "code") {
    return (
      <div className="panel w-full max-w-md p-6 sm:p-8">
        <AccessCode wrong={load.wrong} purpose="see your trips"
                    onEnter={(code) => { setAccessCode(code); setTries((n) => n + 1); }} />
      </div>
    );
  }
  if (load.state === "error") {
    return (
      <div className="text-center">
        <p className="text-snow/85">Your trips can&apos;t be loaded right now. Please try again in a moment.</p>
        <TicketButton className="mt-5" onClick={fetchTrips}>Try again</TicketButton>
      </div>
    );
  }
  if (load.trips.length === 0) {
    return (
      <div className="panel w-full max-w-lg p-6 text-center sm:p-8">
        <p className="text-snow/85">No saved trips yet. Every trip you plan is kept here until you delete it.</p>
        <Link href="/?plan" className="mt-5 inline-block text-gold underline underline-offset-4 hover:text-snow">
          Plan a trip
        </Link>
      </div>
    );
  }
  return (
    <ul className="w-full max-w-3xl space-y-4">
      {load.trips.map((trip) => <TripCard key={trip.trip_id} trip={trip} />)}
    </ul>
  );
}

function TripCard({ trip }: { trip: TripSummary }) {
  const [step, setStep] = useState<"shown" | "confirm" | "deleting" | "failed">("shown");
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const dates = `${longDate(trip.first_day)} to ${longDate(trip.last_day)}`;

  const remove = () => {
    setStep("deleting");
    deleteTrip(trip.trip_id)
      .then((done) => { play("chime"); setReceipt(done); })
      .catch(() => setStep("failed"));
  };

  if (receipt) {
    return (
      <li className="panel rise-in p-5 text-left sm:p-6">
        <p className="text-xs uppercase tracking-[0.25em] text-gold">Deleted</p>
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
          <dt className="text-frost">Trip</dt><dd className="text-snow">{dates} · {trip.cities.join(" · ")}</dd>
          <dt className="text-frost">Planned</dt><dd className="text-snow">{moment(receipt.planned_at)}</dd>
          <dt className="text-frost">Deleted</dt><dd className="text-snow">{moment(receipt.deleted_at)}</dd>
        </dl>
        <p className="mt-3 text-sm text-snow/85">
          Nothing of it is kept: not your request, not the itinerary, not even this receipt.
        </p>
      </li>
    );
  }

  return (
    <li className="panel p-5 text-left transition hover:shadow-[0_0_24px_rgb(244_195_90/0.15)] sm:p-6">
      <div className="flex flex-wrap items-center gap-4">
        <Link href={`/trips/${encodeURIComponent(trip.trip_id)}`} className="group w-full min-w-0 sm:w-auto sm:flex-1">
          <p className="text-sm uppercase tracking-[0.2em] text-gold">{dates}</p>
          <p className="mt-1 font-display text-xl text-snow group-hover:text-gold [font-variation-settings:'SOFT'_100]">
            {trip.cities.join(" · ")}
          </p>
          <p className="mt-1 text-xs text-frost">Planned {moment(trip.created_at)}</p>
        </Link>
        {step === "shown" && (
          <div className="flex gap-3">
            <Link href={`/trips/${encodeURIComponent(trip.trip_id)}`}
                  className="border-[1.5px] border-gold/80 bg-night px-5 py-2.5 text-sm font-semibold uppercase
                             tracking-[0.22em] text-gold transition hover:shadow-[0_0_18px_rgb(244_195_90/0.5)]">
              Open
            </Link>
            <TicketButton kind="quiet" className="px-5! py-2.5! text-sm!" onClick={() => setStep("confirm")}>
              Delete
            </TicketButton>
          </div>
        )}
      </div>

      {step !== "shown" && (
        <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-snow/10 pt-4">
          <p className="flex-1 text-snow">
            {step === "failed" ? "We couldn't delete it just now. Please try again."
                               : "Delete this trip? This can't be undone."}
          </p>
          <TicketButton className="px-5! py-2.5! text-sm!" onClick={remove} disabled={step === "deleting"}>
            {step === "deleting" ? "Deleting…" : "Yes, delete it"}
          </TicketButton>
          <TicketButton kind="quiet" className="px-5! py-2.5! text-sm!" onClick={() => setStep("shown")}
                        disabled={step === "deleting"}>
            Keep it
          </TicketButton>
        </div>
      )}
    </li>
  );
}
