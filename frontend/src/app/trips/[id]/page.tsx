import { Suspense } from "react";
import TripView from "@/components/TripView";

// A saved trip's own page, at /trips/<id>. The trip loads in the browser (it needs the access code).
export default function TripPage({ params }: PageProps<"/trips/[id]">) {
  return (
    <main className="flex flex-1 flex-col items-center pb-12">
      <Suspense fallback={<p className="text-frost">Opening your trip…</p>}>
        <TripView params={params} />
      </Suspense>
    </main>
  );
}
