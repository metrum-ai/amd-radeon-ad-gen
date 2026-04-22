# Created by Metrum AI for AMD

FROM rocm/pytorch:rocm7.1.1_ubuntu22.04_py3.11_pytorch_release_2.10.0

WORKDIR /app

RUN pip install --no-cache-dir \
    diffusers[torch] \
    transformers \
    accelerate \
    sentencepiece \
    protobuf \
    safetensors \
    fastapi \
    uvicorn[standard] \
    pydantic

COPY flux_server.py .

EXPOSE 8002

# nosemgrep: dockerfile.security.missing-user
CMD ["uvicorn", "flux_server:app", "--host", "0.0.0.0", "--port", "8002"]
