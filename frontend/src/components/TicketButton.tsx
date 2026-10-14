import type { ButtonHTMLAttributes } from "react";

// Every button on the site: a simple rectangle with a thin outline, a dark fill and spaced capitals.
// "main" is the one action that moves you forward on a screen; "quiet" is for the others (Back,
// Edit, Cancel). Same shape everywhere, so people learn it at a glance.

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { kind?: "main" | "quiet" };

const LOOKS = {
  main: "border-gold/80 text-gold hover:border-gold hover:shadow-[0_0_18px_rgb(244_195_90/0.5)]",
  quiet: "border-snow/40 text-snow/90 hover:border-snow/70 hover:shadow-[0_0_12px_rgb(247_244_236/0.3)]",
};

export default function TicketButton({ kind = "main", className = "", children, type = "button", ...rest }: Props) {
  return (
    <button type={type} {...rest}
            className={`border-[1.5px] bg-night px-9 py-3.5 text-base font-semibold uppercase tracking-[0.22em]
                        transition duration-300 hover:bg-night-deep disabled:opacity-50
                        focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-snow
                        ${LOOKS[kind]} ${className}`}>
      {children}
    </button>
  );
}
