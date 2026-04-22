// Created by Metrum AI for AMD

import { forwardRef } from "react";
import { C, gradient, shadow, radius } from "../tokens";

export const Box = forwardRef(({ children, style, onClick, className, onMouseEnter, onMouseLeave }, ref) => (
  <div ref={ref} onClick={onClick} className={className} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave} style={{ boxSizing: "border-box", ...style }}>{children}</div>
));

export const T = ({ children, s = 14, c = C.white, w = 400, style, className }) => (
  <div className={className} style={{ fontSize: s, color: c, fontWeight: w, lineHeight: 1.55, letterSpacing: s >= 22 ? "-0.02em" : s >= 16 ? "-0.015em" : "0", ...style }}>{children}</div>
);

export const Label = ({ children, accent }) => (
  <Box style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
    <Box style={{
      width: 3, height: 16, borderRadius: 2,
      background: accent || gradient.amd,
    }} />
    <T s={12} c={C.text} w={700} style={{ textTransform: "uppercase", letterSpacing: "0.1em" }}>{children}</T>
  </Box>
);

export const Badge = ({ children, bg = C.accent, soft }) => (
  <span style={{
    fontSize: 10, fontWeight: 700, color: bg === C.accent ? "#fff" : bg,
    background: bg === C.accent ? gradient.amd : (soft || `${bg}12`),
    padding: "3px 10px", borderRadius: 12,
    letterSpacing: "0.06em", display: "inline-block",
    textTransform: "uppercase",
  }}>{children}</span>
);

export const IconBadge = ({ icon, bg }) => (
  <Box style={{
    width: 44, height: 44, borderRadius: radius.md,
    background: `${bg}10`, display: "flex", alignItems: "center", justifyContent: "center",
  }}>
    <T s={20}>{icon}</T>
  </Box>
);

export const Btn = ({ children, primary, sm, disabled, onClick, full, style }) => (
  <button type="button" disabled={disabled} onClick={onClick} style={{
    padding: sm ? "6px 14px" : "8px 24px", borderRadius: radius.sm,
    border: primary ? "none" : `1px solid ${C.border}`,
    background: disabled ? C.elevated : primary
      ? gradient.amd
      : C.hover,
    color: disabled ? C.muted : primary ? "#fff" : C.text,
    fontSize: sm ? 12 : 13, fontWeight: 600, width: full ? "100%" : "auto",
    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1,
    letterSpacing: "0.02em",
    transition: "all 0.2s ease",
    ...style,
  }}>{children}</button>
);

export const Card = ({ children, style, onClick, onMouseEnter, onMouseLeave, className }) => (
  <Box className={className} onClick={onClick} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave} style={{
    background: C.elevated,
    border: `1px solid ${C.border}`,
    borderRadius: radius.md,
    padding: 24,
    transition: "border-color 0.2s ease",
    ...style,
  }}>{children}</Box>
);

export const StatCard = ({ label, value, sub, icon, color }) => (
  <Card style={{ padding: 14, position: "relative", overflow: "hidden" }}>
    <Box style={{
      position: "absolute", top: 0, left: 0, right: 0, height: 2,
      background: color === C.accent ? gradient.amdH : color,
      borderRadius: `${radius.md}px ${radius.md}px 0 0`,
    }} />
    <Box style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
      <Box>
        <T s={12} c={C.muted} w={500} style={{ marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.1em" }}>{label}</T>
        <T s={28} w={700} c={C.white} style={{ marginBottom: 4, lineHeight: 1 }}>{value}</T>
        <T s={11} c={C.dim}>{sub}</T>
      </Box>
      <IconBadge icon={icon} bg={color || C.blue} />
    </Box>
  </Card>
);

export const ProgressBar = ({ value, max, color = C.accent }) => (
  <Box style={{ height: 4, background: C.border, borderRadius: 2, overflow: "hidden" }}>
    <Box style={{
      height: "100%",
      width: `${max > 0 ? (value / max) * 100 : 0}%`,
      background: color === C.accent ? gradient.amdH : color,
      borderRadius: 2,
      transition: "width 0.6s ease",
    }} />
  </Box>
);
