"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";
import SoundButton from "@/components/SoundButton";

// Clicking Home while already on the home page (for example with the planner open) asks the home
// page to return to its welcome view.
export const HOME_EVENT = "merrymapped:home";

// The header on every page, floating on the night sky: the pages and the sound bell, on the right.

const PAGES = [
  { href: "/", label: "Home" },
  { href: "/about", label: "About us" },
  { href: "/trips", label: "Your trips" },
];

export default function Header() {
  return (
    <header className="relative z-20 flex items-center justify-end px-5 py-4 sm:px-10 sm:py-6">
      <nav className="flex items-center gap-6 sm:gap-9">
        {/* Which page you're on is filled in a moment later; the links show straight away. */}
        <Suspense fallback={<Links pathname={null} />}>
          <CurrentLinks />
        </Suspense>
        <SoundButton />
      </nav>
    </header>
  );
}

function CurrentLinks() {
  return <Links pathname={usePathname()} />;
}

// The links, with the page you're on lit in gold (none while that is not known yet).
function Links({ pathname }: { pathname: string | null }) {
  return (
    <>
      {PAGES.map(({ href, label }) => {
        const here = pathname === href || (href !== "/" && !!pathname?.startsWith(`${href}/`));
        return (
          <Link key={href} href={href} aria-current={here ? "page" : undefined}
                onClick={() => href === "/" && pathname === "/" && window.dispatchEvent(new Event(HOME_EVENT))}
                className={`group relative py-1 text-sm tracking-[0.12em] uppercase transition duration-300
                            hover:text-gold hover:[text-shadow:0_0_12px_rgb(244_195_90/0.7)]
                            ${here ? "text-gold" : "text-snow/85"}`}>
            {label}
            {/* A thin gold line that draws in under the word on hover, and stays on the page you are on. */}
            <span aria-hidden className={`absolute inset-x-0 -bottom-0.5 h-px origin-left bg-gold transition-transform
                                          duration-300 group-hover:scale-x-100 ${here ? "scale-x-100" : "scale-x-0"}`} />
          </Link>
        );
      })}
    </>
  );
}
