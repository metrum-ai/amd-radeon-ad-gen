// Created by Metrum AI for AMD

import { useState, useEffect, useRef } from "react";

const PROM_BASE = import.meta.env.VITE_PROM_BASE || "/metrics";
export const HISTORY_LEN = 30;
const POLL_INTERVAL = 2000;
const MAX_CONSECUTIVE_FAILURES = 3;
const BACKOFF_INTERVAL = 30000;

export function usePrometheusQuery(query, { interval = POLL_INTERVAL, transform = null } = {}) {
  const [series, setSeries] = useState({});
  const [timestamps, setTimestamps] = useState(() => Array(HISTORY_LEN).fill(null));
  const [connected, setConnected] = useState(null);
  const queryRef = useRef(query);
  queryRef.current = query;

  useEffect(() => {
    let active = true;
    let failures = 0;
    let timerId = null;

    const schedule = () => {
      const delay = failures >= MAX_CONSECUTIVE_FAILURES ? BACKOFF_INTERVAL : interval;
      timerId = setTimeout(() => { if (active) poll(); }, delay);
    };

    const poll = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 4000);
        const url = `${PROM_BASE}/api/v1/query?query=${encodeURIComponent(queryRef.current)}`;
        const res = await fetch(url, { signal: controller.signal });
        clearTimeout(timeout);
        if (!active) return;
        if (!res.ok) throw new Error(res.statusText);
        const json = await res.json();
        if (!active) return;

        if (json.status === "success" && json.data?.result?.length > 0) {
          failures = 0;
          setConnected(true);
          const now = Date.now();
          setSeries(prev => {
            const next = { ...prev };
            json.data.result.forEach(r => {
              const key = r.metric.gpu_id ?? "all";
              let val = parseFloat(r.value[1]);
              if (transform) val = transform(val);
              if (isNaN(val)) return;
              const arr = next[key] || Array(HISTORY_LEN).fill(null);
              next[key] = [...arr.slice(1), Math.round(val * 10) / 10];
            });
            return next;
          });
          setTimestamps(prev => [...prev.slice(1), now]);
        }
      } catch {
        failures++;
        if (active && connected === null) setConnected(false);
      }
      if (active) schedule();
    };

    poll();
    return () => { active = false; if (timerId) clearTimeout(timerId); };
  }, [query, interval]);

  return { series, timestamps, connected };
}

export const QUERIES = {
  gpuCompute: 'avg by (gpu_id, card_model) (avg_over_time(gpu_gfx_activity[10s]))',
  gpuMemory: 'avg by (gpu_id, card_model) (avg_over_time(gpu_used_vram[10s]))',
  gpuTemp: 'avg by (gpu_id, card_model) (avg_over_time(gpu_edge_temperature[10s]))',
  gpuPower: 'avg by (gpu_id) (avg_over_time(gpu_average_package_power[10s]))',
  cpuUtil: '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
  sysMem: '(avg_over_time(node_memory_MemTotal_bytes[10s]) - avg_over_time(node_memory_MemAvailable_bytes[10s])) / 1024 / 1024 / 1024',
};

export const MB_TO_GB = (v) => v / 1024;
