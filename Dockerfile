# Multi-stage build: build toolchain never reaches the runtime image
FROM python:3.11-slim AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY trendscope/ ./trendscope/

RUN pip install --no-cache-dir --prefix=/install .

# --- runtime ---
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from build stage (no compilers, no pip cache)
COPY --from=build /install /usr/local

COPY pyproject.toml README.md ./
COPY trendscope/ ./trendscope/

RUN useradd -m -u 1000 trendscope \
    && mkdir -p /app/data \
    && chown -R trendscope:trendscope /app

USER trendscope

ENV API_HOST=0.0.0.0 \
    DATA_DIR=/app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

CMD ["trendscope-api"]
