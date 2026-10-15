import Link from "next/link";

// About us, at /about: what MerryMapped is and why it can be trusted. Its two promises, where every
// market fact and every train comes from, how a trip is planned and checked, and what is kept.

const SECTIONS = [
  {
    title: "Why MerryMapped",
    text: [
      "The internet is full of Christmas market tips that are out of date, copied from other sites or simply made up. A blog says a market is open on the 24th, and it isn't. A trip built on that is a cold evening in an empty square.",
      "MerryMapped plans your trip only from information you can trust: each market's own official website, and the railways' real timetables.",
    ],
  },
  {
    title: "Our two promises",
    text: [
      "You never land at a closed market. Every plan is checked against each market's opening days and hours, and against real trains, before you see it.",
      "We never use information we aren't allowed to use. Before reading any website, we check its rules (its robots.txt and terms of use) and follow them.",
    ],
  },
  {
    title: "Where every market fact comes from",
    text: [
      "Opening dates, hours, closed days and the details that make each market special are read from the market's official website, and only where that website allows it.",
      "Every fact keeps a short quote from the page it came from and the date it was checked. Tap \"Why can I see this?\" on any market to see the proof, with an English translation.",
      "Descriptions are written in our own words, never copied.",
    ],
  },
  {
    title: "Real trains",
    text: [
      "Train times come from the open timetables that Eurostar, SNCF, Deutsche Bahn (through DELFI) and SNCB publish for everyone to use. Every journey is a real train, with its changes and waits.",
      "Before a railway publishes its December timetable, we use the same weekday's trains and say so clearly, so you know to check before you book.",
    ],
  },
  {
    title: "How your trip is planned",
    text: [
      "You tell us your dates, where to start and end, your pace and your wishes in your own words. An AI drafts a route, and then plain rules in code check every day: the market is open, there's time to enjoy it, a train fits your pace, and the route keeps moving onward.",
      "Anything that doesn't pass is fixed or left out, with a tip if a small change would fit it in. The AI never has the last word.",
    ],
  },
  {
    title: "Your trips",
    text: [
      "There are no accounts and we never ask who you are. Each trip keeps only what you asked for and its plan, until you delete it. Deleting removes it completely.",
    ],
  },
];

export default function AboutPage() {
  return (
    <main className="flex flex-1 flex-col items-center px-4 pb-12">
      <p className="mt-6 text-sm uppercase tracking-[0.3em] text-gold">✦ About us ✦</p>
      <h1 className="mt-3 max-w-3xl text-balance text-center font-display text-3xl font-semibold sm:text-5xl
                     [font-variation-settings:'SOFT'_100]">
        Christmas markets you can count on
      </h1>
      <p className="mt-4 max-w-2xl text-center text-lg text-snow/85">
        MerryMapped plans Christmas markets trips through Germany, Belgium and France by train, built
        only on official facts and real timetables.
      </p>

      <div className="mt-10 grid w-full max-w-5xl gap-5 md:grid-cols-2">
        {SECTIONS.map((section) => (
          <section key={section.title} className="panel p-6 text-left sm:p-7">
            <h2 className="font-display text-xl font-semibold text-gold [font-variation-settings:'SOFT'_100]">
              {section.title}
            </h2>
            <div className="mt-3 space-y-3 text-snow/90">
              {section.text.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            </div>
          </section>
        ))}
      </div>

      <Link href="/"
            className="mt-10 border-[1.5px] border-gold/80 bg-night px-9 py-3.5 text-base font-semibold uppercase
                       tracking-[0.22em] text-gold transition duration-300 hover:bg-night-deep
                       hover:shadow-[0_0_18px_rgb(244_195_90/0.5)]">
        Start planning
      </Link>
    </main>
  );
}
