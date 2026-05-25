FROM ubuntu:20.04

LABEL maintainer="developer@example.com"

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        git \
        curl && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY src/ ./src/

CMD ["python3", "app.py"]
