// Created by Metrum AI for AMD

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
  { name: "AMD", colors: [{ hex: "#ED1C24", label: "Primary" }, { hex: "#000000", label: "Secondary" }, { hex: "#FFFFFF", label: "Accent" }], fonts: ["Trade Gothic", "Helvetica Neue"] },
  { name: "Google", colors: [{ hex: "#4285F4", label: "Blue" }, { hex: "#DB4437", label: "Red" }, { hex: "#F4B400", label: "Yellow" }, { hex: "#0F9D58", label: "Green" }], fonts: ["Google Sans", "Roboto"] },
  { name: "Apple", colors: [{ hex: "#000000", label: "Primary" }, { hex: "#555555", label: "Secondary" }, { hex: "#FFFFFF", label: "Accent" }], fonts: ["SF Pro", "SF Mono"] },
  { name: "Meta", colors: [{ hex: "#0082FB", label: "Primary" }, { hex: "#1877F2", label: "Secondary" }, { hex: "#FFFFFF", label: "Accent" }], fonts: ["Optimistic Display", "Helvetica Neue"] },
  { name: "Microsoft", colors: [{ hex: "#F25022", label: "Red" }, { hex: "#7FBA00", label: "Green" }, { hex: "#00A4EF", label: "Blue" }, { hex: "#FFB900", label: "Yellow" }], fonts: ["Segoe UI", "Selawik"] },
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
