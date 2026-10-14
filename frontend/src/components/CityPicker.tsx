"use client";

// Where: one row of city buttons for one choice (where the trip starts, or where it ends). "Anywhere"
// leaves it to the planner. The chosen one glows gold, like the chosen dates.

type Props = {
  label: string; // "Start in"
  cities: string[];
  value?: string; // undefined: Anywhere
  onChange: (city: string | undefined) => void;
};

export default function CityPicker({ label, cities, value, onChange }: Props) {
  const choices: [string, string | undefined][] = [["Anywhere", undefined], ...cities.map((c): [string, string] => [c, c])];
  return (
    <div role="group" aria-label={label}>
      <div className="mb-2 text-xs uppercase tracking-[0.2em] text-frost">{label}</div>
      <div className="flex flex-wrap gap-2">
        {choices.map(([name, city]) => {
          const chosen = value === city;
          return (
            <button key={name} type="button" aria-pressed={chosen} onClick={() => onChange(city)}
                    className={`px-3.5 py-2 text-sm transition duration-200 focus-visible:outline-2 focus-visible:outline-snow
                                ${chosen ? "bg-gold font-semibold text-night shadow-[0_0_12px_rgb(244_195_90/0.5)]"
                                         : "border border-snow/15 text-snow hover:border-gold hover:text-gold"}`}>
              {name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
