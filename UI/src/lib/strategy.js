// Created by Metrum AI for AMD

import { C } from "../tokens";

export const TAB_TO_STAGE = {
  direction: "strategy",
  audience: "strategy",
  copy: "copy_gen",
  scenes: "scene_gen",
  audio: "audio_gen",
  tracks: null,
};

export const STRATEGY_TABS = [
  ["direction", "Direction"],
  ["audience", "Audiences"],
  ["copy", "Copy"],
  ["scenes", "Scenes"],
  ["audio", "Audio"],
  ["tracks", "Tracks"],
];

export const frameworkColors = { AIDA: C.accent, PAS: C.teal, BAB: C.orange };

/** Normalize track_recommendations entries from LLM / JSONB (boolean or occasional string). */
export function isTrackRecommended(entry) {
  if (!entry || typeof entry !== "object") return false;
  const r = entry.recommended;
  return r === true || r === "true";
}
