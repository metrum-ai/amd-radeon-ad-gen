// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C, radius } from "../../tokens";
import { Box } from "../primitives";
import "../../css/strategy/StrategySkeleton.css";

export default function StrategySkeleton({ w = "100%", h = 16, style }) {
  return (
    <Box className="strategy-skeleton" style={{
      width: w, height: h, borderRadius: radius.sm,
      background: `linear-gradient(90deg, ${C.elevated} 25%, ${C.border}30 50%, ${C.elevated} 75%)`,
      ...style,
    }} />
  );
}
