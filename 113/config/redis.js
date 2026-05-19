const redis = require('redis');
require('dotenv').config();

const client = redis.createClient({
  url: process.env.REDIS_PASSWORD 
    ? `redis://:${process.env.REDIS_PASSWORD}@${process.env.REDIS_HOST}:${process.env.REDIS_PORT}`
    : `redis://${process.env.REDIS_HOST}:${process.env.REDIS_PORT}`
});

client.on('error', (err) => console.error('Redis Client Error', err));
client.on('connect', () => console.log('Redis connected successfully'));

(async () => {
  await client.connect();
})();

module.exports = client;