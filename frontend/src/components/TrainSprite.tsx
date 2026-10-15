// The little train, the same everywhere (the planning scene and the holiday map): a red locomotive with
// gold trim pulling two green wagons, one carrying a red gift and one a green tree. It travels along
// a path, looping, each car following the one in front; with "reduce motion" it is hidden.

const CARS = ["engine", "gift", "tree"] as const;

function Car({ kind }: { kind: (typeof CARS)[number] }) {
  if (kind === "engine") {
    return (
      <g transform="translate(-16 -20)" className="fill-cranberry stroke-gold" strokeWidth={1.2}>
        <rect x="0" y="8" width="26" height="12" rx="2" />
        <rect x="18" y="0" width="11" height="13" rx="1.5" />
        <rect x="4" y="2" width="5" height="7" />
        <circle cx="7" cy="22" r="3.5" className="fill-night stroke-gold" strokeWidth="1.6" />
        <circle cx="20" cy="22" r="3.5" className="fill-night stroke-gold" strokeWidth="1.6" />
      </g>
    );
  }
  return (
    <g transform="translate(-12 -16)">
      <rect x="0" y="6" width="24" height="10" rx="1.5" className="fill-[#2f7d4f] stroke-gold" strokeWidth="1.2" />
      {kind === "gift"
        ? <><rect x="6" y="-4" width="12" height="10" className="fill-cranberry stroke-gold" strokeWidth="1.2" />
            <path d="M 12 -4 V 6" className="stroke-gold" strokeWidth="1.2" /></>
        : <path d="M 12 -10 L 19 6 L 5 6 Z" className="fill-[#2f7d4f] stroke-gold" strokeWidth="1.2" />}
      <circle cx="6" cy="18" r="3" className="fill-night stroke-gold" strokeWidth="1.5" />
      <circle cx="18" cy="18" r="3" className="fill-night stroke-gold" strokeWidth="1.5" />
    </g>
  );
}

type Props = {
  path: string; // the SVG path the train travels
  lap: number; // seconds to travel it once
  gap: number; // seconds between one car and the next
  size?: number; // 1 = the planning scene's size
};

export default function TrainSprite({ path, lap, gap, size = 1 }: Props) {
  return (
    <>
      {CARS.map((kind, i) => (
        <g key={kind} className="motion-reduce:hidden">
          <g transform={`scale(${size})`}><Car kind={kind} /></g>
          <animateMotion dur={`${lap}s`} repeatCount="indefinite" path={path} rotate="auto" begin={`-${lap - i * gap}s`} />
        </g>
      ))}
    </>
  );
}
