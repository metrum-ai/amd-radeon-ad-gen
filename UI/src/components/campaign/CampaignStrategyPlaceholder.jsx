// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C, gradient, radius } from "../../tokens";
import { Box, T } from "../primitives";
import "../../css/campaign/CampaignStrategyPlaceholder.css";

export default function CampaignStrategyPlaceholder() {
  return (
    <Box className="campaign-strategy-placeholder">
      <T s={24} w={700} c={C.white} className="campaign-strategy-placeholder__title">Strategy Directive</T>
      <T s={14} c={C.muted} className="campaign-strategy-placeholder__subtitle">
        Complete the campaign brief on the left and click
        <span style={{ color: C.accent, fontWeight: 600 }}> Generate Strategy </span>
        to receive AI-powered audience targeting, copy variants, scene prompts, and creative direction.
      </T>

      <Box className="campaign-strategy-placeholder__steps">
        {[
          { n: "1", label: "Fill Brief", active: true },
          { n: "2", label: "Generate" },
          { n: "3", label: "Review & Approve" },
        ].map((step, i) => (
          <Box key={i} className="campaign-strategy-placeholder__stepCell">
            <Box className="campaign-strategy-placeholder__step">
              <Box style={{ width: 36, height: 36, borderRadius: 10, background: step.active ? gradient.amd : C.elevated, border: `1px solid ${step.active ? "transparent" : C.border}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <T s={13} w={700} c={step.active ? "#fff" : C.muted}>{step.n}</T>
              </Box>
              <T s={11} c={step.active ? C.accent : C.text} w={step.active ? 600 : 400}>{step.label}</T>
            </Box>
            {i < 2 && <T s={14} c={C.muted} style={{ marginTop: 10 }}>{"›"}</T>}
          </Box>
        ))}
      </Box>

      <Box className="campaign-strategy-placeholder__ghost">
        <Box className="campaign-strategy-placeholder__ghostGrid">
          {[0, 1, 2, 3].map((i) => (
            <Box key={i} style={{ background: C.elevated, borderRadius: radius.md, padding: 14, animation: `fadeIn 0.5s ease ${i * 0.1}s both` }}>
              <Box style={{ width: "55%", height: 6, background: C.border, borderRadius: 3, marginBottom: 8 }} />
              <Box style={{ width: "35%", height: 18, background: C.border, borderRadius: 4, marginBottom: 6 }} />
              <Box style={{ width: "75%", height: 5, background: C.border, borderRadius: 3 }} />
            </Box>
          ))}
        </Box>
        <Box className="campaign-strategy-placeholder__ghostPills">
          {[45, 60, 40, 50, 35, 45].map((w, i) => (
            <Box key={i} style={{ width: w, height: 24, background: C.elevated, borderRadius: 4 }} />
          ))}
        </Box>
        <Box style={{ background: C.elevated, borderRadius: radius.md, padding: 16 }}>
          <Box style={{ width: "50%", height: 6, background: C.border, borderRadius: 3, marginBottom: 12 }} />
          <Box style={{ width: "100%", height: 4, background: C.border, borderRadius: 2, marginBottom: 6 }} />
          <Box style={{ width: "88%", height: 4, background: C.border, borderRadius: 2, marginBottom: 6 }} />
          <Box style={{ width: "65%", height: 4, background: C.border, borderRadius: 2 }} />
        </Box>
      </Box>
    </Box>
  );
}
