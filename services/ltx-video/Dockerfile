# Created by Metrum AI for AMD

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

COPY ltx_server.py .

EXPOSE 8004

# nosemgrep: dockerfile.security.missing-user
CMD ["uvicorn", "ltx_server:app", "--host", "0.0.0.0", "--port", "8004"]
