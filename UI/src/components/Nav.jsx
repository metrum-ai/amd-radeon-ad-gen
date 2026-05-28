// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C, gradient, radius } from "../tokens";
import { Box, T } from "./primitives";

const Nav = ({ screen, setScreen, sidebarWidth = 36, generateUnlocked = false }) => {
  const tabs = [["campaign", "Campaign"], ["generate", "Output"]];
  const idx = tabs.findIndex(t => t[0] === screen);

  return (
    <Box style={{
      background: C.surface,
      borderBottom: `1px solid ${C.border}`,
      position: "sticky", top: 0, zIndex: 50,
      flexShrink: 0,
    }}>
      <Box style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 18px", height: 48, position: "relative",
      }}>
        <Box style={{ display: "flex", alignItems: "center", gap: 13 }}>
          <img src="/assets/amd_logo.png" alt="AMD" style={{
            height: 24, objectFit: "contain",
            filter: "brightness(0) invert(1)",
          }} />
          <Box style={{ width: 1.5, height: 24, background: "rgba(255,255,255,0.6)", borderRadius: 1 }} />
          <T s={13} c={C.white} w={700} style={{ letterSpacing: "0.08em", textTransform: "uppercase" }}>Campaign Studio</T>
        </Box>

        <Box style={{
          position: "fixed",
          left: `calc((100% - ${sidebarWidth}px) / 2)`,
          transform: "translateX(-50%)",
          display: "flex", alignItems: "center",
          background: C.elevated,
          border: `1px solid ${C.border}`,
          borderRadius: radius.sm,
          overflow: "hidden",
          zIndex: 51,
          transition: "left 0.3s ease",
        }}>
          {tabs.map(([k, label], i) => {
            const active = k === screen;
            const done = i < idx;
            const locked = k === "generate" && !generateUnlocked;
            return (
              <Box key={k} onClick={() => { if (!locked) setScreen(k); }} style={{
                padding: "6px 0", cursor: locked ? "not-allowed" : "pointer",
                background: active ? gradient.amd : "transparent",
                opacity: locked ? 0.4 : 1,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                width: 110,
                transition: "all 0.2s ease",
                borderRight: i < tabs.length - 1 ? `1px solid ${C.border}` : "none",
              }}>
                {locked && (
                  <T s={10} c={C.dim} style={{ lineHeight: 1 }}>{"\uD83D\uDD12"}</T>
                )}
                {!locked && done && (
                  <Box style={{
                    width: 14, height: 14, borderRadius: radius.sm, fontSize: 8, fontWeight: 700,
                    color: "#fff", background: C.teal,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>{"\u2713"}</Box>
                )}
                <T s={12} c={active ? "#fff" : C.muted} w={active ? 600 : 500} style={{ letterSpacing: "0.02em" }}>{label}</T>
              </Box>
            );
          })}
        </Box>

        <Box style={{ width: 30 }} />
      </Box>
    </Box>
  );
};

export default Nav;
