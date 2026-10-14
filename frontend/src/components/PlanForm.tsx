"use client";

import { useEffect, useState } from "react";
import CityPicker from "@/components/CityPicker";
import DatePicker from "@/components/DatePicker";
import TicketButton from "@/components/TicketButton";
import { ApiError, getOptions, setAccessCode, type Options, type TripForm } from "@/lib/api";

// The trip form inside the planning panel. It first loads what the form needs from the backend
// (the trip dates, our cities and the settings); without a valid access code it asks for one.

type Load = { state: "loading" } | { state: "code"; wrong: boolean } | { state: "error" } | { state: "ready"; options: Options };

export default function PlanForm() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0); // bumped to load again
  const [form, setForm] = useState<TripForm>({});

  useEffect(() => {
    let current = true;
    getOptions()
      .then((options) => current && setLoad({ state: "ready", options }))
      .catch((error) => {
        if (!current) return;
        if (error instanceof ApiError && error.needsAccessCode) setLoad({ state: "code", wrong: attempt > 0 });
        else setLoad({ state: "error" });
      });
    return () => {
      current = false;
    };
  }, [attempt]);

  const retry = () => {
    setLoad({ state: "loading" });
    setAttempt((n) => n + 1);
  };

  if (load.state === "loading") return <p className="mt-6 text-frost">Preparing your planner…</p>;
  if (load.state === "error") {
    return (
      <div className="mt-6">
        <p className="text-snow/85">The planner can&apos;t be reached right now. Is the backend running?</p>
        <TicketButton kind="quiet" className="mt-5" onClick={retry}>Try again</TicketButton>
      </div>
    );
  }
  if (load.state === "code") return <AccessCode wrong={load.wrong} onEnter={(code) => { setAccessCode(code); retry(); }} />;

  const { options } = load;
  return (
    <div className="mt-6 space-y-8 text-left">
      <section>
        <h3 className="mb-3 text-sm uppercase tracking-[0.25em] text-gold">When</h3>
        <DatePicker firstAllowed={options.first_day} lastAllowed={options.last_day}
                    firstDay={form.first_day} lastDay={form.last_day}
                    onChange={(first_day, last_day) => setForm((f) => ({ ...f, first_day, last_day }))} />
      </section>

      <section className="space-y-5">
        <h3 className="text-sm uppercase tracking-[0.25em] text-gold">Where</h3>
        <CityPicker label="Start in" cities={options.cities} value={form.start_city}
                    onChange={(start_city) => setForm((f) => ({ ...f, start_city }))} />
        <CityPicker label="End in" cities={options.cities} value={form.end_city}
                    onChange={(end_city) => setForm((f) => ({ ...f, end_city }))} />
      </section>
    </div>
  );
}

// Asked once: the code from backend/.env, then remembered in this browser.
function AccessCode({ wrong, onEnter }: { wrong: boolean; onEnter: (code: string) => void }) {
  const [code, setCode] = useState("");
  return (
    <form className="mt-6 text-left" onSubmit={(event) => { event.preventDefault(); if (code.trim()) onEnter(code.trim()); }}>
      <label htmlFor="access-code" className="block text-snow/85">Enter your access code to start planning.</label>
      <input id="access-code" type="password" autoComplete="current-password" value={code}
             onChange={(event) => setCode(event.target.value)}
             className="mt-3 w-full border border-snow/25 bg-night-deep/50 px-4 py-3 text-snow outline-none
                        transition focus:border-gold" />
      {wrong && <p className="mt-2 text-sm text-cranberry">That code didn&apos;t work. Please check it and try again.</p>}
      <TicketButton type="submit" className="mt-5">Continue</TicketButton>
    </form>
  );
}
