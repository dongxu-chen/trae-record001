package com.servicetopology.api;

import com.servicetopology.k8s.KubernetesServiceDiscovery;
import com.servicetopology.model.ServiceNode;
import com.servicetopology.neo4j.TopologyGraphService;
import com.servicetopology.tracing.TracingAnalyzer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@Slf4j
@RestController
@RequestMapping("/topology")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class TopologyController {

    private final TopologyGraphService topologyGraphService;
    private final KubernetesServiceDiscovery kubernetesServiceDiscovery;
    private final TracingAnalyzer tracingAnalyzer;

    @GetMapping
    public ResponseEntity<TopologyGraphService.TopologyData> getFullTopology() {
        log.info("Getting full topology");
        return ResponseEntity.ok(topologyGraphService.getFullTopology());
    }

    @GetMapping("/namespace/{namespace}")
    public ResponseEntity<TopologyGraphService.TopologyData> getTopologyByNamespace(
            @PathVariable String namespace) {
        log.info("Getting topology for namespace: {}", namespace);
        return ResponseEntity.ok(topologyGraphService.getTopologyByNamespace(namespace));
    }

    @GetMapping("/stats")
    public ResponseEntity<TopologyGraphService.TopologyStats> getTopologyStats() {
        log.info("Getting topology statistics");
        return ResponseEntity.ok(topologyGraphService.getTopologyStats());
    }

    @GetMapping("/services")
    public ResponseEntity<List<ServiceNode>> getAllServices() {
        log.info("Getting all discovered services");
        return ResponseEntity.ok(kubernetesServiceDiscovery.getAllDiscoveredServices());
    }

    @GetMapping("/services/{id}")
    public ResponseEntity<TopologyGraphService.ServiceNodeDetail> getServiceDetail(
            @PathVariable String id) {
        log.info("Getting service detail for: {}", id);
        TopologyGraphService.ServiceNodeDetail detail = topologyGraphService.getServiceDetail(id);
        if (detail.getId() == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(detail);
    }

    @GetMapping("/services/name/{namespace}/{name}")
    public ResponseEntity<ServiceNode> getServiceByName(
            @PathVariable String namespace,
            @PathVariable String name) {
        log.info("Getting service by name: {}/{}", namespace, name);
        Optional<ServiceNode> service = kubernetesServiceDiscovery.getServiceByName(name, namespace);
        return service.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/discovery/trigger")
    public ResponseEntity<Map<String, String>> triggerDiscovery() {
        log.info("Triggering manual service discovery");
        kubernetesServiceDiscovery.triggerDiscovery();
        return ResponseEntity.ok(Map.of(
            "status", "success",
            "message", "Discovery triggered successfully"
        ));
    }

    @PostMapping("/trace")
    public ResponseEntity<Map<String, String>> analyzeTrace(
            @RequestBody TracingAnalyzer.TraceData traceData) {
        log.info("Analyzing trace: {}", traceData.getTraceId());
        tracingAnalyzer.analyzeTrace(traceData);
        return ResponseEntity.ok(Map.of(
            "status", "success",
            "message", "Trace analyzed successfully"
        ));
    }

    @PostMapping("/call")
    public ResponseEntity<Map<String, String>> recordCall(
            @RequestBody TracingAnalyzer.CallRequest request) {
        log.info("Recording call: {} -> {}", request.getSourceService(), request.getTargetService());
        tracingAnalyzer.recordDirectCall(request);
        return ResponseEntity.ok(Map.of(
            "status", "success",
            "message", "Call recorded successfully"
        ));
    }

    @DeleteMapping("/clear")
    public ResponseEntity<Map<String, String>> clearAllData() {
        log.warn("Clearing all topology data");
        topologyGraphService.clearAllData();
        return ResponseEntity.ok(Map.of(
            "status", "success",
            "message", "All data cleared successfully"
        ));
    }

    @GetMapping("/grouped")
    public ResponseEntity<TopologyGraphService.GroupedTopologyData> getGroupedTopology() {
        log.info("Getting grouped topology");
        return ResponseEntity.ok(topologyGraphService.getGroupedTopology());
    }

    @GetMapping("/groups")
    public ResponseEntity<List<TopologyGraphService.TopologyGroup>> getAllGroups() {
        log.info("Getting all service groups");
        return ResponseEntity.ok(topologyGraphService.getAllGroups());
    }

    @GetMapping("/groups/{groupId}")
    public ResponseEntity<?> getGroupServices(@PathVariable String groupId) {
        log.info("Getting services for group: {}", groupId);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/groups")
    public ResponseEntity<TopologyGraphService.TopologyGroup> createGroup(
            @RequestBody TopologyGraphService.TopologyGroup group) {
        log.info("Creating service group: {}", group.getName());
        return ResponseEntity.ok(topologyGraphService.createGroup(group));
    }

    @PutMapping("/groups/{groupId}/collapsed")
    public ResponseEntity<Map<String, String>> updateGroupCollapsed(
            @PathVariable String groupId,
            @RequestParam boolean collapsed) {
        log.info("Updating group {} collapsed status: {}", groupId, collapsed);
        topologyGraphService.updateGroupCollapsed(groupId, collapsed);
        return ResponseEntity.ok(Map.of(
            "status", "success",
            "message", "Group collapsed status updated"
        ));
    }

    @DeleteMapping("/groups/{groupId}")
    public ResponseEntity<Map<String, String>> deleteGroup(@PathVariable String groupId) {
        log.info("Deleting service group: {}", groupId);
        topologyGraphService.deleteGroup(groupId);
        return ResponseEntity.ok(Map.of(
            "status", "success",
            "message", "Group deleted successfully"
        ));
    }

    @PostMapping("/groups/{groupId}/services/{serviceId}")
    public ResponseEntity<Map<String, String>> addServiceToGroup(
            @PathVariable String groupId,
            @PathVariable String serviceId) {
        log.info("Adding service {} to group {}", serviceId, groupId);
        topologyGraphService.addServiceToGroup(groupId, serviceId);
        return ResponseEntity.ok(Map.of(
            "status", "success",
            "message", "Service added to group successfully"
        ));
    }

    @DeleteMapping("/groups/{groupId}/services/{serviceId}")
    public ResponseEntity<Map<String, String>> removeServiceFromGroup(
            @PathVariable String groupId,
            @PathVariable String serviceId) {
        log.info("Removing service {} from group {}", serviceId, groupId);
        topologyGraphService.removeServiceFromGroup(groupId, serviceId);
        return ResponseEntity.ok(Map.of(
            "status", "success",
            "message", "Service removed from group successfully"
        ));
    }

    @GetMapping("/consumer-groups")
    public ResponseEntity<List<TopologyGraphService.ConsumerGroupNode>> getAllConsumerGroups() {
        log.info("Getting all consumer groups");
        return ResponseEntity.ok(topologyGraphService.getAllConsumerGroups());
    }

    @GetMapping("/traces")
    public ResponseEntity<List<TopologyGraphService.TraceInfo>> getRecentTraces(
            @RequestParam(defaultValue = "100") int limit) {
        log.info("Getting recent traces, limit: {}", limit);
        return ResponseEntity.ok(topologyGraphService.getTraceInfoList(limit));
    }

    @GetMapping("/traces/{traceId}")
    public ResponseEntity<TopologyGraphService.TraceDetail> getTraceDetail(
            @PathVariable String traceId) {
        log.info("Getting trace detail: {}", traceId);
        return ResponseEntity.ok(topologyGraphService.getTraceDetail(traceId));
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> healthCheck() {
        return ResponseEntity.ok(Map.of(
            "status", "healthy",
            "service", "service-topology-discovery"
        ));
    }

    @GetMapping("/impact/{serviceId}")
    public ResponseEntity<TopologyGraphService.ImpactAnalysisResult> getImpactAnalysis(
            @PathVariable String serviceId) {
        log.info("Getting impact analysis for service: {}", serviceId);
        return ResponseEntity.ok(topologyGraphService.getImpactAnalysis(serviceId));
    }

    @GetMapping("/change-prediction/{serviceId}")
    public ResponseEntity<TopologyGraphService.ChangePredictionResult> getChangePrediction(
            @PathVariable String serviceId,
            @RequestParam(defaultValue = "code") String changeType) {
        log.info("Getting change prediction for service: {}, type: {}", serviceId, changeType);
        return ResponseEntity.ok(topologyGraphService.predictChangeImpact(serviceId, changeType));
    }
}
