// Saying things in plain words, the same way everywhere on the site.

export const NUMBER_WORDS = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
                             "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen"];

// "Ten", or the digits beyond the words we have.
export function numberWord(n: number): string {
  return NUMBER_WORDS[n - 1] ?? String(n);
}

// Minutes after midnight as a clock time: 495 → "08:15".
export function hhmm(minutes: number): string {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

// A length of time: 90 → "1 h 30 min", 120 → "2 h", 45 → "45 min".
export function hours(minutes: number): string {
  const h = Math.floor(minutes / 60), m = minutes % 60;
  return h && m ? `${h} h ${m} min` : h ? `${h} h` : `${m} min`;
}

// "08:15" → minutes after midnight.
export function toMinutes(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}

// Which railway runs a train, from the timetable it came from. Both German timetables are named
// "Deutsche Bahn": the regional file also lists some fast cross-border trains, so its name would
// mislead about the train's type (which comes with the train numbers in the 1 December rebuild).
const RAILWAYS: Record<string, string> = {
  eurostar: "Eurostar",
  sncf: "SNCF",
  sncb: "SNCB, Belgian Railways",
  germany_long_distance: "Deutsche Bahn",
  germany_regional: "Deutsche Bahn",
};

export function railway(feed: string | null): string | null {
  return feed ? RAILWAYS[feed] ?? null : null;
}
