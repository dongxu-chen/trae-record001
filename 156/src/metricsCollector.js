const { Histogram, Counter, Gauge, collectDefaultMetrics, register } = require('prom-client');

class MetricsCollector {
  constructor() {
    this.collectors = new Map();
    
    this.registerMetrics();
    
    collectDefaultMetrics({
      prefix: 'leaf_id_generator_',
      gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5]
    });
  }

  registerMetrics() {
    this.idGeneratedCounter = new Counter({
      name: 'leaf_id_generator_ids_generated_total',
      help: 'Total number of IDs generated',
      labelNames: ['bizTag']
    });

    this.idLatencyHistogram = new Histogram({
      name: 'leaf_id_generator_id_latency_seconds',
      help: 'Latency of ID generation',
      labelNames: ['bizTag'],
      buckets: [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1]
    });

    this.segmentLoadCounter = new Counter({
      name: 'leaf_id_generator_segment_loads_total',
      help: 'Total number of segment loads',
      labelNames: ['bizTag']
    });

    this.segmentSwitchCounter = new Counter({
      name: 'leaf_id_generator_segment_switches_total',
      help: 'Total number of segment switches',
      labelNames: ['bizTag']
    });

    this.segmentLoadErrorCounter = new Counter({
      name: 'leaf_id_generator_segment_load_errors_total',
      help: 'Total number of segment load errors',
      labelNames: ['bizTag']
    });

    this.segmentRemainingGauge = new Gauge({
      name: 'leaf_id_generator_segment_remaining_ids',
      help: 'Remaining IDs in current segment',
      labelNames: ['bizTag']
    });

    this.requestCounter = new Counter({
      name: 'leaf_id_generator_http_requests_total',
      help: 'Total number of HTTP requests',
      labelNames: ['method', 'path', 'status']
    });

    this.requestLatencyHistogram = new Histogram({
      name: 'leaf_id_generator_http_request_latency_seconds',
      help: 'HTTP request latency',
      labelNames: ['method', 'path'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5]
    });

    this.zkConnectionGauge = new Gauge({
      name: 'leaf_id_generator_zk_connection_status',
      help: 'ZooKeeper connection status (1=connected, 0=disconnected)'
    });
  }

  recordIdGenerated(bizTag, latencyMs) {
    this.idGeneratedCounter.labels(bizTag).inc();
    this.idLatencyHistogram.labels(bizTag).observe(latencyMs / 1000);
  }

  recordSegmentLoad(bizTag) {
    this.segmentLoadCounter.labels(bizTag).inc();
  }

  recordSegmentSwitch(bizTag) {
    this.segmentSwitchCounter.labels(bizTag).inc();
  }

  recordSegmentLoadError(bizTag) {
    this.segmentLoadErrorCounter.labels(bizTag).inc();
  }

  recordSegmentRemaining(bizTag, remaining) {
    this.segmentRemainingGauge.labels(bizTag).set(remaining);
  }

  recordHttpRequest(method, path, status, latencyMs) {
    this.requestCounter.labels(method, path, status).inc();
    this.requestLatencyHistogram.labels(method, path).observe(latencyMs / 1000);
  }

  setZkConnectionStatus(connected) {
    this.zkConnectionGauge.set(connected ? 1 : 0);
  }

  async getMetrics() {
    return register.metrics();
  }

  getContentType() {
    return register.contentType;
  }

  getMetricsJSON() {
    const metrics = register.getMetricsAsJSON();
    return {
      timestamp: Date.now(),
      metrics: metrics.map(m => ({
        name: m.name,
        help: m.help,
        type: m.type,
        values: m.values.map(v => ({
          labels: v.labels,
          value: v.value,
          timestamp: v.timestamp
        }))
      }))
    };
  }

  getQPSStats() {
    const metrics = register.getMetricsAsJSON();
    const idMetric = metrics.find(m => m.name === 'leaf_id_generator_ids_generated_total');
    
    if (!idMetric) return null;

    const stats = {};
    for (const value of idMetric.values) {
      const bizTag = value.labels.bizTag || 'total';
      stats[bizTag] = {
        total: value.value,
        timestamp: value.timestamp
      };
    }

    return stats;
  }
}

module.exports = MetricsCollector;