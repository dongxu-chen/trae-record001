package com.tracing.staining.controller;

import com.tracing.staining.analysis.StainingAnalysisService;
import com.tracing.staining.context.CrossCloudTraceManager;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/trace/analysis")
@RequiredArgsConstructor
public class StainingAnalysisController {

    private final StainingAnalysisService analysisService;
    private final CrossCloudTraceManager crossCloudTraceManager;

    @GetMapping("/overview")
    public ResponseEntity<Map<String, Object>> getStainingOverview() {
        log.info("Getting staining analysis overview");
        Map<String, Object> overview = analysisService.getStainingOverview();
        return ResponseEntity.ok(overview);
    }

    @GetMapping("/group/{groupBy}")
    public ResponseEntity<Map<String, Object>> getGroupAnalysis(@PathVariable String groupBy) {
        log.info("Getting staining group analysis by: {}", groupBy);
        Map<String, Object> analysis = analysisService.getStainingGroupAnalysis(groupBy);
        return ResponseEntity.ok(analysis);
    }

    @GetMapping("/biztag-distribution")
    public ResponseEntity<Map<String, Object>> getBizTagDistribution() {
        log.info("Getting biz tag distribution");
        Map<String, Object> distribution = analysisService.getBizTagDistribution();
        return ResponseEntity.ok(distribution);
    }

    @GetMapping("/slow-requests")
    public ResponseEntity<List<Map<String, Object>>> getSlowRequests(
            @RequestParam(defaultValue = "20") int limit) {
        log.info("Getting top {} slow requests", limit);
        List<Map<String, Object>> slowRequests = analysisService.getSlowRequests(limit);
        return ResponseEntity.ok(slowRequests);
    }

    @GetMapping("/error-requests")
    public ResponseEntity<List<Map<String, Object>>> getErrorRequests() {
        log.info("Getting error requests");
        List<Map<String, Object>> errorRequests = analysisService.getErrorRequests();
        return ResponseEntity.ok(errorRequests);
    }

    @GetMapping("/trace/{traceId}")
    public ResponseEntity<Map<String, Object>> getTraceDetails(@PathVariable String traceId) {
        log.info("Getting trace details for: {}", traceId);
        Map<String, Object> details = analysisService.getTraceDetails(traceId);
        return ResponseEntity.ok(details);
    }

    @GetMapping("/crosscloud/{crossCloudTraceId}")
    public ResponseEntity<Map<String, Object>> getCrossCloudTraceChain(
            @PathVariable String crossCloudTraceId) {
        log.info("Getting cross-cloud trace chain for: {}", crossCloudTraceId);
        Map<String, Object> chain = analysisService.getCrossCloudTraceChain(crossCloudTraceId);
        return ResponseEntity.ok(chain);
    }

    @GetMapping("/crosscloud-overview")
    public ResponseEntity<Map<String, Object>> getCrossCloudOverview() {
        log.info("Getting cross-cloud analysis overview");
        Map<String, Object> overview = analysisService.getStainingOverview();
        Map<String, Object> result = new LinkedHashMap<>();

        result.put("crossCloudConfig", Map.of(
                "provider", crossCloudTraceManager.getCloudConfig().getProvider(),
                "region", crossCloudTraceManager.getCloudConfig().getRegion(),
                "availabilityZone", crossCloudTraceManager.getCloudConfig().getAvailabilityZone(),
                "accountId", crossCloudTraceManager.getCloudConfig().getAccountId(),
                "serviceName", crossCloudTraceManager.getCloudConfig().getServiceName(),
                "crossCloudEnabled", crossCloudTraceManager.getCloudConfig().isCrossCloudEnabled()
        ));

        result.put("totalCrossCloudRequests", overview.get("totalCrossCloudRequests"));
        result.put("crossCloudAnalysis", analysisService.getStainingOverview().get("countByCloudRegion"));

        return ResponseEntity.ok(result);
    }

    @DeleteMapping("/data")
    public ResponseEntity<Map<String, String>> clearAllData() {
        log.info("Clearing all staining analysis data");
        analysisService.clearAllData();
        Map<String, String> response = new LinkedHashMap<>();
        response.put("status", "success");
        response.put("message", "All staining analysis data cleared");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/cloud-info")
    public ResponseEntity<Map<String, Object>> getCloudInfo() {
        Map<String, Object> info = new LinkedHashMap<>();
        info.put("provider", crossCloudTraceManager.getCloudConfig().getProvider());
        info.put("region", crossCloudTraceManager.getCloudConfig().getRegion());
        info.put("availabilityZone", crossCloudTraceManager.getCloudConfig().getAvailabilityZone());
        info.put("accountId", crossCloudTraceManager.getCloudConfig().getAccountId());
        info.put("serviceName", crossCloudTraceManager.getCloudConfig().getServiceName());
        info.put("crossCloudEnabled", crossCloudTraceManager.getCloudConfig().isCrossCloudEnabled());
        info.put("crossCloudTraceIdPrefix", crossCloudTraceManager.getCloudConfig().getCrossCloudTraceIdPrefix());
        return ResponseEntity.ok(info);
    }
}
