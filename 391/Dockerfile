FROM apache/airflow:2.8.0-python3.10

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

ENV PYTHONPATH="/opt/airflow:${PYTHONPATH}"
