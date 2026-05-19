const { Kafka, Partitioners } = require('kafkajs');
require('dotenv').config();

const brokers = process.env.KAFKA_BROKERS.split(',');

const kafka = new Kafka({
  clientId: process.env.KAFKA_CLIENT_ID || 'shortlink-analytics',
  brokers: brokers,
  retry: {
    retries: 5,
    initialRetryTime: 300,
    factor: 0.2,
    multiplier: 2,
    maxRetryTime: 30000
  }
});

const producer = kafka.producer({
  createPartitioner: Partitioners.LegacyPartitioner,
  allowAutoTopicCreation: true,
  transactionTimeout: 30000
});

const consumer = kafka.consumer({
  groupId: process.env.KAFKA_GROUP_ID || 'clickhouse-consumer',
  allowAutoTopicCreation: true
});

const flinkConsumer = kafka.consumer({
  groupId: process.env.KAFKA_FLINK_GROUP_ID || 'flink-aggregator',
  allowAutoTopicCreation: true
});

const initProducer = async () => {
  try {
    await producer.connect();
    console.log('Kafka Producer connected successfully');
  } catch (error) {
    console.error('Kafka Producer connection error:', error);
    throw error;
  }
};

const initConsumer = async (topics) => {
  try {
    await consumer.connect();
    await consumer.subscribe({ topics, fromBeginning: false });
    console.log(`Kafka Consumer connected and subscribed to: ${topics.join(', ')}`);
  } catch (error) {
    console.error('Kafka Consumer connection error:', error);
    throw error;
  }
};

const initFlinkConsumer = async (topics) => {
  try {
    await flinkConsumer.connect();
    await flinkConsumer.subscribe({ topics, fromBeginning: false });
    console.log(`Kafka Flink Consumer connected and subscribed to: ${topics.join(', ')}`);
  } catch (error) {
    console.error('Kafka Flink Consumer connection error:', error);
    throw error;
  }
};

const sendHeatmapClick = async (data) => {
  try {
    const key = data.fingerprint || data.sessionId || 'default';
    await producer.send({
      topic: process.env.KAFKA_TOPIC_HEATMAP || 'heatmap-clicks',
      messages: [
        {
          key: key,
          value: JSON.stringify({
            ...data,
            _producerTimestamp: Date.now(),
            _kafkaPartition: 0
          })
        }
      ]
    });
    return true;
  } catch (error) {
    console.error('Kafka send heatmap click error:', error);
    return false;
  }
};

const sendAccessLog = async (data) => {
  try {
    const key = data.shortCode || 'default';
    await producer.send({
      topic: process.env.KAFKA_TOPIC_ACCESS || 'access-logs',
      messages: [
        {
          key: key,
          value: JSON.stringify({
            ...data,
            _producerTimestamp: Date.now()
          })
        }
      ]
    });
    return true;
  } catch (error) {
    console.error('Kafka send access log error:', error);
    return false;
  }
};

const disconnectProducer = async () => {
  await producer.disconnect();
  console.log('Kafka Producer disconnected');
};

const disconnectConsumer = async () => {
  await consumer.disconnect();
  console.log('Kafka Consumer disconnected');
};

const disconnectFlinkConsumer = async () => {
  await flinkConsumer.disconnect();
  console.log('Kafka Flink Consumer disconnected');
};

module.exports = {
  kafka,
  producer,
  consumer,
  flinkConsumer,
  initProducer,
  initConsumer,
  initFlinkConsumer,
  sendHeatmapClick,
  sendAccessLog,
  disconnectProducer,
  disconnectConsumer,
  disconnectFlinkConsumer
};
