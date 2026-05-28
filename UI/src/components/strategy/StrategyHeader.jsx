// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C, radius } from "../../tokens";
import { Box, T, Badge } from "../primitives";
import "../../css/strategy/StrategyHeader.css";

export default function StrategyHeader({ campaign, isLoading, isFailed, elapsed, contentMissing }) {
  const llmModel = campaign?.metrics?.llm?.model || "";
  const isOpenClaw = /openclaw/i.test(llmModel);
  return (
    <Box className="strategy-header">
      <Box className="strategy-header__titleBlock">
        <T s={24} w={700} className="strategy-header__title">Strategy Directive</T>
        <T s={13} c={C.muted}>
          {isLoading ? "AI is generating your strategy..." : "Review AI output. Edit anything before approving."}
        </T>
      </Box>
      {isOpenClaw && (
        <Box style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 10px", background: C.elevated, border: `1px solid ${C.border}`, borderRadius: radius.md }}>
            <img
              src="/assets/openclaw.png"
              alt="OpenClaw"
              width={14}
              height={14}
              style={{ display: "block", objectFit: "contain", filter: "invert(1) hue-rotate(180deg)" }}
            />
            <T s={11} w={700}>OpenClaw</T>
            <T s={10} c={C.dim}>used for LLM generation</T>
          </Box>
        </Box>
      )}
      {campaign?.metrics?.llm && (
        <Box className="strategy-header__metrics" style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: radius.md }}>
          <Box className="strategy-header__metricCell">
            <T s={9} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>LLM Throughput</T>
            <Box className="strategy-header__metricValue">
              <T s={13} w={700} c={C.teal}>{campaign.metrics.llm.tokens_per_sec ?? "--"}</T>
              <T s={8} c={C.dim}>tok/s</T>
            </Box>
          </Box>
          <Box style={{ width: 1, height: 20, background: C.border }} />
          <Box className="strategy-header__metricCell">
            <T s={9} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>Total Tokens Generated</T>
            <T s={12} w={600}>{campaign.metrics.llm.total_tokens?.toLocaleString() ?? "--"}</T>
          </Box>
          <Box style={{ width: 1, height: 20, background: C.border }} />
          <Box className="strategy-header__metricCell">
            <T s={9} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>LLM Model</T>
            <T s={10} w={500} c={C.muted}>{campaign.metrics.llm.model || "--"}</T>
          </Box>
        </Box>
      )}
      <Box className="strategy-header__status">
        {isFailed && <Badge bg={C.red}>Failed</Badge>}
        {!isLoading && !isFailed && !contentMissing && <Badge bg={C.green}>Phase 1 Complete</Badge>}
        {!isLoading && !isFailed && contentMissing && <Badge bg={C.orange || "#ed8936"}>Incomplete -- missing content</Badge>}
        {isLoading && <Badge bg={C.accent}>Running...</Badge>}
        {elapsed && <T s={11} c={C.dim} w={500}>{elapsed}s</T>}
      </Box>
    </Box>
  );
}
