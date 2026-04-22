#!/usr/bin/env bash
# Created by Metrum AI for AMD

# =============================================================================
# AI Ad Generator — Setup & Launch
# Checks prerequisites, configures environment, detects GPUs, and starts services.
# =============================================================================
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
    GPU_COUNT=$(rocm-smi --showid 2>/dev/null | grep -o "GPU\[[0-9]*\]" | sort -u | wc -l)
    GPU_COUNT=${GPU_COUNT:-0}
    if [ "$GPU_COUNT" -eq 0 ]; then
        GPU_COUNT=$(rocm-smi -i 2>/dev/null | grep -o "GPU\[[0-9]*\]" | sort -u | wc -l)
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
if [ ! -e /dev/kfd ]; then
    error "/dev/kfd not found — ROCm kernel driver not loaded"
    PREREQ_FAIL=1
elif [ ! -d /dev/dri ]; then
    error "/dev/dri not found — DRM subsystem not available"
    PREREQ_FAIL=1
else
    ok "ROCm device nodes (/dev/kfd, /dev/dri)"
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
_cache_home="$HOME"
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

PROFILE=""
OLLAMA_GPU=0
FLUX_GPU=1
FLUX_GPU_2=-1
LTX_GPU=3

if [ "$GPU_COUNT" -eq 2 ]; then
    info "2 AMD GPUs detected."
    info "GPU 0 will run Ollama (LLM). GPU 1 can run either image or video generation."
    echo ""
    echo "  Choose generation track for GPU 1:"
    echo "    1) Image generation  (FLUX.1-schnell)"
    echo "    2) Video generation  (AnimateDiff Lightning)"
    echo ""
    while true; do
        read -rp "  Enter choice [1/2]: " _choice || _choice=""
        case "$_choice" in
            1)
                PROFILE="image"
                FLUX_GPU=1
                LTX_GPU=1
                ok "2-GPU setup: Ollama (GPU 0) + Image generation (GPU 1)"
                break
                ;;
            2)
                PROFILE="video"
                FLUX_GPU=1
                LTX_GPU=1
                ok "2-GPU setup: Ollama (GPU 0) + Video generation (GPU 1)"
                break
                ;;
            *)
                error "Please enter 1 or 2."
                ;;
        esac
    done

elif [ "$GPU_COUNT" -eq 3 ]; then
    info "3 AMD GPUs detected."
    info "GPU 0 = Ollama (LLM). GPU 1 and GPU 2 can run image and/or video generation."
    echo ""
    echo "  Choose deployment layout:"
    echo "    1) Image only         (FLUX on GPU 1, GPU 2 unused)"
    echo "    2) Video only         (AnimateDiff on GPU 1, GPU 2 unused)"
    echo "    3) Image + Video      (FLUX on GPU 1, AnimateDiff on GPU 2)"
    echo ""
    while true; do
        read -rp "  Enter choice [1/2/3]: " _choice || _choice=""
        case "$_choice" in
            1)
                PROFILE="image"
                FLUX_GPU=1
                LTX_GPU=1
                ok "3-GPU setup: Ollama (GPU 0) + Image generation (GPU 1) — GPU 2 unused"
                break
                ;;
            2)
                PROFILE="video"
                FLUX_GPU=1
                LTX_GPU=1
                ok "3-GPU setup: Ollama (GPU 0) + Video generation (GPU 1) — GPU 2 unused"
                break
                ;;
            3)
                PROFILE="image,video"
                FLUX_GPU=1
                LTX_GPU=2
                ok "3-GPU setup: Ollama (GPU 0) + Image (GPU 1) + Video (GPU 2)"
                break
                ;;
            *)
                error "Please enter 1, 2, or 3."
                ;;
        esac
    done

else
    # 4+ GPUs — parallel image generation on GPU 1 & 2, video on GPU 3
    PROFILE="image,image2,video"
    FLUX_GPU=1
    FLUX_GPU_2=2
    LTX_GPU=3
    if [ "$GPU_COUNT" -gt 4 ]; then
        ok "4-GPU setup: Ollama (GPU 0) + FLUX×2 (GPU 1,2) + Video (GPU 3) — GPUs 4-$((GPU_COUNT - 1)) unused"
    else
        ok "4-GPU setup: Ollama (GPU 0) + FLUX×2 (GPU 1,2) + Video (GPU 3)"
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
        rm .env
    fi
fi

if [ "$SKIP_ENV" -eq 0 ] && [ ! -f .env ]; then
    cp .env.example .env
    echo "  Press Enter to accept the default shown in [brackets]."
    echo ""

    # --- Core service credentials/URLs (written by setup) ---
    # Keep these in .env (not .env.example) so defaults aren't committed as examples.
    sed -i "s|^APP_DATABASE_URL=.*|APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/adgen|" .env
    sed -i "s|^APP_MINIO_ACCESS_KEY=.*|APP_MINIO_ACCESS_KEY=minioadmin|" .env
    sed -i "s|^APP_MINIO_SECRET_KEY=.*|APP_MINIO_SECRET_KEY=minioadmin|" .env

    # --- HuggingFace Token (required) ---
    echo -e "  ${BOLD}Secrets${NC}"
    while true; do
        read -rp "  HuggingFace API Token (hf_...): " _hf || _hf=""
        if [ -n "$_hf" ]; then
            break
        fi
        error "  HF_TOKEN is required to download gated models (FLUX.1) — cannot be empty."
    done
    sed -i "s|HF_TOKEN=.*|HF_TOKEN=${_hf}|" .env

    echo ""

    # --- NewsAPI Token (optional) ---
    echo -e "  ${BOLD}Market Data (optional)${NC}"
    read -rp "  NewsAPI key for market data enrichment [skip]: " _newsapi || _newsapi=""
    if [ -n "$_newsapi" ] && [ "$_newsapi" != "skip" ]; then
        sed -i "s|APP_NEWSAPI_KEY=.*|APP_NEWSAPI_KEY=${_newsapi}|" .env
        ok "NewsAPI key configured"
    else
        info "Skipping NewsAPI — market data enrichment will be unavailable."
    fi

    echo ""

    # --- HOST_HOME ---
    _default_home="$HOME"
    read -rp "  Host home directory for model cache [${_default_home}]: " _host_home || _host_home=""
    _host_home="${_host_home:-$_default_home}"
    sed -i "s|HOST_HOME=.*|HOST_HOME=${_host_home}|" .env

    echo ""
    ok ".env written"
    echo ""
fi

# --- Always apply GPU and profile settings ---
info "Applying GPU assignment and deployment profile to .env..."

sed -i "s|^OLLAMA_GPU_ID=.*|OLLAMA_GPU_ID=${OLLAMA_GPU}|" .env
sed -i "s|^FLUX_GPU_ID=.*|FLUX_GPU_ID=${FLUX_GPU}|" .env
if [ "$FLUX_GPU_2" -ge 0 ]; then
    sed -i "s|^FLUX_GPU_2_ID=.*|FLUX_GPU_2_ID=${FLUX_GPU_2}|" .env
fi
sed -i "s|^LTX_VIDEO_GPU_ID=.*|LTX_VIDEO_GPU_ID=${LTX_GPU}|" .env
sed -i "s|^COMPOSE_PROFILES=.*|COMPOSE_PROFILES=${PROFILE}|" .env

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
