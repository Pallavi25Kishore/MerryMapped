// A simple title screen for now, to see the look; the trip form comes here later.
export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-4 pb-[20vh] text-center">
      <p className="text-sm uppercase tracking-[0.3em] text-gold">Germany · Belgium · France</p>
      <h1 className="font-display text-5xl font-semibold sm:text-7xl [font-variation-settings:'SOFT'_100]">
        Merry<span className="text-gold">Mapped</span>
      </h1>
      <p className="max-w-md text-lg text-snow/90">
        Your Christmas markets trip, planned reliably around accurate opening hours and train schedules.
      </p>
    </main>
  );
}
