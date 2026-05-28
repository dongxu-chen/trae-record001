package com.dbpool.optimizer.controller;

import com.dbpool.optimizer.core.ConnectionPoolSimulator;
import com.dbpool.optimizer.core.PoolOptimizer;
import com.dbpool.optimizer.core.QueueingTheoryAnalyzer;
import com.dbpool.optimizer.model.*;
import com.dbpool.optimizer.parser.PoolConfigParserFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/pool-optimizer")
@CrossOrigin(origins = "*")
public class PoolOptimizerController {

    private final ConnectionPoolSimulator simulator;
    private final PoolOptimizer optimizer;
    private final QueueingTheoryAnalyzer queueingAnalyzer;
    private final PoolConfigParserFactory parserFactory;

    public PoolOptimizerController(ConnectionPoolSimulator simulator,
                                   PoolOptimizer optimizer,
                                   QueueingTheoryAnalyzer queueingAnalyzer,
                                   PoolConfigParserFactory parserFactory) {
        this.simulator = simulator;
        this.optimizer = optimizer;
        this.queueingAnalyzer = queueingAnalyzer;
        this.parserFactory = parserFactory;
    }

    @PostMapping("/simulate")
    public ResponseEntity<SimulationResult> simulate(@RequestBody SimulationRequest request) {
        SimulationResult result = simulator.simulate(request.getConfig(), request.getWorkload());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/optimize")
    public ResponseEntity<OptimizationRecommendation> optimize(@RequestBody OptimizationRequest request) {
        OptimizationRecommendation recommendation = optimizer.optimize(request);
        return ResponseEntity.ok(recommendation);
    }

    @PostMapping("/compare")
    public ResponseEntity<ConfigComparison> compare(@RequestBody OptimizationRequest request) {
        ConfigComparison comparison = optimizer.compareAndOptimize(request);
        return ResponseEntity.ok(comparison);
    }

    @PostMapping("/analyze-queue")
    public ResponseEntity<QueueMetrics> analyzeQueue(@RequestBody QueueAnalysisRequest request) {
        QueueMetrics metrics = queueingAnalyzer.analyze(request.getConfig(), request.getWorkload());
        return ResponseEntity.ok(metrics);
    }

    @GetMapping("/pool-types")
    public ResponseEntity<Map<String, String>> getPoolTypes() {
        Map<String, String> types = new HashMap<>();
        for (PoolType type : PoolType.values()) {
            types.put(type.name(), type.getDisplayName());
        }
        return ResponseEntity.ok(types);
    }

    @GetMapping("/default-config/{poolType}")
    public ResponseEntity<PoolConfig> getDefaultConfig(@PathVariable String poolType) {
        PoolConfig config;
        switch (poolType.toUpperCase()) {
            case "HIKARICP":
                config = PoolConfig.builder()
                        .poolType(PoolType.HIKARICP)
                        .maxPoolSize(10)
                        .minIdle(10)
                        .connectionTimeoutMs(30000)
                        .idleTimeoutMs(600000)
                        .maxLifetimeMs(1800000)
                        .leakDetectionThresholdMs(0)
                        .validationQuery("SELECT 1")
                        .testOnBorrow(false)
                        .testOnReturn(false)
                        .testWhileIdle(false)
                        .timeBetweenEvictionRunsMs(0)
                        .numTestsPerEvictionRun(0)
                        .build();
                break;
            case "DRUID":
                config = PoolConfig.builder()
                        .poolType(PoolType.DRUID)
                        .maxPoolSize(8)
                        .minIdle(0)
                        .connectionTimeoutMs(-1)
                        .idleTimeoutMs(1800000)
                        .maxLifetimeMs(25200000)
                        .leakDetectionThresholdMs(0)
                        .validationQuery("SELECT 1")
                        .testOnBorrow(false)
                        .testOnReturn(false)
                        .testWhileIdle(true)
                        .timeBetweenEvictionRunsMs(60000)
                        .numTestsPerEvictionRun(3)
                        .build();
                break;
            case "TOMCAT_JDBC":
                config = PoolConfig.builder()
                        .poolType(PoolType.TOMCAT_JDBC)
                        .maxPoolSize(100)
                        .minIdle(10)
                        .connectionTimeoutMs(30000)
                        .idleTimeoutMs(60000)
                        .maxLifetimeMs(0)
                        .leakDetectionThresholdMs(0)
                        .validationQuery("SELECT 1")
                        .testOnBorrow(false)
                        .testOnReturn(false)
                        .testWhileIdle(true)
                        .timeBetweenEvictionRunsMs(5000)
                        .numTestsPerEvictionRun(0)
                        .build();
                break;
            default:
                return ResponseEntity.badRequest().build();
        }
        return ResponseEntity.ok(config);
    }

    @GetMapping("/default-workload")
    public ResponseEntity<WorkloadProfile> getDefaultWorkload() {
        WorkloadProfile workload = WorkloadProfile.builder()
                .arrivalRate(50.0)
                .avgServiceTimeMs(100.0)
                .serviceTimeStdDevMs(30.0)
                .peakConcurrentUsers(100)
                .throughput(0)
                .simulationDurationMs(10000)
                .varianceFactor(0.5)
                .markovArrivalConfig(MarkovArrivalConfig.defaultConfig())
                .mixedTransactionConfig(MixedTransactionConfig.defaultConfig())
                .build();
        return ResponseEntity.ok(workload);
    }

    @GetMapping("/default-database-constraint")
    public ResponseEntity<DatabaseConstraint> getDefaultDatabaseConstraint() {
        return ResponseEntity.ok(DatabaseConstraint.defaultConstraint());
    }

    public static class SimulationRequest {
        private PoolConfig config;
        private WorkloadProfile workload;

        public PoolConfig getConfig() { return config; }
        public void setConfig(PoolConfig config) { this.config = config; }
        public WorkloadProfile getWorkload() { return workload; }
        public void setWorkload(WorkloadProfile workload) { this.workload = workload; }
    }

    public static class QueueAnalysisRequest {
        private PoolConfig config;
        private WorkloadProfile workload;

        public PoolConfig getConfig() { return config; }
        public void setConfig(PoolConfig config) { this.config = config; }
        public WorkloadProfile getWorkload() { return workload; }
        public void setWorkload(WorkloadProfile workload) { this.workload = workload; }
    }
}
