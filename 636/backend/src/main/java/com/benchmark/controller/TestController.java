package com.benchmark.controller;

import com.alibaba.fastjson2.JSON;
import com.benchmark.dto.*;
import com.benchmark.service.AutoTuningService;
import com.benchmark.service.BaselineService;
import com.benchmark.service.StabilityTestService;
import com.benchmark.service.TestEngineService;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class TestController {

    private final TestEngineService testEngineService;
    private final StabilityTestService stabilityTestService;
    private final BaselineService baselineService;
    private final AutoTuningService autoTuningService;

    public TestController(TestEngineService testEngineService,
                          StabilityTestService stabilityTestService,
                          BaselineService baselineService,
                          AutoTuningService autoTuningService) {
        this.testEngineService = testEngineService;
        this.stabilityTestService = stabilityTestService;
        this.baselineService = baselineService;
        this.autoTuningService = autoTuningService;
    }

    @PostMapping("/test/start")
    public Map<String, String> startTest(@RequestBody TestConfig config) {
        String testId = testEngineService.startTest(config);
        Map<String, String> response = new HashMap<>();
        response.put("testId", testId);
        return response;
    }

    @GetMapping("/test/stop/{testId}")
    public Map<String, Boolean> stopTest(@PathVariable String testId) {
        boolean success = testEngineService.stopTest(testId);
        Map<String, Boolean> response = new HashMap<>();
        response.put("success", success);
        return response;
    }

    @GetMapping("/test/{testId}")
    public TestReport getReport(@PathVariable String testId) {
        return testEngineService.getReport(testId);
    }

    @GetMapping("/test/list")
    public List<TestReport> listReports() {
        return testEngineService.listReports();
    }

    @GetMapping("/report/{testId}/export")
    public ResponseEntity<String> exportReport(
            @PathVariable String testId,
            @RequestParam(defaultValue = "json") String format) {
        TestReport report = testEngineService.getReport(testId);
        if (report == null) {
            return ResponseEntity.notFound().build();
        }

        String content;
        String fileName;
        MediaType mediaType;

        if ("csv".equalsIgnoreCase(format)) {
            content = generateCsvReport(report);
            fileName = "report-" + testId + ".csv";
            mediaType = MediaType.parseMediaType("text/csv");
        } else {
            content = JSON.toJSONString(report);
            fileName = "report-" + testId + ".json";
            mediaType = MediaType.APPLICATION_JSON;
        }

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + fileName + "\"")
                .contentType(mediaType)
                .body(content);
    }

    @PostMapping("/stability/start")
    public Map<String, String> startStabilityTest(@RequestBody StabilityTestConfig config) {
        String testId = stabilityTestService.startStabilityTest(config);
        Map<String, String> response = new HashMap<>();
        response.put("testId", testId);
        return response;
    }

    @GetMapping("/stability/stop/{testId}")
    public Map<String, Boolean> stopStabilityTest(@PathVariable String testId) {
        boolean success = stabilityTestService.stopStabilityTest(testId);
        Map<String, Boolean> response = new HashMap<>();
        response.put("success", success);
        return response;
    }

    @GetMapping("/stability/{testId}")
    public StabilityTestReport getStabilityReport(@PathVariable String testId) {
        return stabilityTestService.getStabilityReport(testId);
    }

    @GetMapping("/stability/list")
    public List<StabilityTestReport> listStabilityReports() {
        return stabilityTestService.listStabilityReports();
    }

    @GetMapping("/stability/{testId}/status")
    public Map<String, Object> getStabilityTestStatus(@PathVariable String testId) {
        Map<String, Object> status = new HashMap<>();
        status.put("testId", testId);
        status.put("running", stabilityTestService.isRunning(testId));
        return status;
    }

    @PostMapping("/baseline/create/{testId}")
    public PerformanceBaseline createBaselineFromTest(@PathVariable String testId) {
        TestReport report = testEngineService.getReport(testId);
        if (report == null) {
            throw new RuntimeException("Test report not found: " + testId);
        }
        return baselineService.createBaseline(report);
    }

    @GetMapping("/baseline/list")
    public List<PerformanceBaseline> listBaselines() {
        return baselineService.getAllBaselines();
    }

    @GetMapping("/baseline/algorithm/{algorithm}")
    public List<PerformanceBaseline> getBaselinesByAlgorithm(@PathVariable String algorithm) {
        return baselineService.getBaselinesByAlgorithm(algorithm);
    }

    @GetMapping("/baseline/best/{algorithm}")
    public PerformanceBaseline getBestBaseline(@PathVariable String algorithm) {
        return baselineService.getBestBaseline(algorithm);
    }

    @GetMapping("/baseline/compare/{testId}")
    public BaselineService.BaselineComparison compareWithBaseline(@PathVariable String testId) {
        TestReport report = testEngineService.getReport(testId);
        if (report == null) {
            throw new RuntimeException("Test report not found: " + testId);
        }
        return baselineService.compareWithBaseline(report);
    }

    @DeleteMapping("/baseline/{baselineId}")
    public Map<String, Boolean> deleteBaseline(@PathVariable String baselineId) {
        boolean success = baselineService.deleteBaseline(baselineId);
        Map<String, Boolean> response = new HashMap<>();
        response.put("success", success);
        return response;
    }

    @PostMapping("/tuning/start")
    public Map<String, String> startAutoTuning(@RequestBody AutoTuningConfig config) {
        String tuningId = autoTuningService.startAutoTuning(config);
        Map<String, String> response = new HashMap<>();
        response.put("tuningId", tuningId);
        return response;
    }

    @GetMapping("/tuning/stop/{tuningId}")
    public Map<String, Boolean> stopAutoTuning(@PathVariable String tuningId) {
        boolean success = autoTuningService.stopAutoTuning(tuningId);
        Map<String, Boolean> response = new HashMap<>();
        response.put("success", success);
        return response;
    }

    @GetMapping("/tuning/{tuningId}")
    public AutoTuningReport getTuningReport(@PathVariable String tuningId) {
        return autoTuningService.getTuningReport(tuningId);
    }

    @GetMapping("/tuning/list")
    public List<AutoTuningReport> listTuningReports() {
        return autoTuningService.listTuningReports();
    }

    private String generateCsvReport(TestReport report) {
        StringBuilder sb = new StringBuilder();
        sb.append("Metric,Value\n");
        sb.append("Test ID,").append(report.getId()).append("\n");
        sb.append("Algorithm,").append(report.getConfig().getAlgorithm()).append("\n");
        sb.append("Thread Count,").append(report.getConfig().getThreadCount()).append("\n");
        if (report.getSummary() != null) {
            sb.append("Total Generated,").append(report.getSummary().getTotalGenerated()).append("\n");
            sb.append("Average QPS,").append(String.format("%.2f", report.getSummary().getAvgQps())).append("\n");
            sb.append("Peak QPS,").append(report.getSummary().getPeakQps()).append("\n");
        }
        if (report.getLatencyStats() != null) {
            sb.append("Latency Avg (us),").append(String.format("%.2f", report.getLatencyStats().getAvg())).append("\n");
            sb.append("Latency P50 (us),").append(String.format("%.2f", report.getLatencyStats().getP50())).append("\n");
            sb.append("Latency P95 (us),").append(String.format("%.2f", report.getLatencyStats().getP95())).append("\n");
            sb.append("Latency P99 (us),").append(String.format("%.2f", report.getLatencyStats().getP99())).append("\n");
        }
        if (report.getUniquenessCheck() != null) {
            sb.append("Is Unique,").append(report.getUniquenessCheck().isUnique()).append("\n");
            sb.append("Adjusted Duplicate Rate,").append(String.format("%.6f", report.getUniquenessCheck().getAdjustedDuplicateRate())).append("\n");
        }
        return sb.toString();
    }
}
