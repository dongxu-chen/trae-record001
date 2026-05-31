FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        TRIVY_ARCH="Linux-64bit"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        TRIVY_ARCH="Linux-ARM64"; \
    else \
        TRIVY_ARCH="Linux-64bit"; \
    fi && \
    wget -q https://github.com/aquasecurity/trivy/releases/download/v0.47.0/trivy_0.47.0_${TRIVY_ARCH}.tar.gz && \
    tar -xzf trivy_*.tar.gz && \
    mv trivy /usr/local/bin/ && \
    rm -rf trivy_*

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin/trivy /usr/local/bin/trivy

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN trivy --version

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
