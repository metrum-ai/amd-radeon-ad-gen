// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C, gradient, radius } from "../../tokens";
import { Box, T } from "../primitives";
import { TAB_TO_STAGE, STRATEGY_TABS } from "../../lib/strategy";
import "../../css/strategy/StrategyTabs.css";

export default function StrategyTabs({ tab, setTab, stageStatus, isLoading, runningTab }) {
  return (
    <Box className="strategy-tabs" style={{ background: C.elevated, border: `1px solid ${C.border}`, borderRadius: radius.sm }}>
      {STRATEGY_TABS.map(([k, label]) => {
        const stage = TAB_TO_STAGE[k];
        const status = stage ? (stageStatus[stage] || "pending") : "idle";
        const running = isLoading && status === "running" && runningTab === k;
        const completed = status === "completed";
        const failed = status === "failed";
        return (
          <Box key={k} onClick={() => setTab(k)} className="strategy-tabs__tab" style={{ padding: "9px 14px", borderRadius: radius.sm, background: tab === k ? gradient.amd : "transparent" }}>
            {running && tab !== k && <Box style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg, transparent 0%, rgba(242,101,34,0.14) 20%, rgba(242,101,34,0.28) 50%, rgba(242,101,34,0.14) 80%, transparent 100%)", backgroundSize: "260% 100%", animation: "strategySweep 4.8s linear infinite" }} />}
            {completed && tab !== k && <Box style={{ position: "absolute", inset: 0, background: "rgba(242,101,34,0.08)" }} />}
            {failed && tab !== k && <Box style={{ position: "absolute", inset: 0, background: "rgba(239,68,68,0.10)" }} />}
            <T s={12} c={tab === k ? "#fff" : C.dim} w={tab === k || running ? 600 : 400} style={{ position: "relative", zIndex: 1, animation: running ? "pulseSoft 4.2s ease-in-out infinite" : "none" }}>{label}</T>
          </Box>
        );
      })}
    </Box>
  );
}
