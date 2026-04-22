// Created by Metrum AI for AMD

export { frameworkColors as fwColors } from "./strategy";

export const fallbackGradients = [
  "linear-gradient(145deg, #1a1020 0%, #2d1525 35%, #1a1018 100%)",
  "linear-gradient(145deg, #101520 0%, #15202a 35%, #0e1520 100%)",
  "linear-gradient(145deg, #201015 0%, #2a1520 35%, #18080e 100%)",
];

export function titleCase(s) {
  if (!s) return s;
  return s.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ");
}

export function parseAdSize(size) {
  const m = String(size || "").match(/(\d+)\s*x\s*(\d+)/i);
  if (!m) return null;
  return { w: Number(m[1]), h: Number(m[2]) };
}

export function compositionPreviewScore(comp) {
  const parsed = parseAdSize(comp?.ad_size);
  if (!parsed) return 0;
  if (parsed.w === 1080 && parsed.h === 1350) return 1_000_000_000;
  return parsed.w * parsed.h;
}
