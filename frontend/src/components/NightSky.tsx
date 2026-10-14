"use client";

import { useEffect, useRef } from "react";

// The night sky behind every page: falling snow, twinkling gold fairy dust, and a trail of
// sparkles that follows the pointer. Drawn on one canvas; with "reduce motion" on, it stands still.

type Flake = { x: number; y: number; size: number; speed: number; sway: number; phase: number };
type Dust = { x: number; y: number; size: number; drift: number; rise: number; phase: number; twinkle: number };
type Spark = { x: number; y: number; vx: number; vy: number; size: number; life: number };

const FLAKES_PER_PIXEL = 1 / 14000; // about 150 on a large screen; the picture has snow of its own
const DUST_PER_PIXEL = 1 / 30000;
const SPARK_LIFE = 0.7; // seconds a pointer sparkle lasts
const SPARK_SPREAD = 16; // how fast sparkles drift away from the pointer (pixels a second)

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

export default function NightSky() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const snow = sprite("rgba(247, 244, 236, 1)", 0.35);
    const gold = sprite("rgba(244, 195, 90, 1)", 0.2);
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let width = 0, height = 0, flakes: Flake[] = [], dust: Dust[] = [];
    const sparks: Spark[] = [];

    const newFlake = (top: boolean): Flake => {
      const size = 1.5 + Math.random() ** 2 * 5; // mostly small, a few big ones close by
      return { x: Math.random() * width, y: top ? -10 : Math.random() * height, size,
               speed: 12 + size * 9, sway: 8 + Math.random() * 20, phase: Math.random() * Math.PI * 2 };
    };
    const newDust = (): Dust => ({
      x: Math.random() * width, y: Math.random() * height, size: 2 + Math.random() * 5,
      drift: (Math.random() - 0.5) * 8, rise: 3 + Math.random() * 8,
      phase: Math.random() * Math.PI * 2, twinkle: 1 + Math.random() * 2.5,
    });

    const resize = () => {
      const density = window.devicePixelRatio || 1; // screen pixels per CSS pixel
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * density;
      canvas.height = height * density;
      ctx.setTransform(density, 0, 0, density, 0, 0);
      flakes = Array.from({ length: Math.round(width * height * FLAKES_PER_PIXEL) }, () => newFlake(false));
      dust = Array.from({ length: Math.round(width * height * DUST_PER_PIXEL) }, newDust);
    };

    const draw = (time: number) => {
      ctx.clearRect(0, 0, width, height);
      for (const f of flakes) {
        const x = f.x + Math.sin(time * 0.6 + f.phase) * f.sway;
        ctx.globalAlpha = 0.35 + f.size / 12;
        ctx.drawImage(snow, x - f.size, f.y - f.size, f.size * 2, f.size * 2);
      }
      for (const d of dust) {
        ctx.globalAlpha = 0.25 + 0.75 * Math.max(0, Math.sin(time * d.twinkle + d.phase));
        ctx.drawImage(gold, d.x - d.size, d.y - d.size, d.size * 2, d.size * 2);
      }
      for (const s of sparks) {
        ctx.globalAlpha = s.life / SPARK_LIFE;
        const size = s.size * (0.5 + s.life / SPARK_LIFE);
        ctx.drawImage(gold, s.x - size, s.y - size, size * 2, size * 2);
      }
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
        if (d.y < -10) Object.assign(d, newDust(), { y: height + 10 });
      }
      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i];
        s.life -= dt;
        s.x += s.vx * dt;
        s.y += s.vy * dt;
        s.vy += 12 * dt; // dust slowly settles
        if (s.life <= 0) sparks.splice(i, 1);
      }
      draw(now / 1000);
      frame = requestAnimationFrame(tick);
    };

    const sprinkle = (event: PointerEvent) => {
      for (let i = 0; i < 2; i++) {
        sparks.push({ x: event.clientX, y: event.clientY, vx: (Math.random() - 0.5) * SPARK_SPREAD,
                      vy: (Math.random() - 0.5) * SPARK_SPREAD, size: 1.5 + Math.random() * 3, life: SPARK_LIFE });
      }
      if (sparks.length > 200) sparks.splice(0, sparks.length - 200);
    };

    resize();
    window.addEventListener("resize", resize);
    if (still) {
      draw(0); // reduce motion: one quiet, still picture
    } else {
      window.addEventListener("pointermove", sprinkle);
      frame = requestAnimationFrame(tick);
    }
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", sprinkle);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden className="pointer-events-none fixed inset-0 z-0 h-full w-full" />;
}
