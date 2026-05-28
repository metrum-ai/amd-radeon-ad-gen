// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C, radius } from "../tokens";

export const fieldStyle = {
  width: "100%",
  background: C.elevated,
  border: `1.5px solid ${C.border}`,
  borderRadius: radius.sm,
  padding: "11px 14px",
  color: C.white,
  fontSize: 13,
  fontFamily: "'Inter', sans-serif",
  boxSizing: "border-box",
  lineHeight: 1.5,
  boxShadow: "none",
  outline: "none",
};

export const textareaStyle = {
  ...fieldStyle,
  padding: "14px 16px",
  resize: "vertical",
  minHeight: 84,
  lineHeight: 1.7,
};

export const brandPresets = [
  { name: "AMD", colors: [{ hex: "#ED1C24", label: "Primary" }, { hex: "#000000", label: "Secondary" }, { hex: "#FFFFFF", label: "Accent" }], fonts: ["Arial", "Inter"] },
];

export const defaultTones = ["Bold", "Technical", "Aspirational", "Playful", "Premium", "Minimal"];
export const colorLabels = ["Primary", "Secondary", "Accent", "Background", "Highlight", "Muted"];
export const fontOptions = [
  "Inter", "Roboto", "Open Sans", "Montserrat", "Lato",
  "Poppins", "Raleway", "Oswald", "Playfair Display", "Merriweather",
  "Source Sans Pro", "Nunito", "Ubuntu", "Rubik", "Work Sans",
  "DM Sans", "Outfit", "Space Grotesk", "Sora", "Manrope",
  "Helvetica Neue", "Arial", "Trade Gothic", "Futura", "Avenir",
  "Proxima Nova", "Gill Sans", "Franklin Gothic",
];
