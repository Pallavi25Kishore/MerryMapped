"use client";

import { useEffect, useRef } from "react";
import { type Box, MAGIC_EVENT } from "@/lib/magic";

// Fairy-light magic on top of the whole page (see castMagic), kept subtle: a few fine lights and small
// stars lift off the edges of a box, drift up a little way and fade. It only animates while there is
// magic to show; with "reduce motion" on, it shows nothing.

type Mote = { x: number; y: number; vx: number; vy: number; size: number; life: number; full: number;
              star: boolean; spin: number; phase: number };

const SPARKLES = 70; // lights in one scatter: fine and soft, so it stays elegant
const STARS = 0.15; // share of them that are small four-pointed stars
const BRIGHTNESS = 0.75; // the brightest any light gets

function glowSprite(): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const ctx = canvas.getContext("2d")!;
  const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, "rgba(255, 250, 235, 1)");
  gradient.addColorStop(0.15, "rgba(255, 220, 135, 0.95)");
  gradient.addColorStop(0.4, "rgba(244, 195, 90, 0.3)");
  gradient.addColorStop(1, "rgba(244, 195, 90, 0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 64, 64);
  return canvas;
}

// A four-pointed twinkle star with a soft glow.
function starSprite(): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const ctx = canvas.getContext("2d")!;
  ctx.shadowColor = "rgba(255, 214, 120, 0.9)";
  ctx.shadowBlur = 10;
  ctx.fillStyle = "rgba(255, 246, 220, 1)";
  ctx.beginPath();
  ctx.moveTo(32, 4);
  ctx.quadraticCurveTo(35, 29, 60, 32);
  ctx.quadraticCurveTo(35, 35, 32, 60);
  ctx.quadraticCurveTo(29, 35, 4, 32);
  ctx.quadraticCurveTo(29, 29, 32, 4);
  ctx.fill();
  return canvas;
}

// A random point on the outline of a box, and the direction pointing away from the box there.
function onEdge(box: Box): { x: number; y: number; out: [number, number] } {
  const run = Math.random() * 2 * (box.width + box.height);
  if (run < box.width) return { x: box.left + run, y: box.top, out: [0, -1] };
  if (run < box.width + box.height) return { x: box.left + box.width, y: box.top + run - box.width, out: [1, 0] };
  if (run < 2 * box.width + box.height) {
    return { x: box.left + run - box.width - box.height, y: box.top + box.height, out: [0, 1] };
  }
  return { x: box.left, y: box.top + run - 2 * box.width - box.height, out: [-1, 0] };
}

export default function Magic() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const glow = glowSprite();
    const star = starSprite();
    const motes: Mote[] = [];
    let frame = 0, last = 0, width = 0, height = 0;

    const resize = () => {
      const density = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * density;
      canvas.height = height * density;
      ctx.setTransform(density, 0, 0, density, 0, 0);
    };

    const tick = (now: number) => {
      const dt = last ? Math.min((now - last) / 1000, 0.05) : 0;
      last = now;
      for (let i = motes.length - 1; i >= 0; i--) {
        const m = motes[i];
        m.life -= dt;
        m.vx *= 1 - 2 * dt; // air slows them down
        m.vy *= 1 - 2 * dt;
        m.vy -= 18 * dt; // and they float gently upward
        m.x += m.vx * dt;
        m.y += m.vy * dt;
        m.phase += m.spin * dt;
        if (m.life <= 0) motes.splice(i, 1);
      }

      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";
      for (const m of motes) {
        const left = m.life / m.full;
        ctx.globalAlpha = BRIGHTNESS * Math.min(1, left * 1.5) * (0.85 + 0.15 * Math.sin(now / 400 + m.phase));
        const size = m.size * (0.6 + 0.4 * left);
        if (m.star) {
          ctx.save();
          ctx.translate(m.x, m.y);
          ctx.rotate(m.phase);
          ctx.drawImage(star, -size * 1.4, -size * 1.4, size * 2.8, size * 2.8);
          ctx.restore();
        } else {
          ctx.drawImage(glow, m.x - size, m.y - size, size * 2, size * 2);
        }
      }
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;

      if (motes.length) {
        frame = requestAnimationFrame(tick);
      } else {
        frame = 0; // nothing left to show: rest until the next magic
        last = 0;
        ctx.clearRect(0, 0, width, height);
      }
    };

    const onMagic = (event: Event) => {
      const box = (event as CustomEvent<Box>).detail;
      for (let k = 0; k < SPARKLES; k++) {
        const { x, y, out } = onEdge(box);
        const speed = 40 + Math.random() * 90; // how far they travel out from the edge
        const star = Math.random() < STARS;
        const life = 1.1 + Math.random() * 0.8;
        motes.push({ x, y, vx: out[0] * speed + (Math.random() - 0.5) * 20, vy: out[1] * speed - 15,
                     size: star ? 3 + Math.random() * 2 : 1.5 + Math.random() * 2, life, full: life, star,
                     spin: (Math.random() - 0.5) * 3, phase: Math.random() * Math.PI * 2 });
      }
      if (!frame) frame = requestAnimationFrame(tick);
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener(MAGIC_EVENT, onMagic);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener(MAGIC_EVENT, onMagic);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden className="pointer-events-none fixed inset-0 z-30 h-full w-full" />;
}
