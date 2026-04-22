// Created by Metrum AI for AMD

import { useMemo } from "react";

function pickLatestStrategy(rows) {
  if (!rows?.length) return null;
  return [...rows].sort((a, b) => {
    const ta = a.created_at || "";
    const tb = b.created_at || "";
    return tb.localeCompare(ta);
  })[0];
}

export default function useStrategyDerivedState({ campaign, pipelineStatus }) {
  const strategy =
    pickLatestStrategy(campaign?.strategy) ||
    pickLatestStrategy(campaign?.strategies) ||
    null;
  const audiences = strategy?.audience_segments || [];
  const copyVariants = campaign?.copy_variants || [];
  const scenes = campaign?.scene_prompts || [];
  const audioAds = campaign?.audio_ads || [];
  const messagingAngles = strategy?.messaging_angles || [];

  const elapsed = useMemo(() => {
    if (!pipelineStatus.length) return null;
    const durations = pipelineStatus.filter((r) => r.duration_ms).map((r) => r.duration_ms);
    if (!durations.length) return null;
    return (durations.reduce((a, b) => a + b, 0) / 1000).toFixed(1);
  }, [pipelineStatus]);

  const stageStatus = useMemo(() => {
    const map = {};
    pipelineStatus.forEach((r) => {
      map[r.stage] = r.status;
    });
    return map;
  }, [pipelineStatus]);

  const strategyReady = stageStatus.strategy === "completed";
  const copyReady = stageStatus.copy_gen === "completed";
  const scenesReady = stageStatus.scene_gen === "completed";
  const audioReady = stageStatus.audio_gen === "completed";

  const runningTab = useMemo(() => {
    const runningStage = pipelineStatus.find((r) => r.status === "running")?.stage;
    if (!runningStage) return null;
    if (runningStage === "strategy") return "direction";
    if (runningStage === "copy_gen") return "copy";
    if (runningStage === "scene_gen") return "scenes";
    if (runningStage === "audio_gen") return "audio";
    return null;
  }, [pipelineStatus]);

  return {
    strategy, audiences, copyVariants, scenes, audioAds, messagingAngles, elapsed, stageStatus,
    strategyReady, copyReady, scenesReady, audioReady, runningTab,
  };
}
