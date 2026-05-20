FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY fastapi_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fastapi_app/ /app/fastapi_app/

RUN useradd -m appuser
USER appuser

EXPOSE 5000

CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
