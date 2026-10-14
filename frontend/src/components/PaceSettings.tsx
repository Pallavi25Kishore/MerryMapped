"use client";

import type { Settings, SettingRange } from "@/lib/api";
import { hhmm, hours } from "@/lib/words";

// Your pace: the planner's settings, always shown. Each has a plain label and a − value + control
// within the backend's limits; day trips is an on/off switch. Only settings the traveller changed
// are kept (the rest stay at their defaults).

type Numeric = Exclude<keyof Settings, "day_trips">;

const STEPPERS: { key: Numeric; label: string; step: number; show: (value: number) => string }[] = [
  { key: "earliest_train", label: "No trains before", step: 30, show: hhmm },
  { key: "min_market_minutes", label: "At each market, at least", step: 30, show: hours },
  { key: "max_travel_minutes", label: "Train travel a day, at most", step: 30, show: hours },
  { key: "max_markets_per_day", label: "Markets a day, up to", step: 1, show: String },
];

type Props = {
  ranges: Record<string, SettingRange>;
  changed: Partial<Settings>;
  // Given how to change the latest settings (so quick clicks never overwrite each other).
  onChange: (update: (changed: Partial<Settings>) => Partial<Settings>) => void;
};

export default function PaceSettings({ ranges, changed, onChange }: Props) {
  const value = <K extends keyof Settings>(key: K) => (changed[key] ?? ranges[key].default) as Settings[K];

  // Change one setting, starting from the latest settings; keep only those that differ from their default.
  const update = <K extends keyof Settings>(key: K, next: (current: Settings[K]) => Settings[K]) =>
    onChange((latest) => {
      const value = next((latest[key] ?? ranges[key].default) as Settings[K]);
      const rest = { ...latest };
      delete rest[key];
      return value === ranges[key].default ? rest : { ...rest, [key]: value };
    });

  return (
    <div className="divide-y divide-snow/10 border border-snow/15 bg-night-deep/30 px-4">
        {STEPPERS.map(({ key, label, step, show }) => {
          const { low = -Infinity, high = Infinity } = ranges[key];
          const current = value(key);
          return (
            <div key={key} className="flex items-center justify-between py-2">
              <span className="text-snow">{label}</span>
              <div className="flex items-center gap-3">
                <StepButton label={`Less: ${label}`} disabled={current - step < low}
                            onClick={() => update(key, (v) => Math.max(low, v - step))}>−</StepButton>
                <span className="w-24 text-center tabular-nums text-gold" aria-live="polite">{show(current)}</span>
                <StepButton label={`More: ${label}`} disabled={current + step > high}
                            onClick={() => update(key, (v) => Math.min(high, v + step))}>+</StepButton>
              </div>
            </div>
          );
        })}
        <div className="flex items-center justify-between gap-4 py-2">
          <span>
            <span className="block text-snow">Day trips</span>
            <span className="text-xs text-frost">go somewhere and come back the same day</span>
          </span>
          <button type="button" role="switch" aria-checked={value("day_trips")} aria-label="Day trips"
                  onClick={() => update("day_trips", (on) => !on)}
                  className={`relative h-6 w-11 shrink-0 border transition duration-200 focus-visible:outline-2 focus-visible:outline-snow
                              ${value("day_trips") ? "border-gold bg-gold/30" : "border-snow/30 bg-night-deep/60"}`}>
            <span className={`absolute top-0.5 h-4 w-4 transition-all duration-200
                              ${value("day_trips") ? "left-6 bg-gold" : "left-0.5 bg-snow/60"}`} />
          </button>
        </div>
    </div>
  );
}

function StepButton({ label, disabled, onClick, children }: { label: string; disabled: boolean; onClick: () => void; children: string }) {
  return (
    <button type="button" aria-label={label} disabled={disabled} onClick={onClick}
            className="h-8 w-8 border border-snow/25 text-lg leading-none text-snow transition hover:border-gold hover:text-gold
                       disabled:cursor-default disabled:opacity-30 disabled:hover:border-snow/25 disabled:hover:text-snow
                       focus-visible:outline-2 focus-visible:outline-snow">
      {children}
    </button>
  );
}
