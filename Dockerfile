# CostDNA — multi-stage build for a slim CPU-only image.
#
# Final image is ~2GB, runs the full CLI with semantic features.
# To use:  docker run --rm -v ~/.aws:/root/.aws pauti04/costdna scan --aws-profile prod
# Smoke:   docker run --rm pauti04/costdna scan --synthetic --epochs 50
#
# The sentence-transformer model is downloaded at build time and embedded so
# first-run is instant.

FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc g++ \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install CPU-only torch first to avoid pulling CUDA wheels (huge).
RUN pip install --upgrade pip \
 && pip install torch --index-url https://download.pytorch.org/whl/cpu

# Now install the rest from pyproject.toml.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[viz,ui]"

# Pre-download the sentence-transformer model so first run is instant.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface \
    PYTHONPATH=/app/src

# Copy installed deps + the model cache from the builder.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

WORKDIR /app
COPY src ./src
COPY README.md LICENSE ./

ENTRYPOINT ["costdna"]
CMD ["--help"]
