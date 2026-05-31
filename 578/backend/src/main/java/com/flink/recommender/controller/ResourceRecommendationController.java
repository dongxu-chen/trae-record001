package com.flink.recommender.controller;

import com.flink.recommender.analysis.JobAnalysisService;
import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.cost.CostEstimationService;
import com.flink.recommender.model.ResourceConfig;
import com.flink.recommender.model.ResourceRecommendation;
import com.flink.recommender.recommendation.AutoResourceAdjustmentService;
import com.flink.recommender.recommendation.ResourceOptimizationService;
import com.flink.recommender.repository.ResourceConfigRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/recommendations")
@CrossOrigin(origins = "http://localhost:3000")
public class ResourceRecommendationController {

    private static final Logger logger = LoggerFactory.getLogger(ResourceRecommendationController.class);

    private final ResourceOptimizationService optimizationService;
    private final JobAnalysisService jobAnalysisService;
    private final CostEstimationService costEstimationService;
    private final ResourceConfigRepository resourceConfigRepository;
    private final AutoResourceAdjustmentService autoAdjustmentService;

    public ResourceRecommendationController(
            ResourceOptimizationService optimizationService,
            JobAnalysisService jobAnalysisService,
            CostEstimationService costEstimationService,
            ResourceConfigRepository resourceConfigRepository,
            AutoResourceAdjustmentService autoAdjustmentService) {
        this.optimizationService = optimizationService;
        this.jobAnalysisService = jobAnalysisService;
        this.costEstimationService = costEstimationService;
        this.resourceConfigRepository = resourceConfigRepository;
        this.autoAdjustmentService = autoAdjustmentService;
    }

