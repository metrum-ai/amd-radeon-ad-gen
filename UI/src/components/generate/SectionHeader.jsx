// Created by Metrum AI for AMD

import { C, radius } from "../../tokens";
import { Box, T } from "../primitives";
import "../../css/generate/SectionHeader.css";

export default function SectionHeader({ title, sub, right, step }) {
  return (
    <Box className="section-header" style={{ borderBottom: `1px solid ${C.border}` }}>
      <Box className="section-header__left">
        {step && (
          <Box
            className="section-header__step"
            style={{ borderRadius: 8, background: C.elevated, border: `1px solid ${C.border}` }}
          >
            <T s={12} c={C.accent} w={700}>{step}</T>
          </Box>
        )}
        <Box className="section-header__text">
          <T s={12} c={C.text} w={700} className="section-header__title">{title}</T>
          {sub && <T s={10} c={C.dim} className="section-header__sub">{sub}</T>}
        </Box>
      </Box>
      {right}
    </Box>
  );
}
