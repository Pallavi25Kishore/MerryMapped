import type { Train, Travel } from "@/lib/api";
import { hours, railway, stationName, toMinutes } from "@/lib/words";

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
      <ol className="mt-1.5 space-y-0.5 text-xs italic text-frost/90">
        {train.legs.map((leg, i) => {
          const next = train.legs[i + 1];
          const wait = next ? (toMinutes(next.depart) - toMinutes(leg.arrive) + 1440) % 1440 : 0;
          return (
            <li key={`${leg.from}-${leg.depart}`}>
              <span className="tabular-nums">{leg.depart}</span> {stationName(leg.from)}
              <span aria-hidden className="mx-1">→</span>
              <span className="tabular-nums">{leg.arrive}</span> {stationName(leg.to)}
              <span>
                {/* Worked out from the times, so trips saved before legs carried their length show it too. */}
                {" "}· {hours((toMinutes(leg.arrive) - toMinutes(leg.depart) + 1440) % 1440)}
                {railway(leg.railway) ? ` · ${railway(leg.railway)}` : ""}
              </span>
              {next && <span className="block pl-3 text-gold/70">change at {stationName(leg.to)} · {hours(wait)}</span>}
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
