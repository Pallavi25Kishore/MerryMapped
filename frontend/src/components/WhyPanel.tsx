"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { longDate } from "@/components/DatePicker";
import { marketSources, type Sources } from "@/lib/api";

// "Why can I see this?": a panel sliding in from the right (full screen on phones) with the proof for
// every fact we show about a market: the fact in plain words, the quote from the page (and its
// English), which page it came from and when it was checked, or that it was entered by hand. Then
// what the market's site lets us do, from its approved review, each with its reason.

const DAY_NAMES: Record<string, string> = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" };
const WEEK = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

function days(list: string[]): string {
  if (list.length === 7) return "Daily";
  const sorted = WEEK.filter((d) => list.includes(d));
  return sorted.map((d) => DAY_NAMES[d]).join(", ");
}

function tagWords(tag: string): string {
  const words = tag.replace(/-/g, " ");
  return words[0].toUpperCase() + words.slice(1);
}

// One fact in plain words.
function say(kind: string, value: Record<string, unknown>): string {
  const text = (key: string) => String(value[key] ?? "");
  switch (kind) {
    case "opening_date": return `Opens ${longDate(text("date"))}`;
    case "closing_date": return `Last day ${longDate(text("date"))}`;
    case "hours": return `${days((value.days as string[]) ?? [])}, ${text("opens")} to ${text("closes")}`;
    case "closed_on": return `Closed on ${longDate(text("date"))}`;
    case "special_hours": return `${longDate(text("date"))}: ${text("opens")} to ${text("closes")}`;
    case "address": return `Where: ${text("text")}`;
    case "tag": return `Tagged: ${tagWords(text("tag"))}`;
    default: return text("text");
  }
}

const ALLOWED: Record<string, string> = {
  collect_facts: "Collect facts from it",
  keep_evidence: "Keep short quotes as proof",
  write_summary: "Write our own description",
  show_link: "Link to it",
};

function siteOf(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

type Props = { marketId: number; name: string; onClose: () => void };

export default function WhyPanel({ marketId, name, onClose }: Props) {
  const [sources, setSources] = useState<Sources | null | "error">(null);

  useEffect(() => {
    let current = true;
    marketSources(marketId).then((s) => current && setSources(s)).catch(() => current && setSources("error"));
    return () => { current = false; };
  }, [marketId]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Rendered on the page's body: a blurred parent (the description box) would otherwise trap it inside.
  return createPortal(
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={`Why can I see this? ${name}`}>
      <div className="absolute inset-0 bg-night-deep/60 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div className="slide-in panel absolute inset-y-0 right-0 w-full overflow-y-auto bg-night/90 p-6 text-left sm:w-[30rem] sm:p-8">
        <button type="button" onClick={onClose} aria-label="Close"
                className="absolute right-4 top-4 px-2 py-1 text-frost hover:text-gold">✕</button>
        <p className="text-xs uppercase tracking-[0.25em] text-gold">Why can I see this?</p>
        <h3 className="mt-1 font-display text-2xl font-semibold [font-variation-settings:'SOFT'_100]">{name}</h3>
        <p className="mt-3 text-sm text-snow/85">
          Everything we show comes from the market&apos;s own official website. Here&apos;s the proof for each fact.
        </p>

        {sources === null && <p className="mt-6 text-frost">Gathering the proof…</p>}
        {sources === "error" && <p className="mt-6 text-frost">The proof can&apos;t be loaded right now. Please try again.</p>}

        {sources && sources !== "error" && (
          <>
            <ul className="mt-6 space-y-4">
              {sources.facts.map((fact, n) => (
                <li key={n} className="border-l-2 border-gold/40 pl-4">
                  <p className="text-snow">{say(fact.kind, fact.value)}</p>
                  {fact.quote && <p className="mt-1 text-sm italic text-snow/80">“{fact.quote}”</p>}
                  {fact.english && fact.english !== fact.quote && (
                    <p className="text-sm italic text-frost">In English: “{fact.english}”</p>
                  )}
                  <p className="mt-1 text-xs text-frost">
                    {fact.status === "entered by hand" ? "Entered by hand from " : "From "}
                    <a href={fact.page} target="_blank" rel="noopener noreferrer"
                       className="text-gold underline underline-offset-2 hover:text-snow">{siteOf(fact.page)}</a>
                    {" "}· checked {longDate(fact.checked_on)}
                  </p>
                </li>
              ))}
            </ul>

            {Object.entries(sources.legal).map(([site, review]) => (
              <div key={site} className="mt-8 border-t border-snow/10 pt-5">
                <p className="text-xs uppercase tracking-[0.25em] text-gold">What {site} lets us do</p>
                {review ? (
                  <>
                    <ul className="mt-3 space-y-2">
                      {Object.entries(review.purposes).map(([purpose, answer]) => (
                        <li key={purpose}>
                          <details className="group">
                            <summary className="flex cursor-pointer list-none items-center gap-2 text-sm text-snow">
                              <span className={answer.answer === "allow" ? "text-gold" : "text-cranberry"}>
                                {answer.answer === "allow" ? "✓" : "✕"}
                              </span>
                              {ALLOWED[purpose] ?? purpose}
                              <span aria-hidden className="text-xs text-frost group-open:hidden">· why ▾</span>
                            </summary>
                            <p className="mt-1 pl-5 text-xs text-frost">{answer.because}</p>
                          </details>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-3 text-xs text-frost">
                      From the site&apos;s terms, reviewed {longDate(review.reviewed_on)}.
                    </p>
                  </>
                ) : (
                  <p className="mt-2 text-sm text-frost">No review is on file for this site.</p>
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </div>,
    document.body,
  );
}
