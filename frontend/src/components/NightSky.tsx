"use client";

import { useEffect, useRef } from "react";

// The night sky behind every page: falling snow and twinkling gold fairy lights. Drawn on one canvas;
// with "reduce motion" on, it stands still. (The pointer trail is drawn on top, in Magic.)

type Flake = { x: number; y: number; size: number; speed: number; sway: number; phase: number };
type Dust = { x: number; y: number; size: number; drift: number; rise: number; phase: number; twinkle: number };

const FLAKES_PER_PIXEL = 1 / 14000; // about 150 on a large screen; the picture has snow of its own
const DUST_PER_PIXEL = 1 / 68000; // fairy lights: about 30 on a large screen
const FAIRY_SIZE = 9; // average radius of a fairy light's glow, in pixels
const FAIRY_BRIGHTNESS = 0.8; // the brightest a fairy light gets, at the top of its twinkle

// The background picture's size, and the top edge of its snowy hills (x, y in its pixels,
// measured from public/backgrounds/winter-night.jpg): fairy lights stay in the sky above it.
const PICTURE = { width: 1920, height: 1279 };
const HILLS = [[0, 853], [160, 858], [320, 881], [480, 891], [640, 904], [800, 925], [960, 955],
               [1120, 990], [1280, 1033], [1440, 1079], [1600, 1065], [1760, 1056], [1920, 1045]];
const ABOVE_HILLS = 30; // how far above the hills fairy lights stay, in pixels

// The y (in picture pixels) where the hills begin at picture x, between the measured points.
function hillTop(x: number): number {
  const i = Math.min(Math.max(Math.floor(x / 160), 0), HILLS.length - 2);
  const [x0, y0] = HILLS[i], [x1, y1] = HILLS[i + 1];
  return y0 + ((Math.min(Math.max(x, x0), x1) - x0) / (x1 - x0)) * (y1 - y0);
}

// A soft round dot, drawn once and reused, so each frame only copies small pictures.
function sprite(colour: string, glow: number): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const ctx = canvas.getContext("2d")!;
  const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, colour);
  gradient.addColorStop(glow, colour.replace(/[\d.]+\)$/, "0.35)"));
  gradient.addColorStop(1, colour.replace(/[\d.]+\)$/, "0)"));
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 64, 64);
  return canvas;
}

// A fairy light: a small bright core inside a wide, soft golden halo.
function glow(): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const ctx = canvas.getContext("2d")!;
  const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, "rgba(255, 248, 225, 1)"); // a white-hot centre
  gradient.addColorStop(0.12, "rgba(255, 214, 120, 0.95)");
  gradient.addColorStop(0.35, "rgba(244, 195, 90, 0.35)");
  gradient.addColorStop(1, "rgba(244, 195, 90, 0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 64, 64);
  return canvas;
}

export default function NightSky() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const snow = sprite("rgba(247, 244, 236, 1)", 0.35);
    const fairy = glow();
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let width = 0, height = 0, flakes: Flake[] = [], dust: Dust[] = [];
    // Where the picture lands on screen: it covers the window, anchored to the bottom centre.
    let scale = 1, left = 0, top = 0;
    // The lowest a fairy light may be at screen x: just above the hills (or the window's bottom).
    const skyBottom = (x: number) =>
      Math.min(top + hillTop((x - left) / scale) * scale, height) - ABOVE_HILLS;

    const newFlake = (top: boolean): Flake => {
      const size = 1.5 + Math.random() ** 2 * 5; // mostly small, a few big ones close by
      return { x: Math.random() * width, y: top ? -10 : Math.random() * height, size,
               speed: 12 + size * 9, sway: 8 + Math.random() * 20, phase: Math.random() * Math.PI * 2 };
    };
    const newDust = (fromHills: boolean): Dust => {
      const x = Math.random() * width, bottom = skyBottom(x);
      return { x, y: fromHills ? bottom : Math.random() * bottom, size: FAIRY_SIZE * (0.6 + Math.random() * 0.8),
               drift: (Math.random() - 0.5) * 8, rise: 3 + Math.random() * 8,
               phase: Math.random() * Math.PI * 2, twinkle: 1 + Math.random() * 2.5 };
    };

    const resize = () => {
      const density = window.devicePixelRatio || 1; // screen pixels per CSS pixel
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * density;
      canvas.height = height * density;
      ctx.setTransform(density, 0, 0, density, 0, 0);
      scale = Math.max(width / PICTURE.width, height / PICTURE.height);
      left = (width - PICTURE.width * scale) / 2;
      top = height - PICTURE.height * scale;
      flakes = Array.from({ length: Math.round(width * height * FLAKES_PER_PIXEL) }, () => newFlake(false));
      dust = Array.from({ length: Math.round(width * height * DUST_PER_PIXEL) }, () => newDust(false));
    };

    const draw = (time: number) => {
      ctx.clearRect(0, 0, width, height);
      for (const f of flakes) {
        const x = f.x + Math.sin(time * 0.6 + f.phase) * f.sway;
        ctx.globalAlpha = 0.35 + f.size / 12;
        ctx.drawImage(snow, x - f.size, f.y - f.size, f.size * 2, f.size * 2);
      }
      ctx.globalCompositeOperation = "lighter"; // overlapping glows add up, like real light
      for (const d of dust) {
        ctx.globalAlpha = FAIRY_BRIGHTNESS * (0.3 + 0.7 * Math.max(0, Math.sin(time * d.twinkle + d.phase)));
        ctx.drawImage(fairy, d.x - d.size, d.y - d.size, d.size * 2, d.size * 2);
      }
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;
    };

    let last = performance.now(), frame = 0;
    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05); // seconds; capped after a pause
      last = now;
      for (const f of flakes) {
        f.y += f.speed * dt;
        if (f.y > height + 10) Object.assign(f, newFlake(true));
      }
      for (const d of dust) {
        d.y -= d.rise * dt;
        d.x += d.drift * dt;
        // Out of the top, or drifted over a hill: start again just above the hills.
        if (d.y < -10 || d.y > skyBottom(d.x)) Object.assign(d, newDust(true));
      }
      draw(now / 1000);
      frame = requestAnimationFrame(tick);
    };

    resize();
    window.addEventListener("resize", resize);
    if (still) {
      draw(0); // reduce motion: one quiet, still picture
    } else {
      frame = requestAnimationFrame(tick);
    }
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden className="pointer-events-none fixed inset-0 z-0 h-full w-full" />;
}
