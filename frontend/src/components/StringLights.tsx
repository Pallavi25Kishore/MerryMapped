// A garland of fairy lights across the top of the page: a softly swagging wire with glowing bulbs in
// gold, red, snow-white and green, each twinkling at its own pace (steady with "reduce motion").

const SWAGS = 6; // dips in the wire across the width
const BULBS_PER_SWAG = 7;
const COLOURS = ["#f4c35a", "#e5525e", "#f7f4ec", "#5fcf8f"]; // gold, red, snow, green

export default function StringLights() {
  const width = 1200, dip = 26, top = 6;
  const swag = width / SWAGS;
  const wire = Array.from({ length: SWAGS }, (_, i) =>
    `${i === 0 ? `M 0 ${top}` : ""} Q ${swag * i + swag / 2} ${top + dip * 2} ${swag * (i + 1)} ${top}`).join(" ");

  const bulbs = [];
  for (let i = 0; i < SWAGS; i++) {
    for (let b = 1; b < BULBS_PER_SWAG; b++) {
      const t = b / BULBS_PER_SWAG; // along this swag
      const x = swag * i + swag * t;
      const y = (1 - t) ** 2 * top + 2 * (1 - t) * t * (top + dip * 2) + t ** 2 * top; // on the curve
      bulbs.push({ x, y, colour: COLOURS[(i * BULBS_PER_SWAG + b) % COLOURS.length], delay: ((i * 7 + b * 3) % 10) / 4 });
    }
  }

  return (
    <svg viewBox={`0 0 ${width} 70`} preserveAspectRatio="none" className="pointer-events-none h-12 w-full sm:h-16" aria-hidden>
      <path d={wire} fill="none" stroke="#1d3a2e" strokeWidth={1.5} />
      {bulbs.map(({ x, y, colour, delay }, n) => (
        <g key={n} className="twinkle" style={{ animationDelay: `${delay}s` }}>
          <ellipse cx={x} cy={y + 9} rx={9} ry={11} fill={colour} opacity={0.18} />
          <rect x={x - 1.5} y={y} width={3} height={3} fill="#1d3a2e" />
          <ellipse cx={x} cy={y + 8} rx={3} ry={4.5} fill={colour} />
        </g>
      ))}
    </svg>
  );
}
