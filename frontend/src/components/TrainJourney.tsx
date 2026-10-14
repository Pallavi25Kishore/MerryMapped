import type { Train, Travel } from "@/lib/api";
import { hours, railway, toMinutes } from "@/lib/words";

// One day's train journey: a summary (times, total length, direct or how many changes), then each
// leg with its stations, times, length and railway, and each change with its wait. A gentle note
// when the times are estimates.

function changes(train: Train): string {
  const n = train.legs.length - 1;
  return n === 0 ? "direct" : n === 1 ? "1 change" : `${n} changes`;
}

export default function TrainJourney({ travel }: { travel: Travel }) {
  const { train } = travel;
  if (!train) return null;
  const total = (toMinutes(train.arrive) - toMinutes(train.depart) + 1440) % 1440;
  const estimated = train.legs.some((leg) => leg.estimate);

  return (
    <div className="text-left">
      <p className="text-snow">
        <span className="text-gold">{train.depart}</span> {travel.from}
        <span aria-hidden className="mx-2 text-gold">→</span>
        <span className="text-gold">{train.arrive}</span> {travel.to}
        <span className="text-frost"> · {hours(total)} · {changes(train)}</span>
      </p>
      <ol className="mt-2 space-y-1 border-l border-gold/30 pl-4 text-sm text-snow/85">
        {train.legs.map((leg, i) => {
          const next = train.legs[i + 1];
          const wait = next ? (toMinutes(next.depart) - toMinutes(leg.arrive) + 1440) % 1440 : 0;
          return (
            <li key={`${leg.from}-${leg.depart}`}>
              <span className="tabular-nums">{leg.depart}</span> {leg.from}
              <span aria-hidden className="mx-1.5 text-frost">→</span>
              <span className="tabular-nums">{leg.arrive}</span> {leg.to}
              <span className="text-frost"> · {hours(leg.minutes)}{railway(leg.railway) ? ` · ${railway(leg.railway)}` : ""}</span>
              {next && <span className="mt-1 block italic text-frost">Change at {leg.to} · {hours(wait)}</span>}
            </li>
          );
        })}
      </ol>
      {estimated && (
        <p className="mt-2 text-xs italic text-frost">
          Times are based on a similar day&apos;s timetable; check before you book.
        </p>
      )}
    </div>
  );
}