    @GetMapping("/{jobId}")
    public ResponseEntity<?> getRecommendation(@PathVariable String jobId) {
        logger.info("Getting resource recommendation for job: {}", jobId);

        Optional<JobTopologyAnalysis> analysisOpt = jobAnalysisService.analyzeJob(jobId);

        if (analysisOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        JobTopologyAnalysis analysis = analysisOpt.get();

        ResourceConfig currentConfig = resourceConfigRepository.findByJobId(jobId)
                .orElseGet(() -> createDefaultConfig(analysis));

        ResourceRecommendation recommendation = optimizationService.generateRecommendation(
                analysis, currentConfig);

        return ResponseEntity.ok(recommendation);
    }

    @PostMapping("/{jobId}/apply")
    public ResponseEntity<?> applyRecommendation(
            @PathVariable String jobId,
            @RequestBody ResourceConfig config) {
        logger.info("Applying resource recommendation for job: {}", jobId);

        config.setJobId(jobId);
        ResourceConfig saved = resourceConfigRepository.save(config);

        return ResponseEntity.ok(saved);
    }

    @GetMapping("/{jobId}/cost-comparison")
    public ResponseEntity<?> getCostComparison(@PathVariable String jobId) {
        logger.info("Getting cost comparison for job: {}", jobId);

        Optional<JobTopologyAnalysis> analysisOpt = jobAnalysisService.analyzeJob(jobId);

        if (analysisOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        JobTopologyAnalysis analysis = analysisOpt.get();
        ResourceConfig currentConfig = resourceConfigRepository.findByJobId(jobId)
                .orElseGet(() -> createDefaultConfig(analysis));

        ResourceRecommendation recommendation = optimizationService.generateRecommendation(
                analysis, currentConfig);

        Map<String, Object> comparison = costEstimationService.compareCosts(
                currentConfig, recommendation.getRecommendedConfig());

        return ResponseEntity.ok(comparison);
    }

    @GetMapping("/{jobId}/tco")
    public ResponseEntity<?> getTotalCostOfOwnership(
            @PathVariable String jobId,
            @RequestParam(defaultValue = "12") int months) {
        logger.info("Calculating TCO for job: {}, months: {}", jobId, months);

        Optional<JobTopologyAnalysis> analysisOpt = jobAnalysisService.analyzeJob(jobId);

        if (analysisOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        JobTopologyAnalysis analysis = analysisOpt.get();
        ResourceConfig config = resourceConfigRepository.findByJobId(jobId)
                .orElseGet(() -> createDefaultConfig(analysis));

        Map<String, Object> tco = costEstimationService.calculateTotalCostOfOwnership(config, months);
        return ResponseEntity.ok(tco);
    }

    @GetMapping("/{jobId}/optimization-tips")
    public ResponseEntity<?> getOptimizationTips(@PathVariable String jobId) {
        logger.info("Getting optimization tips for job: {}", jobId);

        Optional<JobTopologyAnalysis> analysisOpt = jobAnalysisService.analyzeJob(jobId);

        if (analysisOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        JobTopologyAnalysis analysis = analysisOpt.get();
        ResourceConfig config = resourceConfigRepository.findByJobId(jobId)
                .orElseGet(() -> createDefaultConfig(analysis));

        Map<String, Object> tips = costEstimationService.getCostOptimizationTips(config);
        return ResponseEntity.ok(tips);
    }

    @GetMapping("/demo/mock-recommendation")
    public ResponseEntity<?> getMockRecommendation() {
        logger.info("Generating mock recommendation for demo");

        ResourceConfig currentConfig = ResourceConfig.builder()
                .jobId("demo-job-001")
                .jobName("Demo Streaming Job")
                .jobManagerMemoryMb(1024)
                .taskManagerMemoryMb(4096)
                .taskManagerCpuCores(1.0)
                .numTaskManagers(8)
                .parallelism(8)
                .build();

        ResourceConfig recommendedConfig = ResourceConfig.builder()
                .jobId("demo-job-001")
                .jobName("Demo Streaming Job")
                .jobManagerMemoryMb(1024)
                .taskManagerMemoryMb(4096)
                .taskManagerCpuCores(1.5)
                .numTaskManagers(12)
                .parallelism(12)
                .build();

        ResourceRecommendation recommendation = ResourceRecommendation.builder()
                .jobId("demo-job-001")
                .jobName("Demo Streaming Job")
                .currentConfig(currentConfig)
                .recommendedConfig(recommendedConfig)
                .build();

        recommendation.setEstimatedCostPerHour(0.52);
        recommendation.setEstimatedCostPerDay(12.48);
        recommendation.setEstimatedCostPerMonth(374.40);

        recommendation.setRecommendedCostPerHour(0.78);
        recommendation.setRecommendedCostPerDay(18.72);
        recommendation.setRecommendedCostPerMonth(561.60);
        recommendation.setCostSavingsPercentage(-50.0);

        recommendation.setEstimatedPerformanceImprovement(35.0);
        recommendation.setExpectedLatencyReduction(25.0);
        recommendation.setExpectedThroughputIncrease(40.0);

        Map<String, ResourceRecommendation.VertexRecommendation> vertexRecs = new HashMap<>();
        String[] vertexNames = {"Source: Kafka Consumer", "Window Aggregation", "Keyed Process", "Sink: Elasticsearch"};
        int[] currentParallelism = {8, 8, 8, 8};
        int[] recommendedParallelism = {8, 16, 16, 8};
        String[] reasons = {
                "Current configuration appears optimal",
                "Data skew detected (factor: 2.50), Identified as performance bottleneck",
                "High CPU utilization: 89.0%, Identified as performance bottleneck",
                "Current configuration appears optimal"
        };

        for (int i = 0; i < vertexNames.length; i++) {
            ResourceRecommendation.VertexRecommendation vr = ResourceRecommendation.VertexRecommendation.builder()
                    .vertexId("vertex-" + i)
                    .vertexName(vertexNames[i])
                    .currentParallelism(currentParallelism[i])
                    .recommendedParallelism(recommendedParallelism[i])
                    .recommendedMemoryMb(512)
                    .recommendedCpuCores(0.75)
                    .reason(reasons[i])
                    .expectedImprovement(recommendedParallelism[i] > currentParallelism[i] ? 0.35 : 0.0)
                    .build();
            vertexRecs.put("vertex-" + i, vr);
        }
        recommendation.setVertexRecommendations(vertexRecs);

        recommendation.getReasoning().add("Increased parallelism for 2 bottleneck vertices");
        recommendation.getReasoning().add("Recommendations account for detected data skew issues");
        recommendation.getReasoning().add("Targeting 70% CPU utilization");
        recommendation.getReasoning().add("Targeting 75% memory utilization");

        recommendation.getRisks().add("Recommended configuration increases operational costs");
        recommendation.getRisks().add("Significant parallelism increase may cause higher cluster load");

        recommendation.setConfidenceLevel("HIGH");

        return ResponseEntity.ok(recommendation);
    }

    @PostMapping("/{jobId}/auto-adjust")
    public ResponseEntity<?> autoAdjustResources(
            @PathVariable String jobId,
            @RequestParam(defaultValue = "false") boolean dryRun) {
        logger.info("Auto adjusting resources for job: {}, dryRun: {}", jobId, dryRun);

        JobTopologyAnalysis.AutoAdjustmentResult result = autoAdjustmentService.analyzeAndApplyAdjustment(jobId, dryRun);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/auto-adjust/batch")
    public ResponseEntity<?> batchAutoAdjust(
            @RequestBody List<String> jobIds,
            @RequestParam(defaultValue = "false") boolean dryRun) {
        logger.info("Batch auto adjusting resources for {} jobs, dryRun: {}", jobIds.size(), dryRun);

        List<JobTopologyAnalysis.AutoAdjustmentResult> results = autoAdjustmentService.batchAdjust(jobIds, dryRun);
        return ResponseEntity.ok(results);
    }

    @GetMapping("/{jobId}/adjustment-preview")
    public ResponseEntity<?> getAdjustmentPreview(@PathVariable String jobId) {
        logger.info("Getting adjustment preview for job: {}", jobId);

        Map<String, Object> preview = autoAdjustmentService.getAdjustmentPreview(jobId);
        if (preview.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(preview);
    }

    private ResourceConfig createDefaultConfig(JobTopologyAnalysis analysis) {
        return ResourceConfig.builder()
                .jobId(analysis.getJobId())
                .jobName(analysis.getJobName())
                .jobManagerMemoryMb(1024)
                .taskManagerMemoryMb(4096)
                .taskManagerCpuCores(1.0)
                .numTaskManagers(Math.max(1, analysis.getMaxParallelism()))
                .parallelism(analysis.getMaxParallelism())
                .build();
    }
}
