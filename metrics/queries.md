<!-- Created by Metrum AI for AMD -->

# Prometheus Queries

PromQL queries used by the GPU/system monitoring sidebar in the frontend
(`UI/src/hooks/usePrometheusQuery.js` → `UI/src/components/GpuSidebar.jsx`).

All queries are polled every 2 seconds from the browser via the Nginx
proxy at `/metrics/api/v1/query`.

## GPU Metrics (AMD Device Metrics Exporter)

| Name | Query | Unit |
|------|-------|------|
| GPU Compute | `avg by (gpu_id, card_model) (avg_over_time(gpu_gfx_activity[10s]))` | % |
| GPU VRAM | `avg by (gpu_id, card_model) (avg_over_time(gpu_used_vram[10s]))` | MB (converted to GB in UI) |
| GPU Temperature | `avg by (gpu_id, card_model) (avg_over_time(gpu_edge_temperature[10s]))` | °C |
| GPU Power | `avg by (gpu_id) (avg_over_time(gpu_average_package_power[10s]))` | W |

## System Metrics (Node Exporter)

| Name | Query | Unit |
|------|-------|------|
| CPU Utilisation | `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` | % |
| System Memory | `(avg_over_time(node_memory_MemTotal_bytes[10s]) - avg_over_time(node_memory_MemAvailable_bytes[10s])) / 1024 / 1024 / 1024` | GB |

## Scrape Targets

Configured in `metrics/prometheus.yml`:

| Job | Target | Source |
|-----|--------|--------|
| gpu-metrics | `amd-device-metrics-exporter:5000` | `rocm/device-metrics-exporter:v1.4.2` |
| node-exporter | `node-exporter:9100` | `prom/node-exporter:latest` |
