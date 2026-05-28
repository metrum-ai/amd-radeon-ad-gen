// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C } from "../../tokens";
import { Box, StatCard } from "../primitives";
import "../../css/strategy/StrategySummaryStats.css";

export default function StrategySummaryStats({ strategyReady, copyReady, scenesReady, audioReady, audiences, copyVariants, scenes, audioAds }) {
  return (
    <Box className="strategy-summary-stats">
      <StatCard label="Audience Segments" value={strategyReady ? String(audiences.length || "0") : "-"} sub="Demographics + platforms" icon={"👥"} color={C.blue} />
      <StatCard label="Copy Variants" value={copyReady ? String(copyVariants.length || "0") : "-"} sub="AIDA / PAS / BAB" icon={"✍️"} color={C.accent} />
      <StatCard label="Scene Prompts" value={scenesReady ? String(scenes.length || "0") : "-"} sub="Primary / Lifestyle / Mood" icon={"🖼"} color={C.teal} />
      <StatCard label="Audio Scripts" value={audioReady ? String(audioAds.length || "0") : "-"} sub="Host-read / Produced" icon={"🔊"} color={C.orange} />
    </Box>
  );
}
