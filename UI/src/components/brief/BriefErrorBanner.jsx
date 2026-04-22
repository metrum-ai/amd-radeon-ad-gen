// Created by Metrum AI for AMD

import { C, radius } from "../../tokens";
import { Box, T } from "../primitives";
import "../../css/brief/BriefErrorBanner.css";

export default function BriefErrorBanner({ message }) {
  if (!message) return null;
  return (
    <Box className="brief-error-banner" style={{ padding: "12px 16px", borderRadius: radius.sm, background: `${C.red}15`, border: `1px solid ${C.red}40` }}>
      <T s={12} c={C.red} w={500}>{message}</T>
    </Box>
  );
}
