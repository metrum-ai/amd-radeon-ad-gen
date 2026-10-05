# Release v1.5

## Updates

* **Setup Works When Run as Root or with sudo**: Running the setup script as root or with sudo no longer breaks the build. The image and video services are now always set up to run as a regular (non-root) user, and model downloads are kept in that user's home folder.


---

# Release v1.4

## Updates

* **Model Cache Ownership Handling**: A one-shot `model-cache-perms` init service now creates the Hugging Face and MIOpen cache folders and sets their ownership to the host user before the FLUX and video services start, so they can write to the cache on a fresh machine.

* **Pinned Model Library Versions**: The video service now calls `pipe.vae.enable_slicing()` for compatibility with diffusers 0.40, and all Python packages in the FLUX and video images are pinned to tested versions.

* **OpenClaw Startup Independent of Model Download**: OpenClaw now waits for Ollama to start rather than to become healthy, the `qwen3:8b` pull retries until it succeeds, and the Ollama health window is extended to 4 hours, so the UI comes up while the model is still downloading on slower connections.

---

# Release v1.3

## Features

* **End-to-End Campaign Pipeline**: Automated workflow from brand brief to downloadable campaign package — LLM-driven creative strategy, multi-track asset generation (image, audio, video), brand compositing, and ZIP export, all running locally on AMD Radeon AI PRO R9700S (9700S) GPUs.

* **AI Strategy Generation**: Qwen3 8B LLM (via OpenClaw gateway and Ollama) analyzes brand briefs and produces full creative strategies — positioning, audience segmentation, ad copy, scene descriptions, and audio scripts — with structured JSON output handling per module.

* **Multi-Track Asset Generation**: Parallel generation across three tracks — display images via FLUX.1-schnell, voiceover audio via Kokoro TTS, and animated video via AnimateDiff Lightning — each on dedicated GPU or CPU resources.

* **Real-Time GPU Monitoring**: Collapsible sidebar with live AMD GPU telemetry (compute utilization, VRAM usage, temperature, power draw) alongside CPU and system memory metrics via Prometheus, AMD Device Metrics Exporter, and Node Exporter.

* **Parallel Image Generation**: On 4-GPU AMD Radeon AI PRO R9700S setups, two FLUX.1-schnell instances generate scene images concurrently across GPU 1 and GPU 2, roughly halving image generation time compared to single-GPU sequential generation.

* **Flexible GPU Deployment**: Built and optimized for AMD Radeon AI PRO R9700S (9700S) GPUs, with support for 4-GPU (parallel image + video), 3-GPU, and 2-GPU (image or video) configurations via Docker Compose profiles (`image`, `image2`, `video`) and environment-driven GPU assignment (`OLLAMA_GPU_ID`, `FLUX_GPU_ID`, `FLUX_GPU_2_ID`, `LTX_VIDEO_GPU_ID`).

* **One-Command Deployment**: Fully containerized microservices architecture with Docker Compose orchestration for all services — FastAPI backend, Celery workers, Ollama, FLUX, LTX-Video, Kokoro TTS, PostgreSQL, Valkey, RustFS, Prometheus, and Nginx reverse proxy.

* **Dynamic Free-GPU Allocation**: `setup.sh` probes each AMD GPU for active compute processes and assigns only free GPUs to services. Enables deployment on shared servers where some GPUs are already in use.

* **Compliance and Security Hardening**: Resolved high-severity vulnerability findings. Added SPDX copyright headers to all source files.

---

## Main User Flow

1. **Create a campaign brief** (brand identity + product + objective + style/tone)
2. **Generate strategy** (LLM produces direction, audiences, copy, scenes, and audio plan)
3. **Approve tracks** (image/audio/video based on available hardware)
4. **Run generation** (parallel image/audio/video pipelines)
5. **Composite & export** (brand overlays + downloadable ZIP package)

---

## Architecture & Components

### Infrastructure & Services

