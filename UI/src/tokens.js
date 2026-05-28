// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

export const C = {
  bg: "#08080A",
  surface: "#111114",
  card: "#18181C",
  elevated: "#1E1E23",
  hover: "#26262C",
  border: "#2E2E35",
  borderLight: "#3A3A42",
  borderAccent: "rgba(237, 28, 36, 0.15)",

  accent: "#ED1C24",
  accentHover: "#c41019",
  accentSoft: "rgba(237, 28, 36, 0.08)",
  accentGlow: "rgba(237, 28, 36, 0.25)",
  orange: "#F26522",

  green: "#10b981",
  greenSoft: "rgba(16,185,129,0.10)",
  blue: "#6366f1",
  blueSoft: "rgba(99,102,241,0.10)",
  teal: "#007C97",
  tealSoft: "rgba(0,124,151,0.08)",
  yellow: "#eab308",
  red: "#ef4444",
  redSoft: "rgba(239,68,68,0.10)",

  white: "#F0F0F0",
  text: "#B0B2B5",
  muted: "#8A8D91",
  dim: "#70737A",

  glass: "rgba(17, 17, 20, 0.85)",
};

export const gradient = {
  amd: "linear-gradient(135deg, #ED1C24, #F26522)",
  amdH: "linear-gradient(90deg, #ED1C24, #F26522)",
  amdSubtle: "linear-gradient(135deg, rgba(237,28,36,0.08), rgba(242,101,34,0.02))",
};

export const shadow = {
  sm: "0 2px 12px rgba(0,0,0,0.4)",
  md: "0 8px 32px rgba(0,0,0,0.6)",
  lg: "0 8px 32px rgba(0,0,0,0.6)",
  xl: "0 20px 50px rgba(0,0,0,0.7)",
  glow: (color) => `0 0 32px ${color}15, 0 4px 20px ${color}20`,
  amdGlow: "0 0 32px rgba(237, 28, 36, 0.08)",
  up: "0 -2px 10px rgba(0,0,0,0.4)",
};

export const radius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 20,
};
