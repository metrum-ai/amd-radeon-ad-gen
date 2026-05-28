// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C, radius } from "../tokens";
import { Box, T } from "./primitives";
import MetricGraph from "./MetricGraph";
import { usePrometheusQuery, QUERIES, MB_TO_GB } from "../hooks/usePrometheusQuery";

export default function GpuSidebar({ open, onToggle }) {
  const gpuCompute = usePrometheusQuery(QUERIES.gpuCompute);
  const gpuMemory = usePrometheusQuery(QUERIES.gpuMemory, { transform: MB_TO_GB });
  const gpuTemp = usePrometheusQuery(QUERIES.gpuTemp);
  const gpuPower = usePrometheusQuery(QUERIES.gpuPower);
  const cpuUtil = usePrometheusQuery(QUERIES.cpuUtil);
  const sysMem = usePrometheusQuery(QUERIES.sysMem);

  const anyConnected = [gpuCompute, gpuMemory, gpuTemp, gpuPower, cpuUtil, sysMem]
    .some(q => q.connected === true);
  const allChecked = [gpuCompute, gpuMemory, gpuTemp, gpuPower, cpuUtil, sysMem]
    .every(q => q.connected !== null);

  if (!open) {
    return (
      <Box
        onClick={onToggle}
        style={{
          width: 36, flexShrink: 0,
          background: C.surface,
          borderLeft: `1px solid ${C.border}`,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          cursor: "pointer",
          transition: "background 0.15s ease",
        }}
        onMouseEnter={e => e.currentTarget.style.background = C.card}
        onMouseLeave={e => e.currentTarget.style.background = C.surface}
      >
        <T s={14} c={C.dim} style={{ writingMode: "vertical-rl", textOrientation: "mixed", letterSpacing: "0.08em" }}>
        AMD Radeon™ AI PRO R9700S
        </T>
        <T s={16} c={C.dim} style={{ marginTop: 12 }}>{"\u2039"}</T>
      </Box>
    );
  }

  return (
    <Box style={{
      width: 230, flexShrink: 0,
      background: C.surface,
      borderLeft: `1px solid ${C.border}`,
      display: "flex", flexDirection: "column",
      overflowY: "auto",
      animation: "fadeIn 0.2s ease",
    }}>
      <Box style={{
        padding: "8px 14px", display: "flex", justifyContent: "flex-end",
        position: "sticky", top: 0, zIndex: 5,
        background: C.surface,
      }}>
        <Box
          onClick={onToggle}
          style={{
            width: 24, height: 24, borderRadius: 6,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", background: C.elevated,
          }}
          onMouseEnter={e => e.currentTarget.style.background = C.border}
          onMouseLeave={e => e.currentTarget.style.background = C.elevated}
        >
          <T s={12} c={C.dim}>{"\u203A"}</T>
        </Box>
      </Box>

      <Box style={{
        padding: "8px 16px 16px",
        borderBottom: `1px solid ${C.border}`,
        textAlign: "center",
      }}>
        <img src="/assets/radeon_gpu.png" alt="AMD Radeon™ AI PRO R9700S" style={{
          width: "100%", maxWidth: 160, objectFit: "contain", marginBottom: 10,
        }} />
        <T s={11} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>AI PRO</T>
        <T s={14} c={C.white} w={700}>AMD Radeon™ AI PRO R9700S</T>

        <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 14 }}>
          <Box style={{ textAlign: "center" }}>
            <T s={16} w={700} c={C.white}>64</T>
            <T s={8} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>Compute Units</T>
          </Box>
          <Box style={{ textAlign: "center" }}>
            <T s={16} w={700} c={C.white}>128</T>
            <T s={8} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>AI Accelerators</T>
          </Box>
          <Box style={{ textAlign: "center" }}>
            <T s={14} w={700} c={C.white}>4,096</T>
            <T s={8} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>Stream Processors</T>
          </Box>
          <Box style={{ textAlign: "center" }}>
            <T s={14} w={700} c={C.white}>64</T>
            <T s={8} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>Ray Accelerators</T>
          </Box>
        </Box>
        <Box style={{ marginTop: 10 }}>
          <T s={16} w={700} c={C.white}>32 GB</T>
        </Box>
      </Box>

      <Box style={{ padding: "12px 14px", flex: 1 }}>
        {allChecked && !anyConnected && (
          <Box style={{
            padding: "10px 12px", borderRadius: radius.sm,
            background: C.elevated, border: `1px solid ${C.border}`,
            marginBottom: 14, textAlign: "center",
          }}>
            <T s={10} c={C.dim} w={500}>Prometheus not reachable</T>
            <T s={9} c={C.dim} style={{ marginTop: 2, opacity: 0.6 }}>Expecting metrics at /metrics</T>
          </Box>
        )}

        <MetricGraph label="GPU Compute" series={gpuCompute.series} timestamps={gpuCompute.timestamps} unit="%" color="#ED1C24" maxVal={100} />
        <MetricGraph label="GPU Memory" series={gpuMemory.series} timestamps={gpuMemory.timestamps} unit="GB" color="#FACC15" maxVal={32} />
        <MetricGraph label="GPU Temperature" series={gpuTemp.series} timestamps={gpuTemp.timestamps} unit="°C" color="#22C55E" maxVal={100} />
        <MetricGraph label="GPU Power" series={gpuPower.series} timestamps={gpuPower.timestamps} unit="W" color="#F26522" maxVal={300} />
        <MetricGraph label="CPU Utilization" series={cpuUtil.series} timestamps={cpuUtil.timestamps} unit="%" color="#EC4899" maxVal={100} />
        <MetricGraph label="System Memory" series={sysMem.series} timestamps={sysMem.timestamps} unit="GB" color="#A855F7" maxVal={64} />
      </Box>

      <Box style={{
        padding: "10px 14px",
        borderTop: `1px solid ${C.border}`,
      }}>
        <Box style={{ display: "flex", alignItems: "center", gap: 5, justifyContent: "center" }}>
          <Box style={{
            width: 6, height: 6, borderRadius: 3,
            background: anyConnected ? C.orange : C.dim,
            animation: anyConnected ? "livePulse 1.6s ease-in-out infinite" : "none",
          }} />
          <T s={10} c={anyConnected ? C.orange : C.dim} w={700} style={{ letterSpacing: "0.08em", textTransform: "uppercase" }}>
            {anyConnected ? "Live" : "Offline"}
          </T>
        </Box>
      </Box>
    </Box>
  );
}
