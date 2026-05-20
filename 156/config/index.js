module.exports = {
  server: {
    port: process.env.PORT || 3000
  },
  snowflake: {
    epoch: 1609459200000,
    workerIdBits: 10,
    sequenceBits: 12,
    maxWorkerId: -1 ^ (-1 << 10),
    maxSequence: -1 ^ (-1 << 12)
  },
  zookeeper: {
    connectionString: process.env.ZK_CONNECTION || '127.0.0.1:2181',
    sessionTimeout: 30000,
    spinDelay: 1000,
    retries: 5,
    basePath: '/distributed-id-generator',
    workerPath: '/workers'
  },
  segment: {
    defaultStep: 1000,
    nextLoadThreshold: 0.2
  },
  formatter: {
    defaultPrefix: '',
    separator: '_',
    enableTimestamp: true,
    enableChecksum: false
  },
  prefixes: {
    'order': 'ORD',
    'user': 'USR',
    'product': 'PRD',
    'payment': 'PAY',
    'default': 'ID'
  }
};