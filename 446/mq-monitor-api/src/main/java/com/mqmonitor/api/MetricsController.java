package com.mqmonitor.api;

import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.common.model.TimeSeriesPoint;
import com.mqmonitor.collector.MetricsManager;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/metrics")
@CrossOrigin(origins = "*")
public class MetricsController {

    private final MetricsManager metricsManager;

    public MetricsController() {
        this.metricsManager = MetricsManager.getInstance();
    }

    @GetMapping
    public ResponseEntity<Map<String, Object>> getAllMetrics() {
        List<QueueMetrics> metrics = metricsManager.getAllMetrics();
        Map<String, Object> response = new HashMap<>();
        response.put("timestamp", System.currentTimeMillis());
        response.put("count", metrics.size());
        response.put("metrics", metrics);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{cluster}/{topic}")
    public ResponseEntity<List<QueueMetrics>> getMetrics(
            @PathVariable String cluster,
            @PathVariable String topic,
            @RequestParam(required = false) String consumerGroup) {
        List<QueueMetrics> metrics = metricsManager.getMetrics(cluster, topic, consumerGroup);
        return ResponseEntity.ok(metrics);
    }

    @GetMapping("/history/backlog/{cluster}/{topic}")
    public ResponseEntity<List<TimeSeriesPoint>> getBacklogHistory(
            @PathVariable String cluster,
            @PathVariable String topic,
            @RequestParam(required = false) String consumerGroup,
            @RequestParam(defaultValue = "3600000") long startTime,
            @RequestParam(defaultValue = "0") long endTime) {
        if (endTime == 0) {
            endTime = System.currentTimeMillis();
        }
        if (startTime == 3600000) {
            startTime = endTime - 3600000;
        }
        List<TimeSeriesPoint> history = metricsManager.getBacklogHistory(
                cluster, topic, consumerGroup, startTime, endTime);
        return ResponseEntity.ok(history);
    }

    @GetMapping("/history/latency/{cluster}/{topic}")
    public ResponseEntity<List<TimeSeriesPoint>> getLatencyHistory(
            @PathVariable String cluster,
            @PathVariable String topic,
            @RequestParam(required = false) String consumerGroup,
            @RequestParam(defaultValue = "3600000") long startTime,
            @RequestParam(defaultValue = "0") long endTime) {
        if (endTime == 0) {
            endTime = System.currentTimeMillis();
        }
        if (startTime == 3600000) {
            startTime = endTime - 3600000;
        }
        List<TimeSeriesPoint> history = metricsManager.getLatencyHistory(
                cluster, topic, consumerGroup, startTime, endTime);
        return ResponseEntity.ok(history);
    }

    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> getSummary() {
        List<QueueMetrics> allMetrics = metricsManager.getAllMetrics();
        Map<String, Object> summary = new HashMap<>();

        long totalBacklog = 0;
        double avgLatency = 0;
        double totalProduceThroughput = 0;
        double totalConsumeThroughput = 0;
        long maxLatency = 0;
        long maxBacklog = 0;

        for (QueueMetrics m : allMetrics) {
            totalBacklog += m.getBacklogSize();
            avgLatency += m.getEndToEndLatencyMs();
            totalProduceThroughput += m.getProduceThroughput();
            totalConsumeThroughput += m.getConsumeThroughput();
            maxLatency = Math.max(maxLatency, m.getEndToEndLatencyMs());
            maxBacklog = Math.max(maxBacklog, m.getBacklogSize());
        }

        if (!allMetrics.isEmpty()) {
            avgLatency /= allMetrics.size();
        }

        summary.put("totalMonitored", allMetrics.size());
        summary.put("totalBacklog", totalBacklog);
        summary.put("averageLatencyMs", Math.round(avgLatency));
        summary.put("maxLatencyMs", maxLatency);
        summary.put("maxBacklog", maxBacklog);
        summary.put("totalProduceThroughput", Math.round(totalProduceThroughput));
        summary.put("totalConsumeThroughput", Math.round(totalConsumeThroughput));
        summary.put("timestamp", System.currentTimeMillis());

        return ResponseEntity.ok(summary);
    }
}
