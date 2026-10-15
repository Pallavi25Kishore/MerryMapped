import type { WishNote } from "@/lib/api";

// "Wishes granted": the wishes the traveller typed (in their own words) that the planned trip meets,
// fully or in part, each with a warm note on where it comes true. Only what was granted is shown;
// the section is left out when nothing was.

type Props = { wishes: WishNote[]; typed: string[] };

export default function WishesGranted({ wishes, typed }: Props) {
  const granted = wishes.filter((note) => typed.includes(note.wish) && (note.verdict === "met" || note.verdict === "partly_met"));
  if (granted.length === 0) return null;

  return (
    <section className="mx-auto mt-14 max-w-[1312px] px-4" aria-label="Wishes granted">
      <p className="text-center text-sm uppercase tracking-[0.3em] text-gold">✦ Wishes granted ✦</p>
      <ul className="mt-5 flex flex-wrap justify-center gap-4">
        {granted.map((note) => (
          <li key={note.wish} className="panel rise-in w-full max-w-sm p-5 text-left">
            <p className="font-display text-lg text-snow [font-variation-settings:'SOFT'_100]">“{note.wish}”</p>
            <p className="mt-2 text-sm text-snow/85">{note.note}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
