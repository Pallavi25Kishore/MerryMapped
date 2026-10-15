import TripList from "@/components/TripList";

// Your trips, at /trips: every saved trip, newest first. The list loads in the browser (it needs the
// access code).
export default function TripsPage() {
  return (
    <main className="flex flex-1 flex-col items-center px-4 pb-12">
      <p className="mt-6 text-sm uppercase tracking-[0.3em] text-gold">✦ Your trips ✦</p>
      <h1 className="mb-10 mt-3 text-center font-display text-3xl font-semibold sm:text-5xl
                     [font-variation-settings:'SOFT'_100]">
        Every Christmas markets trip you&apos;ve planned
      </h1>
      <TripList />
    </main>
  );
}
