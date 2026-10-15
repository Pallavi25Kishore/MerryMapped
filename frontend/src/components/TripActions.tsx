"use client";

import { useRouter } from "next/navigation";
import TicketButton from "@/components/TicketButton";
import { castMagic } from "@/lib/magic";
import { play } from "@/lib/sound";

// Under the trip's headline: every planned trip is saved straight away (kept until it is deleted from
// Your trips), so this says so, with the way to plan another trip.

export default function TripActions() {
  const router = useRouter();

  const another = (event: React.MouseEvent<HTMLButtonElement>) => {
    castMagic(event.currentTarget);
    play("magic");
    router.push("/");
  };

  return (
    <div className="mt-6 flex flex-col items-center gap-3">
      <p className="text-gold">✦ Your trip has been saved to Your trips</p>
      <TicketButton onClick={another}>Plan another trip</TicketButton>
    </div>
  );
}
