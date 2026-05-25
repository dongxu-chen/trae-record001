#!/bin/bash

FLINK_HOME="${FLINK_HOME:-/opt/flink}"
JOB_JAR="${JOB_JAR:-tracking-flink-1.0.0.jar}"
JOB_MANAGER="${JOB_MANAGER:-localhost:8081}"

KAFKA_BROKERS="${KAFKA_BROKERS:-localhost:9092}"
KAFKA_GROUP_ID="${KAFKA_GROUP_ID:-tracking_flink_group}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-localhost}"
CLICKHOUSE_PORT="${CLICKHOUSE_PORT:-8123}"
CLICKHOUSE_DB="${CLICKHOUSE_DB:-tracking}"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-default}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-}"
SESSION_TIMEOUT="${SESSION_TIMEOUT:-1800000}"

echo "Submitting Flink job..."
echo "Kafka brokers: $KAFKA_BROKERS"
echo "Redis host: $REDIS_HOST:$REDIS_PORT"
echo "ClickHouse host: $CLICKHOUSE_HOST:$CLICKHOUSE_PORT"
echo "Session timeout: $SESSION_TIMEOUT ms"

$FLINK_HOME/bin/flink run \
    -m $JOB_MANAGER \
    -c com.tracking.flink.TrackingFlinkJob \
    -p 4 \
    $JOB_JAR \
    --kafka.brokers $KAFKA_BROKERS \
    --kafka.group.id $KAFKA_GROUP_ID \
    --redis.host $REDIS_HOST \
    --redis.port $REDIS_PORT \
    --redis.password "$REDIS_PASSWORD" \
    --clickhouse.host $CLICKHOUSE_HOST \
    --clickhouse.port $CLICKHOUSE_PORT \
    --clickhouse.database $CLICKHOUSE_DB \
    --clickhouse.username $CLICKHOUSE_USER \
    --clickhouse.password "$CLICKHOUSE_PASSWORD" \
    --session.timeout.ms $SESSION_TIMEOUT

echo "Flink job submitted!"
