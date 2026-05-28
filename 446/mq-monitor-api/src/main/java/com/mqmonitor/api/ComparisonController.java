package com.mqmonitor.api;

import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.ConsumerGroupComparison;
import com.mqmonitor.comparison.ConsumerGroupComparator;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/comparison")
@CrossOrigin(origins = "*")
public class ComparisonController {

    private final ConsumerGroupComparator comparator;

    public ComparisonController() {
        this.comparator = new ConsumerGroupComparator();
    }

    @PostMapping("/{mqType}/{cluster}/{topic}")
    public ResponseEntity<ConsumerGroupComparison> compareConsumerGroups(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @RequestBody List<String> consumerGroups) {
        ConsumerGroupComparison comparison = comparator.compareConsumerGroups(
                mqType, cluster, topic, consumerGroups);
        return ResponseEntity.ok(comparison);
    }

    @GetMapping("/{mqType}/{cluster}")
    public ResponseEntity<List<ConsumerGroupComparison>> compareAllTopics(
            @PathVariable MQType mqType,
            @PathVariable String cluster) {
        List<ConsumerGroupComparison> comparisons = comparator.compareAllTopics(mqType, cluster);
        return ResponseEntity.ok(comparisons);
    }

    @PostMapping("/summary/{mqType}/{cluster}/{topic}")
    public ResponseEntity<Map<String, Object>> getComparisonSummary(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @RequestBody List<String> consumerGroups) {
        ConsumerGroupComparison comparison = comparator.compareConsumerGroups(
                mqType, cluster, topic, consumerGroups);
        Map<String, Object> summary = comparator.getComparisonSummary(comparison);
        return ResponseEntity.ok(summary);
    }
}
