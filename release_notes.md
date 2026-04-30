# Release v1.1

## Updates

* **OpenClaw Integration**: Strategy generation is routed through OpenClaw (OpenAI-compatible gateway) in front of the local Ollama model.
* **Structured JSON Reliability**: Added per-module handling for structured outputs.

---

# Release v1.0

## Features

* **End-to-End Campaign Pipeline**: Automated workflow from brand brief to downloadable campaign package — LLM-driven creative strategy, multi-track asset generation (image, audio, video), brand compositing, and ZIP export, all running locally on AMD Radeon AI PRO R9700S (9700S) GPUs.

* **AI Strategy Generation**: Qwen3 8B LLM via Ollama analyzes brand briefs and produces full creative strategies including positioning direction, audience segmentation with demographics, ad copy variants, scene descriptions, audio scripts, and soundtrack planning.

* **Multi-Track Asset Generation**: Parallel generation across three tracks — display images via FLUX.1-schnell, voiceover audio via Kokoro TTS, and animated video via AnimateDiff Lightning — each on dedicated GPU or CPU resources.

* **Market Data Enrichment**: Optional live market data injection via NewsAPI for trend-aware strategy generation.

* **Real-Time GPU Monitoring**: Collapsible sidebar with live AMD GPU telemetry (compute utilization, VRAM usage, temperature, power draw) alongside CPU and system memory metrics via Prometheus, AMD Device Metrics Exporter, and Node Exporter.

* **Parallel Image Generation**: On 4-GPU AMD Radeon AI PRO R9700S setups, two FLUX.1-schnell instances generate scene images concurrently across GPU 1 and GPU 2, roughly halving image generation time compared to single-GPU sequential generation.

* **Flexible GPU Deployment**: Built and optimized for AMD Radeon AI PRO R9700S (9700S) GPUs, with support for 4-GPU (parallel image + video), 3-GPU, and 2-GPU (image or video) configurations via Docker Compose profiles (`image`, `image2`, `video`) and environment-driven GPU assignment (`OLLAMA_GPU_ID`, `FLUX_GPU_ID`, `FLUX_GPU_2_ID`, `LTX_VIDEO_GPU_ID`).

* **One-Command Deployment**: Fully containerized microservices architecture with Docker Compose orchestration for all services — FastAPI backend, Celery workers, Ollama, FLUX, LTX-Video, Kokoro TTS, PostgreSQL, Valkey, MinIO, Prometheus, and Nginx reverse proxy.

---

## Main User Flow

1. **Create a campaign brief** (brand identity + product + objective + style/tone, optional market data)
2. **Generate strategy** (LLM produces direction, audiences, copy, scenes, and audio plan)
3. **Approve tracks** (image/audio/video based on available hardware)
4. **Run generation** (parallel image/audio/video pipelines)
5. **Composite & export** (brand overlays + downloadable ZIP package)

---

## Architecture & Components

### Infrastructure & Services

