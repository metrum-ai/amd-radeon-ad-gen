# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

FROM rocm/pytorch:rocm7.1.1_ubuntu22.04_py3.11_pytorch_release_2.10.0

WORKDIR /app

# Every package here is pinned to the version this image was tested with: an
# unpinned rebuild once pulled a diffusers release that removed
# pipe.enable_vae_slicing() and crashed the video server, and the Xet
# download / timeout behaviour was verified on huggingface_hub 1.33.0 +
# hf-xet 1.6.0. Bump deliberately and re-test.
RUN pip install --no-cache-dir \
    "diffusers[torch]==0.40.0" \
    "transformers==5.17.0" \
    "accelerate==1.15.0" \
    "peft==0.21.0" \
    "sentencepiece==0.2.2" \
    "protobuf==7.36.2" \
    "safetensors==0.8.0" \
    "huggingface_hub==1.33.0" \
    "hf-xet==1.6.0" \
    "imageio==2.37.4" \
    "imageio-ffmpeg==0.6.0" \
    "fastapi==0.141.1" \
    "uvicorn[standard]==0.54.0" \
    "pydantic==2.13.5"

ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd -g ${APP_GID} appuser 2>/dev/null || true \
    && useradd -m -u ${APP_UID} -g ${APP_GID} appuser \
    && mkdir -p /home/appuser/.cache/huggingface \
                /home/appuser/.cache/miopen \
                /home/appuser/.cache/hip \
                /home/appuser/.cache/torch/hub \
                /home/appuser/.config/miopen \
    && chown -R ${APP_UID}:${APP_GID} /app /home/appuser

COPY --chown=appuser:appuser ltx_server.py .

USER appuser

ENV HOME=/home/appuser

EXPOSE 8004

CMD ["uvicorn", "ltx_server:app", "--host", "0.0.0.0", "--port", "8004"]
