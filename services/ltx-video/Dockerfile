# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

FROM rocm/pytorch:rocm7.1.1_ubuntu22.04_py3.11_pytorch_release_2.10.0

WORKDIR /app

RUN pip install --no-cache-dir \
    "diffusers[torch]>=0.36.0" \
    transformers \
    accelerate \
    peft \
    sentencepiece \
    protobuf \
    safetensors \
    huggingface_hub \
    imageio \
    imageio-ffmpeg \
    fastapi \
    "uvicorn[standard]" \
    pydantic

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
