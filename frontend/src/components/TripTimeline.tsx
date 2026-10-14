import { longDate } from "@/components/DatePicker";
import TrainJourney from "@/components/TrainJourney";
import type { ItineraryDay } from "@/lib/api";

// The whole itinerary flowing down the page, like a train route: a gold line with a glowing bauble for
// each day, a dotted railway with a small train where the trip travels (its summary, and every leg
// and change in small type), each market as a row to click (the chosen one glows), and free days.

export type Chosen = { day: number; market: number } | null;

type Props = {
  days: ItineraryDay[];
  chosen: Chosen;
  onChoose: (day: number, market: number) => void;
};

const TrainIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden className="h-4 w-4 fill-gold">
    <rect x="3" y="9" width="13" height="7" rx="1" /><rect x="12" y="5" width="6" height="7" rx="1" />
    <rect x="5" y="6" width="3" height="4" /><circle cx="7" cy="18" r="2" /><circle cx="14" cy="18" r="2" />
  </svg>
);

const TreeIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden className="h-4 w-4 shrink-0 fill-gold">
    <path d="M12 2l5 7h-3l5 7H5l5-7H7zM11 16h2v4h-2z" />
  </svg>
);

export default function TripTimeline({ days, chosen, onChoose }: Props) {
  return (
    // On a frosted panel, so the small train details read well even over the bright snow.
    <ol className="panel relative px-4 py-6 text-left sm:px-6">
      {days.map((day, n) => (
        <li key={day.date} className="relative pb-2 pl-10">
          {/* The line down the page: solid within a day, a dotted railway on travel. */}
          {n < days.length - 1 && (
            <span aria-hidden className="absolute bottom-0 left-[11px] top-6 border-l-2 border-gold/35" />
          )}

          {day.travel && (
            <div className="relative mb-4">
              <span aria-hidden className="absolute -left-[40px] top-1 flex h-6 w-6 items-center justify-center
                                           rounded-full border border-gold/40 bg-night">
                <TrainIcon />
              </span>
              <div className="border-l-2 border-dashed border-gold/40 py-1 pl-4">
                <TrainJourney travel={day.travel} />
              </div>
            </div>
          )}

          {/* The day: a glowing bauble beside its heading. */}
          <p className="relative text-sm uppercase tracking-[0.25em] text-gold">
            <span aria-hidden className="absolute -left-[37px] top-0 h-[18px] w-[18px] rounded-full border-2 border-gold
                                         bg-[radial-gradient(circle_at_35%_35%,#fff3cf,#f4c35a_45%,#b8862e)]
                                         shadow-[0_0_12px_rgb(244_195_90/0.7)]" />
            Day {n + 1} · {longDate(day.date)} · <span className="text-snow">{day.sleep_in}</span>
          </p>

          <div className="mt-3 space-y-2 pb-6">
            {day.visits.map((visit, m) => {
              const here = chosen?.day === n && chosen.market === m;
              return (
                <button key={visit.market_id} type="button" onClick={() => onChoose(n, m)} aria-pressed={here}
                        className={`flex w-full items-center gap-3 border px-4 py-3 text-left transition duration-300
                                    focus-visible:outline-2 focus-visible:outline-snow
                                    ${here ? "border-gold bg-gold/15 shadow-[0_0_18px_rgb(244_195_90/0.25)]"
                                           : "border-snow/15 bg-night/50 hover:border-gold/60"}`}>
                  <TreeIcon />
                  <span className="flex-1">
                    <span className={here ? "text-gold" : "text-snow"}>{visit.name}</span>
                    {visit.tiles.length > 0 && (
                      <span className="mt-0.5 block text-xs text-frost">{visit.tiles.join(" · ")}</span>
                    )}
                  </span>
                  <span aria-hidden className={here ? "text-gold" : "text-frost"}>›</span>
                </button>
              );
            })}
            {day.free_day && day.travel && (
              <p className="px-1 text-snow/90">
                <span className="text-gold">✦ A travel day</span>
                <span className="italic">
                  {day.travel.train ? `: you arrive in ${day.travel.to} at ${day.travel.train.arrive}` : ` to ${day.travel.to}`},
                  {" "}after the markets have their best hours. Rest up for tomorrow.
                </span>
              </p>
            )}
            {day.free_day && !day.travel && (
              <p className="px-1 text-snow/90">
                <span className="text-gold">✦ Free day in {day.free_day.city}</span>
                <span className="italic"> · a lovely day for sightseeing.</span>
                {day.free_day.reason === "closed" && <span className="text-frost"> The Christmas market is closed today.</span>}
              </p>
            )}
            {day.left_out.map((out) => (
              <p key={out.market_id} className="px-1 text-sm text-frost">
                We couldn&apos;t fit {out.name ?? "a market"} in: {out.reason}
                {out.tip && <span className="text-gold"> Tip: {out.tip}</span>}
              </p>
            ))}
            {day.problem && (
              <p className="px-1 text-sm text-frost">
                This day doesn&apos;t quite work yet: {day.problem}
                {day.tip && <span className="text-gold"> Tip: {day.tip}</span>}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
