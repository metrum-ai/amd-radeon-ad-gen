#!/usr/bin/env bash
# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

# =============================================================================
# AI Ad Generator — Setup & Launch
# Checks prerequisites, configures environment, detects GPUs, and starts services.
# =============================================================================
# Bash is required (arrays, pipefail); "sh setup.sh" would otherwise stop with
# a cryptic "Illegal option -o pipefail".
if [ -z "${BASH_VERSION:-}" ]; then
    echo "[FAIL]  Run this script with bash: ./setup.sh (or: bash setup.sh)" >&2
    exit 1
fi
set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[FAIL]${NC}  $*"; }
die()   { error "$*"; exit 1; }
hr()    { echo -e "${BOLD}────────────────────────────────────────────────────${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Set a key=value in .env: replace if the key exists, append if it doesn't
set_env() {
    local key="$1" val="$2"
    if grep -q "^${key}=" .env 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" .env
    else
        echo "${key}=${val}" >> .env
    fi
}

# Resolve the non-root host UID/GID that the FLUX / LTX-Video containers run
# as (written to .env as APP_UID/APP_GID). Under sudo or a root login, id -u
# is 0, and the Dockerfiles' "useradd -u 0" fails with "UID 0 is not unique",
# breaking the build. So use the invoking sudo user, else the 1000:1000
# default the compose files already fall back to.
resolve_app_ids() {
    APP_UID_VAL=$(id -u)
    APP_GID_VAL=$(id -g)
    if [ "$APP_UID_VAL" -eq 0 ]; then
        if [ -n "${SUDO_UID:-}" ] && [ "${SUDO_UID}" -ne 0 ]; then
            APP_UID_VAL="${SUDO_UID}"
            APP_GID_VAL="${SUDO_GID:-$SUDO_UID}"
        else
            APP_UID_VAL=1000
            APP_GID_VAL=1000
            warn "Running as root with no non-root sudo user — containers will run as UID/GID 1000:1000."
        fi
    fi
    if [ "$APP_GID_VAL" -eq 0 ]; then
        APP_GID_VAL=1000
    fi
}

# Home directory of the user who launched the script. sudo resets HOME to
# /root, which would put the model caches (~40 GB) under /root and let the
# model-cache-perms service hand /root/.cache to APP_UID. Use the sudo user's
# own home instead.
USER_HOME="$HOME"
if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    _sudo_home=$(getent passwd "${SUDO_USER}" | cut -d: -f6 || true)
    [ -n "$_sudo_home" ] && USER_HOME="$_sudo_home"
fi

# Prompt helper failure: stdin is closed or not a terminal (CI, nohup,
# "< /dev/null"). Without this, the answer-required prompt loops below would
# repeat forever.
no_input() {
    die "No input available for: $1 — run ./setup.sh from an interactive terminal."
}

# --- Credential helpers ---
# Value of KEY in the current .env, or empty. The .env.example placeholder
# (CHANGE_ME) counts as empty so a copied example file is never reused.
old_env_val() {
    local val
    val=$(grep "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- || true)
    [ "$val" = "CHANGE_ME" ] && val=""
    echo "$val"
}

# 32 hex chars: safe inside the database URL, sed replacements and the
# OpenClaw seed substitution.
gen_secret() {
    od -An -N16 -tx1 /dev/urandom | tr -d ' \n'
}

# True if this compose project already has the named data volume.
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-$(basename "$SCRIPT_DIR" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')}"
volume_exists() {
    docker volume inspect "${COMPOSE_PROJECT}_$1" >/dev/null 2>&1
}

# pick_secret OLD_VALUE VOLUME LEGACY_DEFAULT LABEL
# Reuse OLD_VALUE; else keep LEGACY_DEFAULT if VOLUME already holds data
# initialised with it; else generate a new random secret.
pick_secret() {
    if [ -n "$1" ]; then
        echo "$1"
    elif [ -n "$2" ] && volume_exists "$2"; then
        warn "Existing '$2' data volume found without its .env — keeping the legacy default $4 so it still matches." >&2
        echo "$3"
    else
        gen_secret
    fi
}

echo ""
hr
echo -e "  ${BOLD}AI Ad Generator — Setup & Launch${NC}"
hr
echo ""

# =============================================================================
# STEP 1: PREREQUISITES
# =============================================================================
echo -e "${BOLD}[1/4] Checking prerequisites...${NC}"
echo ""
PREREQ_FAIL=0

# Docker
if ! command -v docker &>/dev/null; then
    error "docker not found — install: https://docs.docker.com/get-docker/"
    PREREQ_FAIL=1
elif ! docker info &>/dev/null 2>&1; then
    error "Docker daemon not running — start with: sudo systemctl start docker"
    PREREQ_FAIL=1
else
    DOCKER_VER=$(docker --version | awk '{print $3}' | tr -d ',')
    DOCKER_MAJOR=$(echo "$DOCKER_VER" | cut -d. -f1)
    if [ "${DOCKER_MAJOR:-0}" -lt 25 ]; then
        error "Docker $DOCKER_VER detected — version 25.0+ required"
        PREREQ_FAIL=1
    else
        ok "Docker $DOCKER_VER"
    fi
fi

# Docker Compose v2
if docker compose version &>/dev/null 2>&1; then
    ok "Docker Compose $(docker compose version --short 2>/dev/null || echo 'v2')"
else
    error "Docker Compose v2 not found — install: https://docs.docker.com/compose/install/"
    PREREQ_FAIL=1
fi

# ROCm drivers + AMD GPUs
GPU_COUNT=0
if command -v rocm-smi &>/dev/null; then
    GPU_COUNT=$(rocm-smi --showid 2>/dev/null | grep -o "GPU\[[0-9]*\]" | sort -u | wc -l || true)
    GPU_COUNT=${GPU_COUNT:-0}
    if [ "$GPU_COUNT" -eq 0 ]; then
        GPU_COUNT=$(rocm-smi -i 2>/dev/null | grep -o "GPU\[[0-9]*\]" | sort -u | wc -l || true)
        GPU_COUNT=${GPU_COUNT:-0}
    fi
    if [ "$GPU_COUNT" -eq 0 ]; then
        GPU_COUNT=$(rocm-smi 2>/dev/null | grep -cE "^\s*[0-9]" || echo 0)
    fi
fi

if [ "$GPU_COUNT" -eq 0 ] && [ -d /sys/class/drm ]; then
    GPU_COUNT=$(ls -d /sys/class/drm/card*/device/vendor 2>/dev/null | while read f; do
        cat "$f" 2>/dev/null
    done | grep -c "0x1002" || echo 0)
fi

if [ "$GPU_COUNT" -eq 0 ]; then
    error "No AMD GPUs detected — ROCm drivers required (https://rocm.docs.amd.com)"
    PREREQ_FAIL=1
elif [ "$GPU_COUNT" -lt 2 ]; then
    error "${GPU_COUNT} AMD GPU detected — minimum 2 required (Ollama + at least one generation service)"
    PREREQ_FAIL=1
else
    GPU_NAMES=""
    if command -v rocm-smi &>/dev/null; then
        GPU_NAMES=$(rocm-smi --showproductname 2>/dev/null | grep "Card Series" | sed 's/.*: *//' | tr '\n' ',' | sed 's/,$//' || echo "")
    fi
    if [ -z "$GPU_NAMES" ]; then
        ok "${GPU_COUNT} AMD GPU(s) detected"
    else
        ok "${GPU_COUNT} AMD GPU(s): ${GPU_NAMES}"
    fi
fi

# /dev/kfd and /dev/dri (ROCm device nodes)
RENDER_GID=""
if [ ! -e /dev/kfd ]; then
    error "/dev/kfd not found — ROCm kernel driver not loaded"
    PREREQ_FAIL=1
elif [ ! -d /dev/dri ]; then
    error "/dev/dri not found — DRM subsystem not available"
    PREREQ_FAIL=1
else
    # Detect the GID that owns /dev/kfd (the render/video group on this host)
    RENDER_GID=$(stat -c '%g' /dev/kfd 2>/dev/null)
    if [ -z "$RENDER_GID" ]; then
        RENDER_GID=$(getent group render 2>/dev/null | cut -d: -f3)
    fi
    if [ -z "$RENDER_GID" ]; then
        RENDER_GID=$(getent group video 2>/dev/null | cut -d: -f3)
    fi
    if [ -z "$RENDER_GID" ]; then
        error "Could not detect GPU device group GID from /dev/kfd — set RENDER_GID manually in .env"
        PREREQ_FAIL=1
    else
        ok "ROCm device nodes (/dev/kfd, /dev/dri) — GPU group GID=${RENDER_GID}"
    fi
fi

# Disk space — scale by GPU count, reduce if models/images are already cached
FREE_GB=$(df -BG "$SCRIPT_DIR" | awk 'NR==2{gsub("G","",$4); print $4}')

# Fresh-install baselines by GPU count
if [ "$GPU_COUNT" -le 2 ]; then
    DISK_MIN=100; DISK_REC=150
elif [ "$GPU_COUNT" -eq 3 ]; then
    DISK_MIN=150; DISK_REC=200
else
    DISK_MIN=200; DISK_REC=300
fi

# Detect cached artifacts from a previous run
_cache_home="$USER_HOME"
[ -f .env ] && _eh=$(grep '^HOST_HOME=' .env 2>/dev/null | cut -d= -f2) && [ -n "$_eh" ] && _cache_home="$_eh"

_cached=""
if [ -d "$_cache_home/.ollama/models/manifests" ]; then
    DISK_MIN=$((DISK_MIN - 10))
    _cached="Ollama models"
fi
if ls "$_cache_home/.cache/huggingface/hub"/models--* &>/dev/null 2>&1; then
    DISK_MIN=$((DISK_MIN - 20))
    _cached="${_cached:+$_cached, }HuggingFace weights"
fi
if docker images --format '{{.Repository}}' 2>/dev/null | grep -qE "flux|ollama|ltx"; then
    DISK_MIN=$((DISK_MIN - 50))
    DISK_REC=$((DISK_REC - 50))
    _cached="${_cached:+$_cached, }Docker images"
fi

# Floor: always require at least 20 GB operational headroom
[ "$DISK_MIN" -lt 20 ] && DISK_MIN=20
[ "$DISK_REC" -lt "$((DISK_MIN + 20))" ] && DISK_REC=$((DISK_MIN + 20))

if [ "${FREE_GB:-0}" -lt "$DISK_MIN" ]; then
    if [ -n "$_cached" ]; then
        error "Only ${FREE_GB} GB free — minimum ${DISK_MIN} GB required (already cached: ${_cached})"
    else
        error "Only ${FREE_GB} GB free — minimum ${DISK_MIN} GB required for fresh install"
    fi
    # PREREQ_FAIL=1
elif [ "${FREE_GB:-0}" -lt "$DISK_REC" ]; then
    if [ -n "$_cached" ]; then
        warn "${FREE_GB} GB free — ${DISK_REC} GB+ recommended (already cached: ${_cached})"
    else
        warn "${FREE_GB} GB free — ${DISK_REC} GB+ recommended for comfortable operation"
    fi
else
    if [ -n "$_cached" ]; then
        ok "${FREE_GB} GB free disk space (already cached: ${_cached})"
    else
        ok "${FREE_GB} GB free disk space"
    fi
fi

# RAM: 4-GPU needs >=128 GB (two FLUX instances ~76 GB alone), 2-GPU needs >=64 GB
TOTAL_RAM_GB=$(awk '/MemTotal/{printf "%d", $2/1024/1024}' /proc/meminfo 2>/dev/null || echo 0)
if [ "${TOTAL_RAM_GB:-0}" -lt 64 ]; then
    error "${TOTAL_RAM_GB} GB RAM — minimum 64 GB required (2-GPU) / 128 GB (4-GPU)"
    PREREQ_FAIL=1
elif [ "${TOTAL_RAM_GB:-0}" -lt 128 ]; then
    warn "${TOTAL_RAM_GB} GB RAM — sufficient for 2-GPU setup; 4-GPU setup needs 128 GB+"
else
    ok "${TOTAL_RAM_GB} GB total RAM"
fi

echo ""
if [ "$PREREQ_FAIL" -ne 0 ]; then
    die "Fix the errors above then re-run this script."
fi

# =============================================================================
# STEP 2: GPU DETECTION & PROFILE SELECTION
# =============================================================================
echo -e "${BOLD}[2/4] GPU configuration${NC}"
echo ""

# --- Detect which GPUs are free (no active compute processes) ---
declare -a FREE_GPUS=()
declare -A _GPU_BUSY=()

if command -v rocm-smi &>/dev/null; then
    # Method 1: rocm-smi --showpidgpus
    # Output format (per PID):
    #   PID 12345 is using N DRM device(s):
    #   0 1
    # GPU indices appear on the line AFTER the PID header.
    _pidgpu_out=$(rocm-smi --showpidgpus 2>/dev/null || true)
    _in_pid_block=0
    while IFS= read -r _line; do
        if echo "$_line" | grep -qE "is using .* DRM device"; then
            _in_pid_block=1
            continue
        fi
        if [ "$_in_pid_block" -eq 1 ]; then
            for _tok in $_line; do
                if echo "$_tok" | grep -qE '^[0-9]+$'; then
                    _GPU_BUSY[$_tok]=1
                fi
            done
            _in_pid_block=0
        fi
    done <<< "$_pidgpu_out"

    # Method 2 (cross-check): rocm-smi --showpids GPU(s) column
    # Output: PID  PROCESS_NAME  GPU(s)  VRAM_USED  ...
    # GPU(s) column may contain comma-separated IDs.
    if [ ${#_GPU_BUSY[@]} -eq 0 ]; then
        _pids_out=$(rocm-smi --showpids 2>/dev/null || true)
        while IFS= read -r _line; do
            if echo "$_line" | grep -qE '^[0-9]+\s'; then
                _gpu_col=$(echo "$_line" | awk '{print $3}')
                IFS=',' read -ra _gids <<< "$_gpu_col"
                for _g in "${_gids[@]}"; do
                    _g=$(echo "$_g" | tr -d ' ')
                    if echo "$_g" | grep -qE '^[0-9]+$'; then
                        _GPU_BUSY[$_g]=1
                    fi
                done
            fi
        done <<< "$_pids_out"
    fi

    for gpu_id in $(seq 0 $((GPU_COUNT - 1))); do
        if [ -z "${_GPU_BUSY[$gpu_id]+x}" ]; then
            FREE_GPUS+=("$gpu_id")
        fi
    done

    # Fallback: if PID-based detection found nothing, check GPU utilization
    if [ ${#FREE_GPUS[@]} -eq 0 ] && [ ${#_GPU_BUSY[@]} -eq 0 ]; then
        for gpu_id in $(seq 0 $((GPU_COUNT - 1))); do
            _util=$(rocm-smi -d "$gpu_id" --showuse 2>/dev/null | grep -oP '\d+(?=%)' | head -1 || echo "0")
            if [ "${_util:-0}" -lt 5 ]; then
                FREE_GPUS+=("$gpu_id")
            fi
        done
    fi

    # Last resort: if we still can't determine, assume all GPUs are free
    if [ ${#FREE_GPUS[@]} -eq 0 ] && [ ${#_GPU_BUSY[@]} -eq 0 ] && [ "$GPU_COUNT" -gt 0 ]; then
        warn "Could not determine GPU utilization — assuming all ${GPU_COUNT} GPUs are free."
        for gpu_id in $(seq 0 $((GPU_COUNT - 1))); do
            FREE_GPUS+=("$gpu_id")
        done
    fi
else
    # No rocm-smi: assume all detected GPUs are free
    for gpu_id in $(seq 0 $((GPU_COUNT - 1))); do
        FREE_GPUS+=("$gpu_id")
    done
fi

FREE_GPU_COUNT=${#FREE_GPUS[@]}

if [ "$FREE_GPU_COUNT" -eq 0 ]; then
    die "No free AMD GPUs available — all ${GPU_COUNT} GPU(s) are currently in use. Free up at least 2 GPUs and re-run."
elif [ "$FREE_GPU_COUNT" -lt 2 ]; then
    die "Only 1 free GPU (GPU ${FREE_GPUS[0]}) — minimum 2 free GPUs required (Ollama + at least one generation service). Free up more GPUs and re-run."
else
    ok "${FREE_GPU_COUNT} free GPU(s) available: ${FREE_GPUS[*]}"
fi

echo ""

# --- Allocate free GPUs to services ---
PROFILE=""
OLLAMA_GPU=${FREE_GPUS[0]}
FLUX_GPU=${FREE_GPUS[1]}
FLUX_GPU_2=-1
LTX_GPU=-1

if [ "$FREE_GPU_COUNT" -eq 2 ]; then
    info "2 free GPUs detected (GPU ${FREE_GPUS[0]}, GPU ${FREE_GPUS[1]})."
    info "GPU ${FREE_GPUS[0]} will run Ollama (LLM). GPU ${FREE_GPUS[1]} can run either image or video generation."
    echo ""
    echo "  Choose generation track for GPU ${FREE_GPUS[1]}:"
    echo "    1) Image generation  (FLUX.1-schnell)"
    echo "    2) Video generation  (AnimateDiff Lightning)"
    echo ""
    while true; do
        read -rp "  Enter choice [1/2]: " _choice || no_input "generation track choice"
        case "$_choice" in
            1)
                PROFILE="image"
                FLUX_GPU=${FREE_GPUS[1]}
                LTX_GPU=${FREE_GPUS[1]}
                ok "2-GPU setup: Ollama (GPU ${OLLAMA_GPU}) + Image generation (GPU ${FLUX_GPU})"
                break
                ;;
            2)
                PROFILE="video"
                FLUX_GPU=${FREE_GPUS[1]}
                LTX_GPU=${FREE_GPUS[1]}
                ok "2-GPU setup: Ollama (GPU ${OLLAMA_GPU}) + Video generation (GPU ${LTX_GPU})"
                break
                ;;
            *)
                error "Please enter 1 or 2."
                ;;
        esac
    done

elif [ "$FREE_GPU_COUNT" -eq 3 ]; then
    info "3 free GPUs detected (GPU ${FREE_GPUS[0]}, GPU ${FREE_GPUS[1]}, GPU ${FREE_GPUS[2]})."
    info "GPU ${FREE_GPUS[0]} = Ollama (LLM). GPU ${FREE_GPUS[1]} and GPU ${FREE_GPUS[2]} can run image and/or video generation."
    echo ""
    echo "  Choose deployment layout:"
    echo "    1) Image only         (FLUX on GPU ${FREE_GPUS[1]}, GPU ${FREE_GPUS[2]} unused)"
    echo "    2) Video only         (AnimateDiff on GPU ${FREE_GPUS[1]}, GPU ${FREE_GPUS[2]} unused)"
    echo "    3) Image + Video      (FLUX on GPU ${FREE_GPUS[1]}, AnimateDiff on GPU ${FREE_GPUS[2]})"
    echo ""
    while true; do
        read -rp "  Enter choice [1/2/3]: " _choice || no_input "deployment layout choice"
        case "$_choice" in
            1)
                PROFILE="image"
                FLUX_GPU=${FREE_GPUS[1]}
                LTX_GPU=${FREE_GPUS[1]}
                ok "3-GPU setup: Ollama (GPU ${OLLAMA_GPU}) + Image generation (GPU ${FLUX_GPU}) — GPU ${FREE_GPUS[2]} unused"
                break
                ;;
            2)
                PROFILE="video"
                FLUX_GPU=${FREE_GPUS[1]}
                LTX_GPU=${FREE_GPUS[1]}
                ok "3-GPU setup: Ollama (GPU ${OLLAMA_GPU}) + Video generation (GPU ${LTX_GPU}) — GPU ${FREE_GPUS[2]} unused"
                break
                ;;
            3)
                PROFILE="image,video"
                FLUX_GPU=${FREE_GPUS[1]}
                LTX_GPU=${FREE_GPUS[2]}
                ok "3-GPU setup: Ollama (GPU ${OLLAMA_GPU}) + Image (GPU ${FLUX_GPU}) + Video (GPU ${LTX_GPU})"
                break
                ;;
            *)
                error "Please enter 1, 2, or 3."
                ;;
        esac
    done

else
    # 4+ free GPUs — parallel image generation on two, video on another
    PROFILE="image,image2,video"
    FLUX_GPU=${FREE_GPUS[1]}
    FLUX_GPU_2=${FREE_GPUS[2]}
    LTX_GPU=${FREE_GPUS[3]}
    if [ "$FREE_GPU_COUNT" -gt 4 ]; then
        ok "4-GPU setup: Ollama (GPU ${OLLAMA_GPU}) + FLUX×2 (GPU ${FLUX_GPU},${FLUX_GPU_2}) + Video (GPU ${LTX_GPU}) — ${FREE_GPUS[*]:4} unused"
    else
        ok "4-GPU setup: Ollama (GPU ${OLLAMA_GPU}) + FLUX×2 (GPU ${FLUX_GPU},${FLUX_GPU_2}) + Video (GPU ${LTX_GPU})"
    fi
fi

echo ""

# =============================================================================
# STEP 3: ENVIRONMENT CONFIGURATION
# =============================================================================
echo -e "${BOLD}[3/4] Environment configuration${NC}"
echo ""

SKIP_ENV=0
if [ -f .env ]; then
    warn ".env already exists."
    read -rp "  Overwrite it? [y/N]: " _ow || _ow="N"
    if [[ ! "${_ow:-N}" =~ ^[Yy]$ ]]; then
        info "Keeping existing .env — updating GPU and profile settings only."
        SKIP_ENV=1
        echo ""
    else
        # Keep the credentials the running data volumes were created with.
        _old_pg=$(old_env_val POSTGRES_PASSWORD)
        _old_ak=$(old_env_val RUSTFS_ACCESS_KEY)
        _old_sk=$(old_env_val RUSTFS_SECRET_KEY)
        _old_oc=$(old_env_val OPENCLAW_AUTH_TOKEN)
        rm .env
    fi
fi

if [ "$SKIP_ENV" -eq 0 ] && [ ! -f .env ]; then
    cp .env.example .env
    echo "  Press Enter to accept the default shown in [brackets]."
    echo ""

    # --- Infrastructure service credentials (written to .env only) ---
    # Random per install instead of fixed, publicly known defaults; reused
    # from the overwritten .env, or kept at the legacy defaults when data
    # volumes already exist, so existing databases still accept them.
    _pg=$(pick_secret "${_old_pg:-}" pgdata postgres "PostgreSQL password")
    set_env POSTGRES_PASSWORD "${_pg}"
    sed -i "s|^APP_DATABASE_URL=.*|APP_DATABASE_URL=postgresql+asyncpg://postgres:${_pg}@postgres:5432/adgen|" .env

    _ak=$(pick_secret "${_old_ak:-}" rustfsdata minioadmin "storage access key")
    _sk=$(pick_secret "${_old_sk:-}" rustfsdata minioadmin "storage secret key")
    set_env RUSTFS_ACCESS_KEY "${_ak}"
    set_env RUSTFS_SECRET_KEY "${_sk}"
    sed -i "s|^APP_MINIO_ACCESS_KEY=.*|APP_MINIO_ACCESS_KEY=${_ak}|" .env
    sed -i "s|^APP_MINIO_SECRET_KEY=.*|APP_MINIO_SECRET_KEY=${_sk}|" .env
    sed -i "s|^APP_MINIO_ENDPOINT=.*|APP_MINIO_ENDPOINT=rustfs:9000|" .env

    # OpenClaw rewrites its config from the seed on every start, so a new
    # token never conflicts with existing data.
    _oc=$(pick_secret "${_old_oc:-}" "" "" "OpenClaw token")
    set_env OPENCLAW_AUTH_TOKEN "${_oc}"
    sed -i "s|^APP_OPENCLAW_API_KEY=.*|APP_OPENCLAW_API_KEY=${_oc}|" .env

    sed -i "s|^APP_LLM_API_KEY=.*|APP_LLM_API_KEY=ollama-no-auth|" .env

    # --- HuggingFace Token (required) ---
    echo -e "  ${BOLD}Secrets${NC}"
    while true; do
        read -rp "  HuggingFace API Token (hf_...): " _hf || no_input "HuggingFace token"
        if [ -n "$_hf" ]; then
            break
        fi
        error "  HF_TOKEN is required to download gated models (FLUX.1) — cannot be empty."
    done
    set_env HF_TOKEN "${_hf}"

    echo ""

    # --- HOST_HOME ---
    _default_home="$USER_HOME"
    read -rp "  Host home directory for model cache [${_default_home}]: " _host_home || _host_home=""
    _host_home="${_host_home:-$_default_home}"
    set_env HOST_HOME "${_host_home}"

    echo ""
    ok ".env written"
    echo ""
fi

# --- Kept .env from an earlier sudo run ---
# Older setup.sh versions defaulted HOST_HOME to /root under sudo. Keeping that
# .env would put the model caches under /root and let model-cache-perms hand
# /root/.cache to APP_UID, so point it back at the sudo user's home. Custom
# HOST_HOME values are left untouched.
if [ "$SKIP_ENV" -eq 1 ] && [ "$USER_HOME" != "$HOME" ]; then
    _kept_home=$(grep '^HOST_HOME=' .env 2>/dev/null | cut -d= -f2 || true)
    if [ "$_kept_home" = "$HOME" ]; then
        set_env HOST_HOME "${USER_HOME}"
        warn "HOST_HOME was ${_kept_home} (root's home, from an earlier sudo run) — changed to ${USER_HOME}."
    fi
fi

# --- Always apply GPU and profile settings ---
info "Applying GPU assignment and deployment profile to .env..."

set_env OLLAMA_GPU_ID "${OLLAMA_GPU}"
set_env FLUX_GPU_ID "${FLUX_GPU}"
if [ "$FLUX_GPU_2" -ge 0 ]; then
    set_env FLUX_GPU_2_ID "${FLUX_GPU_2}"
fi
set_env LTX_VIDEO_GPU_ID "${LTX_GPU}"
set_env RENDER_GID "${RENDER_GID}"
resolve_app_ids
set_env APP_UID "${APP_UID_VAL}"
set_env APP_GID "${APP_GID_VAL}"
set_env COMPOSE_PROFILES "${PROFILE}"

if [ "$FLUX_GPU_2" -ge 0 ]; then
    ok "OLLAMA=${OLLAMA_GPU}, FLUX-1=${FLUX_GPU}, FLUX-2=${FLUX_GPU_2}, LTX-Video=${LTX_GPU}"
else
    ok "OLLAMA=${OLLAMA_GPU}, FLUX=${FLUX_GPU}, LTX-Video=${LTX_GPU}"
fi
ok "COMPOSE_PROFILES=${PROFILE}"
echo ""

# =============================================================================
# STEP 4: BUILD & LAUNCH
# =============================================================================
echo -e "${BOLD}[4/4] Building & starting services...${NC}"
echo ""

info "Building all service images..."
docker compose build && ok "All images built" || die "Docker build failed — check output above."
echo ""

# --- Model cache folders ---
# Create the bind-mounted model caches as the host user before "up". If they
# are missing, the Docker daemon would create them as root. Any root-owned
# leftovers are fixed on every start by the model-cache-perms init service
# (services/model-cache/docker-compose.yml), including plain "docker compose up".
_cache_home=$(grep '^HOST_HOME=' .env 2>/dev/null | cut -d= -f2)
_cache_home="${_cache_home:-$USER_HOME}"
mkdir -p "$_cache_home/.cache/huggingface" "$_cache_home/.cache/miopen" 2>/dev/null \
    || warn "Could not create model cache folders under $_cache_home/.cache (the model-cache-perms service will still fix them)."

info "Starting services (profile: ${PROFILE})..."
docker compose up -d

echo ""
hr
ok "All services started."
hr
echo ""
echo "  Endpoint:"
echo "    UI  →  http://localhost:8080"
echo ""
echo "  Active profile: ${PROFILE}"

if [ "$PROFILE" = "image,image2,video" ]; then
    echo "  Running: Ollama (GPU ${OLLAMA_GPU}) + FLUX×2 parallel image gen (GPU ${FLUX_GPU},${FLUX_GPU_2}) + AnimateDiff video gen (GPU ${LTX_GPU})"
elif [ "$PROFILE" = "image,video" ]; then
    echo "  Running: Ollama (GPU ${OLLAMA_GPU}) + FLUX image gen (GPU ${FLUX_GPU}) + AnimateDiff video gen (GPU ${LTX_GPU})"
elif [ "$PROFILE" = "image" ]; then
    echo "  Running: Ollama (GPU ${OLLAMA_GPU}) + FLUX image gen (GPU ${FLUX_GPU})"
elif [ "$PROFILE" = "video" ]; then
    echo "  Running: Ollama (GPU ${OLLAMA_GPU}) + AnimateDiff video gen (GPU ${LTX_GPU})"
fi

echo ""
echo "  First boot: Ollama downloads the Qwen3 8B model and"
echo "  FLUX/LTX-Video download weights from HuggingFace (~10 GB each)."
echo "  This can take several minutes. Monitor with:"
echo "    docker compose logs -f ollama"

if [[ "$PROFILE" == *"image"* ]]; then
    echo "    docker compose logs -f flux-server"
fi
if [[ "$PROFILE" == *"image2"* ]]; then
    echo "    docker compose logs -f flux-server-2"
fi
if [[ "$PROFILE" == *"video"* ]]; then
    echo "    docker compose logs -f ltx-video"
fi

echo ""
echo "  To stop all services:"
echo "    docker compose --profile image --profile image2 --profile video down"
echo ""
