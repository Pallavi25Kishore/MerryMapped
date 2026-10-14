// Ask the Magic canvas (src/components/Magic.tsx) for a soft scatter of fairy-light sparkles lifting
// off the edges of something on screen, such as a button that has just flipped.

export const MAGIC_EVENT = "merrymapped:magic";

export type Box = { left: number; top: number; width: number; height: number };

export function castMagic(element: Element): void {
  const { left, top, width, height } = element.getBoundingClientRect();
  window.dispatchEvent(new CustomEvent<Box>(MAGIC_EVENT, { detail: { left, top, width, height } }));
}