| Component | Version | License |
|-----------|---------|---------|
| Nginx | 1.27-alpine | [BSD 2-Clause](https://nginx.org/LICENSE) |
| PostgreSQL | 16-alpine | [PostgreSQL License](https://www.postgresql.org/about/licence/) |
| Valkey | 8-alpine | [BSD 3-Clause](https://github.com/valkey-io/valkey-container/blob/mainline/LICENSE) |
| MinIO | RELEASE.2025-04-08T15-41-24Z | [GNU AGPLv3](https://github.com/minio/minio/blob/RELEASE.2025-03-12T18-04-18Z/LICENSE) |
| Ollama (ROCm) | rocm | [MIT License](https://github.com/ollama/ollama/blob/main/LICENSE) |
| Kokoro FastAPI TTS (CPU) | v0.2.4 | [Apache License 2.0](https://github.com/remsky/Kokoro-FastAPI/blob/master/LICENSE) |
| ROCm PyTorch (FLUX / LTX-Video base) | rocm7.1.1, PyTorch 2.10.0 | [BSD 3-Clause](https://github.com/pytorch/pytorch/blob/main/LICENSE) |
| AMD Device Metrics Exporter | v1.4.2 | [Apache License 2.0](https://github.com/ROCm/device-metrics-exporter/blob/main/LICENSE) |
| Prometheus | v3.3.1 | [Apache License 2.0](https://github.com/prometheus/prometheus/blob/main/LICENSE) |
| Node Exporter | v1.9.1 | [Apache License 2.0](https://github.com/prometheus/node_exporter/blob/master/LICENSE) |
| Python | 3.11-slim | [PSF License](https://docs.python.org/3/license.html) |
| Node.js | 20-alpine | [MIT License](https://github.com/nodejs/node/blob/main/LICENSE) |
| Docker | >=25.0 | [Apache License 2.0](https://github.com/moby/moby/blob/master/LICENSE) |
| Docker Compose | >=v2.0 | [Apache License 2.0](https://github.com/docker/compose/blob/main/LICENSE) |
| fastapi | 0.133.0 | [MIT License](https://github.com/fastapi/fastapi/blob/master/LICENSE) |
| uvicorn[standard] | 0.41.0 | [BSD 3-Clause](https://github.com/encode/uvicorn/blob/master/LICENSE.md) |
| celery[redis] | 5.6.2 | [BSD 3-Clause](https://github.com/celery/celery/blob/main/LICENSE) |
| redis (Python) | 6.4.0 | [MIT License](https://github.com/redis/redis-py/blob/master/LICENSE) |
| sqlalchemy[asyncio] | 2.0.47 | [MIT License](https://github.com/sqlalchemy/sqlalchemy/blob/main/LICENSE) |
| asyncpg | 0.31.0 | [Apache License 2.0](https://github.com/MagicStack/asyncpg/blob/master/LICENSE) |
| pydantic-settings | 2.13.1 | [MIT License](https://pypi.org/project/pydantic-settings/) |
| httpx | 0.28.1 | [BSD 3-Clause](https://github.com/encode/httpx/blob/master/LICENSE.md) |
| minio (Python) | 7.2.20 | [Apache License 2.0](https://github.com/minio/minio-py/blob/master/LICENSE) |
| numpy | 2.4.2 | [BSD 3-Clause](https://numpy.org/doc/stable/license.html) |
| pillow | 12.1.1 | [HPND (MIT-CMU)](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |
| psycopg2-binary | 2.9.11 | [LGPL v2.1+](https://www.psycopg.org/license/) |
| pytesseract | 0.3.13 | [Apache License 2.0](https://github.com/madmaze/pytesseract/blob/master/LICENSE) |
| defusedxml | 0.7.1 | [PSF License](https://github.com/tiran/defusedxml/blob/main/LICENSE) |
| diffusers[torch] | >=0.36.0 | [Apache License 2.0](https://github.com/huggingface/diffusers/blob/main/LICENSE) |
| transformers | latest | [Apache License 2.0](https://github.com/huggingface/transformers/blob/main/LICENSE) |
| accelerate | latest | [Apache License 2.0](https://github.com/huggingface/accelerate/blob/main/LICENSE) |
| peft | latest | [Apache License 2.0](https://pypi.org/project/peft/) |
| sentencepiece | latest | [Apache License 2.0](https://github.com/google/sentencepiece/blob/master/LICENSE) |
| protobuf | latest | [BSD 3-Clause](https://github.com/protocolbuffers/protobuf/blob/master/LICENSE) |
| safetensors | latest | [Apache License 2.0](https://github.com/huggingface/safetensors/blob/main/LICENSE) |
| huggingface_hub | latest | [Apache License 2.0](https://github.com/huggingface/huggingface_hub/blob/main/LICENSE) |
| imageio | latest | [BSD 2-Clause](https://github.com/imageio/imageio/blob/master/LICENSE) |
| imageio-ffmpeg | latest | [BSD 2-Clause](https://github.com/imageio/imageio-ffmpeg/blob/master/LICENSE) |
| react | ^19.0.0 | [MIT License](https://github.com/facebook/react/blob/main/LICENSE) |
| react-dom | ^19.0.0 | [MIT License](https://github.com/facebook/react/blob/main/LICENSE) |
| react-redux | ^9.2.0 | [MIT License](https://github.com/reduxjs/react-redux/blob/master/LICENSE.md) |
| @reduxjs/toolkit | ^2.11.2 | [MIT License](https://github.com/reduxjs/redux-toolkit/blob/master/LICENSE) |
| vite | ^6.0.0 | [MIT License](https://github.com/vitejs/vite/blob/main/LICENSE) |
| @vitejs/plugin-react | ^4.3.0 | [MIT License](https://github.com/vitejs/vite-plugin-react/blob/main/LICENSE) |
| ffmpeg (system) | — | [LGPL v2.1+](https://ffmpeg.org/legal.html) |
| tesseract-ocr (system) | — | [Apache License 2.0](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE) |
