// Created by Metrum AI for AMD

import { useState, useRef, useMemo, useCallback } from "react";
import { C, radius } from "../tokens";
import { Box, T } from "./primitives";
import { HISTORY_LEN } from "../hooks/usePrometheusQuery";

function fmtNum(v) {
  if (v === null || v === undefined || isNaN(v)) return "--";
  return v % 1 ? v.toFixed(1) : String(v);
}

function fmtTime(ts) {
  if (!ts) return "--:--:--";
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function fmtVal(v, unit) {
  if (v === null || v === undefined) return "--";
  return (v % 1 ? v.toFixed(1) : v) + unit;
}

const GPU_COLORS = ["#ED1C24", "#F26522", "#FACC15", "#22C55E", "#A855F7"];

function seriesColor(color, idx) {
  if (idx === 0) return color;
  const available = GPU_COLORS.filter(c => c.toLowerCase() !== color.toLowerCase());
  return available[(idx - 1) % available.length];
}

export default function MetricGraph({ label, series, timestamps, unit, color, maxVal = 100 }) {
  const [hover, setHover] = useState(null);
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  const keys = useMemo(() => Object.keys(series).sort(), [Object.keys(series).join(",")]);
  const hasData = keys.length > 0 && keys.some(k => series[k]?.some(v => v !== null));

  const graphH = 80;
  const graphW = 200;
  const padL = 28;
  const padB = 16;
  const padT = 4;
  const padR = 4;
  const plotW = graphW - padL - padR;
  const plotH = graphH - padB - padT;

  const ticks = useMemo(() => {
    const count = 4;
    return Array.from({ length: count + 1 }, (_, i) => Math.round((maxVal / count) * i));
  }, [maxVal]);

  const timeLabels = ["-30s", "-15s", "now"];

  const pointCoords = useMemo(() => {
    const coords = {};
    keys.forEach(k => {
      const history = series[k];
      if (!history) return;
      const divisor = history.length > 1 ? history.length - 1 : 1;
      coords[k] = history.map((v, i) => {
        const clamped = v === null ? 0 : Math.max(0, Math.min(maxVal, v));
        return {
          x: padL + (i / divisor) * plotW,
          y: padT + plotH - (clamped / maxVal) * plotH,
          v,
        };
      });
    });
    return coords;
  }, [keys.join(","), series, maxVal, plotW, plotH]);

  const buildPolyline = useCallback((k) => {
    return pointCoords[k]?.map(p => `${p.x},${p.y}`).join(" ") || "";
  }, [pointCoords]);

  const handleMouseMove = useCallback((e) => {
    const svg = svgRef.current;
    const container = containerRef.current;
    if (!svg || !container) return;
    const rect = svg.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * graphW;
    const relX = svgX - padL;
    if (relX < -4 || relX > plotW + 4) { setHover(null); return; }
    const idx = Math.round((relX / plotW) * (HISTORY_LEN - 1));
    const clamped = Math.max(0, Math.min(HISTORY_LEN - 1, idx));
    const pxX = (e.clientX - rect.left);
    setHover({ index: clamped, pxX });
  }, [graphW, plotW]);

  const handleMouseLeave = useCallback(() => setHover(null), []);

  const isMulti = keys.length > 1;
  const [headerHover, setHeaderHover] = useState(false);

  const avgCurrent = useMemo(() => {
    const vals = keys.map(k => series[k]?.[series[k]?.length - 1]).filter(v => v !== null && v !== undefined);
    if (vals.length === 0) return null;
    return Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10;
  }, [keys, series]);

  const hoverX = hover !== null ? padL + (hover.index / (HISTORY_LEN - 1)) * plotW : null;
  const tooltipLeft = hover !== null
    ? (hover.pxX < 100 ? hover.pxX + 8 : hover.pxX - 108)
    : 0;

  return (
    <Box style={{ marginBottom: 16 }}>
      <Box style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <T s={10} c={C.text} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</T>
        {hasData ? (
          <Box
            style={{ position: "relative" }}
            onMouseEnter={() => isMulti && setHeaderHover(true)}
            onMouseLeave={() => setHeaderHover(false)}
          >
            <T s={13} c={color} w={700} style={{ cursor: isMulti ? "default" : "auto" }}>
              {fmtNum(avgCurrent)}
              <span style={{ fontSize: 9, color: C.dim, fontWeight: 400, marginLeft: 1 }}>{unit}</span>
            </T>
            {isMulti && headerHover && (
              <Box style={{
                position: "absolute", right: 0, top: "100%", marginTop: 4,
                background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6,
                padding: "6px 10px", zIndex: 20, minWidth: 100,
                boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
              }}>
                {keys.map((k, i) => {
                  const lineColor = seriesColor(color, i);
                  const val = series[k]?.[series[k]?.length - 1];
                  return (
                    <Box key={k} style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: i < keys.length - 1 ? 4 : 0 }}>
                      <Box style={{ width: 6, height: 6, borderRadius: 3, background: lineColor, flexShrink: 0 }} />
                      <T s={9} c={C.text} w={500}>GPU {k}</T>
                      <T s={10} c={lineColor} w={700} style={{ marginLeft: "auto" }}>
                        {fmtNum(val)}<span style={{ fontSize: 8, color: C.dim, fontWeight: 400, marginLeft: 1 }}>{unit}</span>
                      </T>
                    </Box>
                  );
                })}
              </Box>
            )}
          </Box>
        ) : (
          <T s={11} c={C.dim}>--</T>
        )}
      </Box>
      <Box
        ref={containerRef}
        style={{
          background: C.elevated, borderRadius: radius.sm,
          border: `1px solid ${C.border}`, padding: "6px 6px 2px 2px",
          position: "relative",
        }}
      >
        <svg
          ref={svgRef}
          width={graphW}
          height={graphH}
          style={{ display: "block", width: "100%", height: "auto", cursor: hasData ? "crosshair" : "default" }}
          viewBox={`0 0 ${graphW} ${graphH}`}
          onMouseMove={hasData ? handleMouseMove : undefined}
          onMouseLeave={handleMouseLeave}
        >
          {ticks.map((tick, i) => {
            const y = padT + plotH - (tick / maxVal) * plotH;
            return (
              <g key={i}>
                <line x1={padL} y1={y} x2={padL + plotW} y2={y}
                  stroke={C.border} strokeWidth="0.5" />
                <text x={padL - 4} y={y + 3} textAnchor="end"
                  fill={C.dim} fontSize="7" fontFamily="Inter, sans-serif">{tick}</text>
              </g>
            );
          })}
          {timeLabels.map((lbl, i) => {
            const x = padL + (i / (timeLabels.length - 1)) * plotW;
            return (
              <text key={i} x={x} y={graphH - 2} textAnchor="middle"
                fill={C.dim} fontSize="7" fontFamily="Inter, sans-serif">{lbl}</text>
            );
          })}

          {keys.map((k, idx) => {
            const lineColor = seriesColor(color, idx);
            const pts = buildPolyline(k);
            if (!pts) return null;
            const coords = pointCoords[k];
            const fillPts = `${padL},${padT + plotH} ${pts} ${padL + plotW},${padT + plotH}`;

            return (
              <g key={k}>
                <polygon points={fillPts} fill={`${lineColor}10`} />
                <polyline points={pts} fill="none" stroke={lineColor} strokeWidth="1.5"
                  vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
                {coords.map((p, i) => p.v !== null && (
                  <circle
                    key={i}
                    cx={p.x} cy={p.y}
                    r={hover?.index === i ? 3.5 : 1.8}
                    fill={lineColor}
                    opacity={hover?.index === i ? 1 : 0.5}
                  />
                ))}
              </g>
            );
          })}

          {hover !== null && hoverX !== null && (
            <line
              x1={hoverX} y1={padT} x2={hoverX} y2={padT + plotH}
              stroke={C.dim} strokeWidth="0.5" strokeDasharray="2,2"
            />
          )}
        </svg>

        {hover !== null && hasData && (
          <div style={{
            position: "absolute",
            left: tooltipLeft,
            top: 4,
            background: C.bg,
            border: `1px solid ${C.border}`,
            borderRadius: 6,
            padding: "5px 8px",
            pointerEvents: "none",
            zIndex: 10,
            minWidth: 80,
            boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
          }}>
            <div style={{ fontSize: 8, color: C.dim, marginBottom: 3, fontFamily: "Inter, sans-serif", letterSpacing: "0.04em" }}>
              {fmtTime(timestamps?.[hover.index])}
            </div>
            {keys.map((k, idx) => {
              const lineColor = seriesColor(color, idx);
              const val = series[k]?.[hover.index];
              return (
                <div key={k} style={{
                  fontSize: 10, fontFamily: "Inter, sans-serif", fontWeight: 600,
                  color: lineColor,
                  display: "flex", alignItems: "center", gap: 4,
                }}>
                  {isMulti && (
                    <span style={{
                      width: 6, height: 6, borderRadius: 3, background: lineColor,
                      display: "inline-block", flexShrink: 0,
                    }} />
                  )}
                  {isMulti && <span style={{ fontSize: 8, color: C.text, fontWeight: 500 }}>GPU {k}</span>}
                  <span>{fmtVal(val, unit)}</span>
                </div>
              );
            })}
          </div>
        )}
      </Box>
      {isMulti && hasData && (
        <Box style={{ display: "flex", gap: 10, marginTop: 4 }}>
          {keys.map((k, i) => {
            const lineColor = seriesColor(color, i);
            return (
              <Box key={k} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <Box style={{ width: 6, height: 6, borderRadius: 3, background: lineColor }} />
                <T s={8} c={C.text}>GPU {k}</T>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
