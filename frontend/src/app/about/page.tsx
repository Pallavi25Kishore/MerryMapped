import Link from "next/link";
import StringLights from "@/components/StringLights";

// About us, at /about: for travellers, not coders. What MerryMapped is and why it can be trusted: its
// two promises, where every market fact and every train comes from, how a trip is planned and checked,
// and what is kept. Dressed for the season like the trip page: string lights across the top, fresh snow
// on each card, the cards rising in one after another, and a warm wish to close.

const SECTIONS = [
  {
    title: "Why MerryMapped",
    text: [
      "Christmas market tips online are often out of date, copied or simply wrong. A blog says a market is open on Christmas Eve, and it isn't: a cold evening in an empty square instead of mulled wine under the lights.",
      "MerryMapped plans only from what you can trust: each market's own official website, and the railways' own timetables.",
    ],
  },
  {
    title: "Our two promises",
    text: [
      "You never land at a closed market. Every day of your trip is checked against each market's official opening days and hours before you see it.",
      "We never use information we aren't allowed to use. Before reading any website, we check its rules and follow them.",
    ],
  },
  {
    title: "Every fact, with its proof",
    text: [
      "Dates, hours and the details that make each market special come from its official website. Descriptions are written in our own words.",
      "Tap \"Why can I see this?\" on any market to see where each fact came from and when we checked it, with a short quote and an English translation wherever the website allows.",
    ],
  },
  {
    title: "Trains you can actually take",
    text: [
      "Routes are built from the railways' own timetables (Eurostar, SNCF, Deutsche Bahn and SNCB), with every change and wait, so your evenings are spent at the markets, not on the platform.",
      "Until a railway publishes its December times, we use the same weekday's trains and mark them clearly, so you know to check before you book.",
    ],
  },
  {
    title: "How your trip is planned",
    text: [
      "Tell us your dates, your pace and your wishes in your own words, like \"somewhere medieval, with good mulled wine\". AI drafts the route, then strict rules check every day: the market is open, there's time to enjoy it, and a train fits your pace.",
      "Anything that doesn't fit is fixed or left out. The AI never has the last word.",
    ],
  },
  {
    title: "Your trips",
    text: [
      "No accounts, and we never ask who you are. Each trip is saved for you until you delete it, and deleting removes it completely.",
    ],
  },
];

export default function AboutPage() {
  return (
    <main className="flex flex-1 flex-col items-center px-4 pb-12">
      <StringLights />
      <p className="mt-6 text-sm uppercase tracking-[0.3em] text-gold">✦ About us ✦</p>
      <h1 className="mt-3 max-w-3xl text-balance text-center font-display text-3xl font-semibold sm:text-5xl
                     [font-variation-settings:'SOFT'_100]">
        Christmas markets you can count on
      </h1>
      <p className="mt-4 max-w-2xl text-center text-lg text-snow/85">
        MerryMapped plans Christmas markets trips through Germany, Belgium and France by train, built
        only on official market facts and the railways&apos; own timetables.
      </p>

      <div className="mt-10 grid w-full max-w-5xl gap-5 md:grid-cols-2">
        {SECTIONS.map((section, n) => (
          <section key={section.title} style={{ animationDelay: `${n * 90}ms` }}
                   className="panel snow-cap rise-in relative p-6 text-left sm:p-7">
            <h2 className="font-display text-xl font-semibold text-gold [font-variation-settings:'SOFT'_100]">
              <span aria-hidden className="mr-2 text-base">✦</span>{section.title}
            </h2>
            <div className="mt-3 space-y-3 text-snow/90">
              {section.text.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            </div>
          </section>
        ))}
      </div>

      <p className="mt-12 font-display text-xl italic text-gold drop-shadow-[0_1px_8px_rgb(7_28_35/0.9)] [font-variation-settings:'SOFT'_100]">
        Wishing you a merry, well-mapped December.
      </p>

      <Link href="/"
            className="mt-6 border-[1.5px] border-gold/80 bg-night px-9 py-3.5 text-base font-semibold uppercase
                       tracking-[0.22em] text-gold transition duration-300 hover:bg-night-deep
                       hover:shadow-[0_0_18px_rgb(244_195_90/0.5)]">
        Start planning
      </Link>
    </main>
  );
}
