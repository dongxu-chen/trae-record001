#!/bin/bash

KAFKA_HOME="${KAFKA_HOME:-/opt/kafka}"
BOOTSTRAP_SERVERS="${BOOTSTRAP_SERVERS:-localhost:9092}"
ZK_SERVERS="${ZK_SERVERS:-localhost:2181}"

echo "Creating Kafka topics..."

create_topic() {
    local topic=$1
    local partitions=${2:-6}
    local replication=${3:-1}
    local retention=${4:-259200000}

    echo "Creating topic: $topic (partitions=$partitions, replication=$replication, retention=$retention ms)"

    $KAFKA_HOME/bin/kafka-topics.sh --create \
        --zookeeper $ZK_SERVERS \
        --topic $topic \
        --partitions $partitions \
        --replication-factor $replication \
        --config retention.ms=$retention \
        --if-not-exists
}

create_topic "tracking_raw_events" 6 1 259200000
create_topic "tracking_cleaned_events" 6 1 259200000
create_topic "tracking_session_events" 6 1 259200000

echo "Listing topics..."
$KAFKA_HOME/bin/kafka-topics.sh --list --zookeeper $ZK_SERVERS

echo "Kafka topics created successfully!"
