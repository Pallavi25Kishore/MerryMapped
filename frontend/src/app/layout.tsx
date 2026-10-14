import type { Metadata } from "next";
import { Fraunces, Nunito } from "next/font/google";
import Footer from "@/components/Footer";
import NightSky from "@/components/NightSky";
import "./globals.css";

// Titles: a warm, soft serif, like a Christmas card.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["SOFT", "opsz"],
});

// Everything else: friendly and easy to read.
const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MerryMapped",
  description: "Plan a Christmas-markets trip by train through Germany, Belgium and France.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${fraunces.variable} ${nunito.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <div aria-hidden className="winter-night fixed inset-0 z-0" />
        <NightSky />
        <div className="relative z-10 flex flex-1 flex-col">{children}</div>
        <Footer />
      </body>
    </html>
  );
}
