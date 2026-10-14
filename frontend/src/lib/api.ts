// The website's only way to talk to the backend. Every request goes to /api/... on this site
// (passed through to FastAPI, see next.config.ts) and carries the access code.

// ---------- What the addresses send and return (mirrors backend/app/main.py) ----------

export type SettingRange = { default: number | boolean; low?: number; high?: number };

export type Place = { city: string; country: string; lat: number; lon: number; market_city: boolean };

export type Options = {
  first_day: string; // "2026-12-15"
  last_day: string;
  cities: string[];
  places: Place[]; // every city, with its country and position, for the map
  settings: Record<string, SettingRange>; // times in minutes after midnight, durations in minutes
  train_data_credits: { credit: string; licence: string }[];
};

export type Settings = {
  earliest_train: number;
  min_market_minutes: number;
  max_travel_minutes: number;
  max_markets_per_day: number;
  day_trips: boolean;
};

// The form: every field optional; settings only those the traveller changed.
export type TripForm = {
  text?: string;
  first_day?: string;
  last_day?: string;
  start_city?: string;
  end_city?: string;
  settings?: Partial<Settings>;
};

export type TripRequest = {
  first_day: string;
  last_day: string;
  start_city: string | null;
  end_city: string | null;
  settings: Settings;
  wishes: string[];
  tags: string[];
};

export type Understood = { request: TripRequest | null; notes: string[]; not_covered: string[] };

export type Leg = {
  from: string;
  to: string;
  depart: string;
  arrive: string;
  minutes: number;
  railway: string | null; // which timetable it came from (see railway() in words.ts)
  estimate: boolean; // times borrowed from a similar weekday
};
export type Train = { depart: string; arrive: string; via: string | null; legs: Leg[] };
export type Travel = { from: string; to: string; train: Train | null };

export type Visit = {
  market_id: number;
  name: string;
  why: string;
  tiles: string[];
  description: string | null;
  dont_miss: string[];
  website: string | null;
};

export type ItineraryDay = {
  date: string;
  travel: Travel | null;
  travel_back: Travel | null;
  visits: Visit[];
  sleep_in: string;
  left_out: { market_id: number; name: string | null; reason: string; tip: string | null }[];
  free_day: { city: string; reason: "closed" | "rest" } | null; // a day without markets: where, and why
  problem: string | null;
  tip: string | null;
};

export type WishNote = {
  wish: string;
  verdict: "met" | "partly_met" | "not_met" | "no_information" | "not_covered";
  note: string;
  evidence: { market_id: number; text: string }[];
};

export type Itinerary = { days: ItineraryDay[]; warnings: string[]; wishes: WishNote[] };

export type Trip = { trip_id: string; created_at: string; request: TripRequest; itinerary: Itinerary };

export type TripSummary = {
  trip_id: string;
  created_at: string;
  first_day: string;
  last_day: string;
  cities: string[];
};

export type Receipt = {
  trip_id: string;
  planned_at: string;
  deleted_at: string;
  deleted: string;
  kept: string;
};

export type Answer = { answer: "allow" | "deny"; because: string };

export type Sources = {
  market_id: number;
  name: string;
  website: string;
  facts: {
    kind: string;
    value: Record<string, unknown>;
    page: string;
    quote: string | null;
    english: string | null;
    checked_on: string;
    status: string; // "checked" or "entered by hand"
  }[];
  legal: Record<string, null | {
    reviewed_on: string;
    terms_pages: string[];
    automated_access: Answer;
    purposes: Record<string, Answer>;
  }>;
};

// ---------- The access code, kept in this browser ----------

const CODE_KEY = "merrymapped-access-code";

export function getAccessCode(): string {
  try {
    return localStorage.getItem(CODE_KEY) ?? "";
  } catch {
    return ""; // storage blocked (private window): the code is asked for again
  }
}

export function setAccessCode(code: string): void {
  try {
    localStorage.setItem(CODE_KEY, code);
  } catch {
    // storage blocked: the code works until the page is closed
  }
}

// ---------- Calling the backend ----------

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
  }

  // A missing or wrong access code: the website asks for it again.
  get needsAccessCode(): boolean {
    return this.status === 401;
  }
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Access-Code": getAccessCode(), ...init.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, body?.detail ?? body);
  return body as T;
}

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

export const getOptions = () => call<Options>("/options");
export const understand = (form: TripForm) => call<Understood>("/understand", post(form));
export const plan = (request: TripRequest & { not_covered: string[] }) => call<Trip>("/plan", post(request));
export const myTrips = () => call<TripSummary[]>("/trips");
export const openTrip = (tripId: string) => call<Trip>(`/trips/${encodeURIComponent(tripId)}`);
export const deleteTrip = (tripId: string) =>
  call<Receipt>(`/trips/${encodeURIComponent(tripId)}`, { method: "DELETE" });
export const marketSources = (marketId: number) => call<Sources>(`/markets/${marketId}/sources`);
