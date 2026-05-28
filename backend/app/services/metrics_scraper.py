# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

"""Prometheus -> PostgreSQL metrics bridge. Polls Prometheus HTTP API
and writes GPU metrics to the gpu_metrics table for frontend consumption.

When no real AMD GPU hardware is detected (preflight check fails), the
scraper generates realistic simulated metrics so the dashboard always
has data to display.
"""

import logging
import random  # nosec B311
import time
from datetime import datetime, timezone

import httpx
from app.config import settings
from app.db.models import GpuMetric
from app.services.gpu_preflight import gpu_hardware_available
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

log = logging.getLogger("metrics_scraper")

sync_engine = create_engine(
    settings.database_url.replace("+asyncpg", "+psycopg")
)
SyncSession = sessionmaker(sync_engine)

PROMETHEUS_URL = "http://prometheus:9090"
SCRAPE_INTERVAL = 5


GPU_QUERIES = {
    "vram_used_mb": "gpu_used_vram",
    "vram_total_mb": "gpu_total_vram",
    "gpu_util_pct": "gpu_gfx_activity",
    "power_watts": "gpu_average_package_power",
    "temp_celsius": "gpu_edge_temperature",
}


# ---------------------------------------------------------------------------
# Simulated metrics generator
# ---------------------------------------------------------------------------


class SimulatedGpuState:
    """Maintains smoothly-varying fake GPU metrics per GPU index."""

    def __init__(self, gpu_index: int):
        self.gpu_index = gpu_index
        self.vram_used_mb = 9800 + random.randint(-500, 500)  # nosec B311
        self.vram_total_mb = 32768
        self.gpu_util_pct = 45.0 + random.random() * 40  # nosec B311
        self.power_watts = 120.0 + random.random() * 30  # nosec B311
        self.temp_celsius = 58.0 + random.random() * 10  # nosec B311

    def step(self) -> dict:
        """Advance one tick and return a metrics dict."""
        self.vram_used_mb = max(
            512,
            min(
                self.vram_total_mb,
                self.vram_used_mb + random.randint(-200, 200),  # nosec B311
            ),
        )
        self.gpu_util_pct = max(
            0,
            min(100, self.gpu_util_pct + random.uniform(-5, 5)),  # nosec B311
        )
        self.power_watts = max(
            30,
            min(300, self.power_watts + random.uniform(-8, 8)),  # nosec B311
        )
        self.temp_celsius = max(
            30,
            min(95, self.temp_celsius + random.uniform(-2, 2)),  # nosec B311
        )
        return {
            "vram_used_mb": self.vram_used_mb,
            "vram_total_mb": self.vram_total_mb,
            "gpu_util_pct": round(self.gpu_util_pct, 1),
            "power_watts": round(self.power_watts, 1),
            "temp_celsius": round(self.temp_celsius, 1),
        }


def generate_simulated(gpu_states: list[SimulatedGpuState]):
    """Write one tick of simulated data to PostgreSQL."""
    with SyncSession() as db:
        now = datetime.now(timezone.utc)
        for state in gpu_states:
            db.add(
                GpuMetric(
                    recorded_at=now,
                    gpu_index=state.gpu_index,
                    **state.step(),
                )
            )
        db.commit()
        log.debug("Stored simulated metrics for %d GPUs", len(gpu_states))


# ---------------------------------------------------------------------------
# Real Prometheus scraper
# ---------------------------------------------------------------------------


def query_prometheus(query: str) -> list[dict]:
    """Execute a PromQL instant query and return results."""
    try:
        resp = httpx.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("result", [])
    except Exception as e:
        log.warning("Prometheus query failed: %s", e)
        return []


def scrape_and_store():
    """Scrape GPU metrics from Prometheus and persist to the database."""
    gpu_data: dict[int, dict] = {}

    for metric_name, prom_query in GPU_QUERIES.items():
        results = query_prometheus(prom_query)
        for r in results:
            gpu_idx = int(r.get("metric", {}).get("gpu_id", "0"))
            if gpu_idx not in gpu_data:
                gpu_data[gpu_idx] = {}
            value = r.get("value", [None, None])
            if len(value) >= 2 and value[1] is not None:
                try:
                    gpu_data[gpu_idx][metric_name] = float(value[1])
                except (ValueError, TypeError):
                    pass

    if not gpu_data:
        return False  # signal: no real data

    with SyncSession() as db:
        now = datetime.now(timezone.utc)
        for gpu_idx, metrics in gpu_data.items():
            db.add(
                GpuMetric(
                    recorded_at=now,
                    gpu_index=gpu_idx,
                    **metrics,
                )
            )
        db.commit()
        log.info("Stored metrics for %d GPUs", len(gpu_data))
    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main():
    """Run the metrics scraper loop."""
    hw_available = gpu_hardware_available()
    mode = "real" if hw_available else "simulated"
    log.info(
        "Metrics scraper started (interval=%ds, mode=%s)",
        SCRAPE_INTERVAL,
        mode,
    )

    # Pre-create simulated GPU state (1 GPU when faking)
    sim_states = [SimulatedGpuState(0)] if not hw_available else []

    while True:
        if hw_available:
            got_data = scrape_and_store()
            # If the exporter was available at startup but Prometheus
            # temporarily returns empty, just skip this tick.
            if not got_data:
                log.debug("No real GPU data this tick — skipping")
        else:
            generate_simulated(sim_states)
        time.sleep(SCRAPE_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
