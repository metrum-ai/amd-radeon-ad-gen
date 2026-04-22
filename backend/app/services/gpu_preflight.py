# Created by Metrum AI for AMD

"""GPU hardware preflight check.

Runs before the metrics scraper to verify that `amd-smi` (ROCm) is
reachable, either locally or via the device-metrics-exporter container.
Exports a boolean flag so the scraper knows whether to expect real data
or fall back to simulated metrics.
"""

import logging
import os
import shutil
import subprocess  # nosec B404

import httpx

log = logging.getLogger("gpu_preflight")

# Where the official AMD exporter lives inside the compose network
EXPORTER_URL = os.getenv(
    "AMD_EXPORTER_URL", "http://amd-device-metrics-exporter:5000/metrics"
)


def _check_local_amd_smi() -> bool:
    """Return True if `amd-smi` is on PATH and exits cleanly."""
    if not shutil.which("amd-smi"):
        return False
    try:
        result = subprocess.run(  # nosec B603 B607
            ["amd-smi", "version"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception as exc:
        log.debug("amd-smi local check failed: %s", exc)
        return False


def _check_exporter_endpoint() -> bool:
    """Return True if the device-metrics-exporter HTTP endpoint responds."""
    try:
        resp = httpx.get(EXPORTER_URL, timeout=5)
        return resp.status_code == 200 and len(resp.text) > 0
    except Exception as exc:
        log.debug("Exporter endpoint check failed: %s", exc)
        return False


def gpu_hardware_available() -> bool:
    """Run all preflight checks; return True if *any* GPU source works."""
    if _check_exporter_endpoint():
        log.info("GPU preflight PASS: device-metrics-exporter reachable")
        return True
    if _check_local_amd_smi():
        log.info("GPU preflight PASS: local amd-smi available")
        return True
    log.warning(
        "GPU preflight FAIL: no AMD GPU source detected — will use simulated metrics"
    )
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = gpu_hardware_available()
    raise SystemExit(0 if result else 1)