| Component | Version | License |
|-----------|---------|---------|
| Nginx (reverse proxy) | 1.27-alpine | [BSD-2-Clause](https://nginx.org/LICENSE) |
| Nginx (frontend container) | stable-alpine | [BSD-2-Clause](https://nginx.org/LICENSE) |
| PostgreSQL | 16-alpine | [PostgreSQL](https://www.postgresql.org/about/licence/) |
| Valkey | 8-alpine | [BSD-3-Clause](https://github.com/valkey-io/valkey-container/blob/mainline/LICENSE) |
| RustFS | latest (1.0.0-beta) | [Apache-2.0](https://github.com/rustfs/rustfs/blob/main/LICENSE) |
| Ollama (ROCm) | rocm | [MIT](https://github.com/ollama/ollama/blob/main/LICENSE) |
| OpenClaw | latest | [MIT](https://github.com/openclaw/openclaw/blob/main/LICENSE) |
| Kokoro FastAPI TTS (CPU) | v0.2.4 | [Apache-2.0](https://github.com/remsky/Kokoro-FastAPI/blob/master/LICENSE) |
| ROCm PyTorch (FLUX / LTX-Video base) | rocm7.1.1, PyTorch 2.10.0 | [BSD-3-Clause](https://github.com/pytorch/pytorch/blob/main/LICENSE) |
| AMD Device Metrics Exporter | v1.4.2 | [Apache-2.0](https://github.com/ROCm/device-metrics-exporter/blob/main/LICENSE) |
| Prometheus | v3.3.1 | [Apache-2.0](https://github.com/prometheus/prometheus/blob/main/LICENSE) |
| Node Exporter | v1.9.1 | [Apache-2.0](https://github.com/prometheus/node_exporter/blob/master/LICENSE) |
| Python | 3.11-slim | [PSF-2.0](https://docs.python.org/3/license.html) |
| Node.js | 20-alpine | [MIT](https://github.com/nodejs/node/blob/main/LICENSE) |
| Docker | >=25.0 | [Apache-2.0](https://github.com/moby/moby/blob/master/LICENSE) |
| Docker Compose | >=v2.0 | [Apache-2.0](https://github.com/docker/compose/blob/main/LICENSE) |
| fastapi | 0.133.0 | [MIT](https://github.com/fastapi/fastapi/blob/master/LICENSE) |
| uvicorn[standard] | 0.41.0 | [BSD-3-Clause](https://github.com/encode/uvicorn/blob/master/LICENSE.md) |
| celery[redis] | 5.6.2 | [BSD-3-Clause](https://github.com/celery/celery/blob/main/LICENSE) |
| redis (Python) | 6.4.0 | [MIT](https://github.com/redis/redis-py/blob/master/LICENSE) |
| sqlalchemy[asyncio] | 2.0.47 | [MIT](https://github.com/sqlalchemy/sqlalchemy/blob/main/LICENSE) |
| asyncpg | 0.31.0 | [Apache-2.0](https://github.com/MagicStack/asyncpg/blob/master/LICENSE) |
| pydantic-settings | 2.13.1 | [MIT](https://github.com/pydantic/pydantic-settings/blob/main/LICENSE) |
| httpx | 0.28.1 | [BSD-3-Clause](https://github.com/encode/httpx/blob/master/LICENSE.md) |
| minio (Python SDK) | 7.2.20 | [Apache-2.0](https://github.com/minio/minio-py/blob/master/LICENSE) |
| numpy | 2.4.2 | [BSD-3-Clause](https://numpy.org/doc/stable/license.html) |
| pillow | 12.2.0 | [MIT-CMU](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |
| psycopg | 3.2.9 | [LGPL-3.0-only](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt) |
| pytesseract | 0.3.13 | [Apache-2.0](https://github.com/madmaze/pytesseract/blob/master/LICENSE) |
| defusedxml | 0.7.1 | [PSF-2.0](https://github.com/tiran/defusedxml/blob/main/LICENSE) |
| diffusers[torch] | >=0.36.0 | [Apache-2.0](https://github.com/huggingface/diffusers/blob/main/LICENSE) |
| transformers | latest | [Apache-2.0](https://github.com/huggingface/transformers/blob/main/LICENSE) |
| accelerate | latest | [Apache-2.0](https://github.com/huggingface/accelerate/blob/main/LICENSE) |
| peft | latest | [Apache-2.0](https://github.com/huggingface/peft/blob/main/LICENSE) |
| sentencepiece | latest | [Apache-2.0](https://github.com/google/sentencepiece/blob/master/LICENSE) |
| protobuf | latest | [BSD-3-Clause](https://github.com/protocolbuffers/protobuf/blob/master/LICENSE) |
| safetensors | latest | [Apache-2.0](https://github.com/huggingface/safetensors/blob/main/LICENSE) |
| huggingface_hub | latest | [Apache-2.0](https://github.com/huggingface/huggingface_hub/blob/main/LICENSE) |
| imageio | latest | [BSD-2-Clause](https://github.com/imageio/imageio/blob/master/LICENSE) |
| imageio-ffmpeg | latest | [BSD-2-Clause](https://github.com/imageio/imageio-ffmpeg/blob/master/LICENSE) |
| react | ^19.0.0 | [MIT](https://github.com/facebook/react/blob/main/LICENSE) |
| react-dom | ^19.0.0 | [MIT](https://github.com/facebook/react/blob/main/LICENSE) |
| react-redux | ^9.2.0 | [MIT](https://github.com/reduxjs/react-redux/blob/master/LICENSE.md) |
| @reduxjs/toolkit | ^2.11.2 | [MIT](https://github.com/reduxjs/redux-toolkit/blob/master/LICENSE) |
| vite | ^6.0.0 | [MIT](https://github.com/vitejs/vite/blob/main/LICENSE) |
| @vitejs/plugin-react | ^4.3.0 | [MIT](https://github.com/vitejs/vite-plugin-react/blob/main/LICENSE) |
| ffmpeg (system) | — | [LGPL-2.1-or-later](https://ffmpeg.org/legal.html) |
| tesseract-ocr (system) | — | [Apache-2.0](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE) |

### AI/ML Models (Runtime-Fetched)

| Model | Provider | License |
|-------|----------|---------|
| FLUX.1-schnell | Black Forest Labs | [Apache-2.0](https://github.com/black-forest-labs/flux/blob/main/model_licenses/LICENSE-FLUX1-schnell) |
| AnimateDiff-Lightning | ByteDance | [LicenseRef-CreativeML-OpenRAIL-M](https://huggingface.co/ByteDance/AnimateDiff-Lightning/blob/main/LICENSE.md) |
| DreamShaper | Lykon | [LicenseRef-CreativeML-OpenRAIL-M](https://huggingface.co/spaces/CompVis/stable-diffusion-license) |
| AnimateDiff Motion LoRA | guoyww | [Apache-2.0](https://github.com/guoyww/AnimateDiff/blob/main/LICENSE.txt) |
| Qwen3 8B | Alibaba Cloud (Qwen) | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE) |
| Kokoro-82M TTS | hexgrad | [Apache-2.0](https://github.com/hexgrad/kokoro/blob/main/LICENSE) |

