"use client";

import { useEffect, useState } from "react";
import CityPicker from "@/components/CityPicker";
import ConfirmView from "@/components/ConfirmView";
import DatePicker from "@/components/DatePicker";
import PaceSettings from "@/components/PaceSettings";
import TicketButton from "@/components/TicketButton";
import { ApiError, getOptions, setAccessCode, understand, type Options, type Settings, type TripForm,
         type Understood } from "@/lib/api";

// The trip form inside the planning panel. It first loads what the form needs from the backend
// (the trip dates, our cities and the settings); without a valid access code it asks for one. The
// dates are required; everything else has a sensible default. See my plan asks the backend to read
// the form and the typed wishes, then shows the confirm screen in the form's place.

const MAX_TEXT = 2000; // the most the backend accepts for typed wishes

type Load = { state: "loading" } | { state: "code"; wrong: boolean } | { state: "error"; outdated?: boolean }
  | { state: "ready"; options: Options };

type Props = {
  onBack: () => void;
  onPlan?: (understood: Understood) => void; // Plan my trip (planning comes next)
};

export default function PlanForm({ onBack, onPlan }: Props) {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0); // bumped to load again
  const [form, setForm] = useState<TripForm>({});
  const [reading, setReading] = useState(false); // waiting for the backend to read the wishes
  const [problem, setProblem] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<Understood | null>(null);

  // The confirm screen and the form replace each other: start each at the top of the panel.
  useEffect(() => {
    document.querySelector('section[aria-label="Plan your trip"]')?.scrollTo({ top: 0, behavior: "smooth" });
  }, [confirm]);

  const seeMyPlan = () => {
    setReading(true);
    setProblem(null);
    understand(form)
      .then(setConfirm)
      .catch((error) => {
        if (error instanceof ApiError && error.needsAccessCode) setLoad({ state: "code", wrong: true });
        else setProblem("We couldn't read your wishes just now. Please try again in a moment.");
      })
      .finally(() => setReading(false));
  };

  useEffect(() => {
    let current = true;
    getOptions()
      .then((options) => {
        if (!current) return;
        // A backend started before the latest changes may lack fields the form needs.
        if (!Array.isArray(options.places)) setLoad({ state: "error", outdated: true });
        else setLoad({ state: "ready", options });
      })
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

  const back = <TicketButton kind="quiet" onClick={onBack}>Back</TicketButton>;

  if (load.state === "loading") {
    return <><p className="mt-6 text-frost">Preparing your planner…</p><div className="mt-8">{back}</div></>;
  }
  if (load.state === "error") {
    return (
      <div className="mt-6">
        <p className="text-snow/85">
          {load.outdated ? "The backend is running older code. Please restart it, then try again."
                         : "The planner can't be reached right now. Is the backend running?"}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {back}
          <TicketButton onClick={retry}>Try again</TicketButton>
        </div>
      </div>
    );
  }
  if (load.state === "code") {
    return (
      <>
        <AccessCode wrong={load.wrong} onEnter={(code) => { setAccessCode(code); retry(); }} />
        <div className="mt-8">{back}</div>
      </>
    );
  }

  const { options } = load;
  if (confirm) {
    const defaults = Object.fromEntries(Object.entries(options.settings).map(([key, range]) => [key, range.default]));
    return <ConfirmView understood={confirm} form={form} defaults={defaults as Settings}
                        onEdit={() => setConfirm(null)} onPlan={() => onPlan?.(confirm)} />;
  }
  const datesChosen = Boolean(form.first_day && form.last_day);
  const text = form.text ?? "";
  return (
    <div className="mt-6 text-left">
      {/* One column, about 592 px wide. On wide screens, two such columns side by side (same sizes as one
          column): the text-like parts on the left, the map on the right. */}
      <div className="grid gap-8 xl:grid-cols-2 xl:gap-12">
        <div className="space-y-8">
          <section>
            <h3 className="mb-3 text-sm uppercase tracking-[0.25em] text-gold">
              When <span className="normal-case tracking-normal text-frost">· required</span>
            </h3>
            <DatePicker firstAllowed={options.first_day} lastAllowed={options.last_day}
                        firstDay={form.first_day} lastDay={form.last_day}
                        onChange={(first_day, last_day) => setForm((f) => ({ ...f, first_day, last_day }))} />
          </section>

          <section>
            <h3 className="mb-3 text-sm uppercase tracking-[0.25em] text-gold">Your pace</h3>
            <PaceSettings ranges={options.settings} changed={form.settings ?? {}}
                          onChange={(update) => setForm((f) => ({ ...f, settings: update(f.settings ?? {}) }))} />
          </section>
        </div>

        {/* Stretches to the left column's height; the map fills what is left under the tabs. */}
        <section className="flex flex-col">
          <h3 className="mb-3 text-sm uppercase tracking-[0.25em] text-gold">Where</h3>
          <div className="flex-1">
            <CityPicker places={options.places} start={form.start_city} end={form.end_city}
                        onChange={(start_city, end_city) => setForm((f) => ({ ...f, start_city, end_city }))} />
          </div>
        </section>
      </div>

      <section className="mt-8">
        <h3 className="mb-3 text-sm uppercase tracking-[0.25em] text-gold">Your wishes</h3>
        <label htmlFor="wishes" className="sr-only">Your wishes</label>
        <textarea id="wishes" rows={3} maxLength={MAX_TEXT} value={text}
                  onChange={(event) => setForm((f) => ({ ...f, text: event.target.value }))}
                  placeholder="Tell us what you'd love: old towns, mulled wine, not too touristy…"
                  className="block w-full resize-y border border-snow/20 bg-night-deep/50 px-4 py-3 text-snow outline-none
                             transition placeholder:text-snow/35 focus:border-gold" />
        <div className="mt-2 flex justify-between gap-4 text-sm text-frost">
          <span>Santa can&apos;t promise everything, but we&apos;ll fit in as many wishes as the trains allow.</span>
          <span className="tabular-nums">{text.length} / {MAX_TEXT}</span>
        </div>
      </section>

      <div className="mt-8 flex flex-wrap items-center justify-end gap-3">
        <span className="mr-2 text-sm text-frost" aria-live="polite">
          {problem ?? (!datesChosen ? "Choose your dates to continue" : "")}
        </span>
        {back}
        <TicketButton disabled={!datesChosen || reading} onClick={seeMyPlan}>
          {reading ? "Reading your wishes…" : "See my plan"}
        </TicketButton>
      </div>
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
