FROM python:3.11-slim

WORKDIR /app

# System dependencies for compilation and scraping libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy metadata and source
COPY pyproject.toml README.md ./
COPY trendscope/ ./trendscope/

# Install package with dev dependencies for testing
RUN pip install --no-cache-dir -e ".[dev]"

# Create non-root user and data directory
RUN useradd -m -u 1000 trendscope && mkdir -p /app/data && chown -R trendscope:trendscope /app
USER trendscope

EXPOSE 8000

CMD ["trendscope-api"]
