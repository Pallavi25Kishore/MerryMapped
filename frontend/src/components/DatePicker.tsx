"use client";

// When: a small December calendar (Monday to Sunday) showing only the trip season. Tap the first
// day, then the last; the days between light up. The first and last day are shown above it.

type Props = {
  firstAllowed: string; // "2026-12-15"
  lastAllowed: string; // "2026-12-31"
  firstDay?: string;
  lastDay?: string;
  onChange: (firstDay: string | undefined, lastDay: string | undefined) => void;
};

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function iso(day: Date): string {
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}

function fromIso(text: string): Date {
  const [year, month, day] = text.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function longDate(text: string): string {
  return fromIso(text).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

// The calendar's days: whole weeks, Monday to Sunday, around the allowed dates.
function calendarDays(firstAllowed: string, lastAllowed: string): Date[] {
  const start = fromIso(firstAllowed);
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7)); // back to Monday
  const end = fromIso(lastAllowed);
  end.setDate(end.getDate() + (6 - ((end.getDay() + 6) % 7))); // on to Sunday
  const days = [];
  for (const day = new Date(start); day <= end; day.setDate(day.getDate() + 1)) days.push(new Date(day));
  return days;
}

export default function DatePicker({ firstAllowed, lastAllowed, firstDay, lastDay, onChange }: Props) {
  const pick = (day: string) => {
    if (!firstDay || lastDay) onChange(day, undefined); // start a new choice
    else if (day < firstDay) onChange(day, undefined); // earlier than the first day: start again from it
    else onChange(firstDay, day);
  };
  const count = firstDay && lastDay ? (fromIso(lastDay).getTime() - fromIso(firstDay).getTime()) / 86_400_000 + 1 : 0;

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 text-left">
        {[["First day", firstDay], ["Last day", lastDay]].map(([label, value]) => (
          <div key={label} className="border border-snow/20 bg-night-deep/40 px-4 py-2.5">
            <div className="text-xs uppercase tracking-[0.2em] text-frost">{label}</div>
            <div className={value ? "text-snow" : "text-snow/40"}>{value ? longDate(value) : "Choose below"}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-7 gap-1.5" role="group" aria-label="December 2026">
        {WEEKDAYS.map((weekday) => (
          <div key={weekday} className="pb-1 text-center text-xs uppercase tracking-wider text-frost">{weekday}</div>
        ))}
        {calendarDays(firstAllowed, lastAllowed).map((date) => {
          const day = iso(date);
          const allowed = day >= firstAllowed && day <= lastAllowed;
          const end = day === firstDay || day === lastDay;
          const between = !!firstDay && !!lastDay && day > firstDay && day < lastDay;
          return (
            <button key={day} type="button" disabled={!allowed} onClick={() => pick(day)}
                    aria-pressed={end || between} aria-label={longDate(day)}
                    className={`py-2 text-sm transition duration-200 disabled:cursor-default disabled:text-snow/20
                                focus-visible:outline-2 focus-visible:outline-snow
                                ${end ? "bg-gold font-semibold text-night shadow-[0_0_12px_rgb(244_195_90/0.5)]"
                                  : between ? "bg-[#1e5c68] text-snow"
                                  : allowed ? "border border-snow/15 text-snow hover:border-gold hover:text-gold" : ""}`}>
              {date.getDate()}
            </button>
          );
        })}
      </div>

      <p className="mt-3 h-5 text-sm text-frost" aria-live="polite">
        {count ? `${count} ${count === 1 ? "day" : "days"}` : firstDay ? "Now choose your last day" : ""}
      </p>
    </div>
  );
}
