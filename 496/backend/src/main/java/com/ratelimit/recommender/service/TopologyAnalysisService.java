package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class TopologyAnalysisService {

    public ServiceTopology analyzeTopology(List<ServiceNode> services) {
        List<ServiceEdge> edges = buildEdges(services);
        Map<String, List<ServiceNode>> dependencyChains = buildDependencyChains(services);
        List<String> criticalPath = findCriticalPath(services, edges);
        double healthScore = calculateOverallHealth(services);

        return ServiceTopology.builder()
                .nodes(services)
                .edges(edges)
                .dependencyChains(dependencyChains)
                .criticalPath(criticalPath)
                .overallHealthScore(healthScore)
                .build();
    }

    private List<ServiceEdge> buildEdges(List<ServiceNode> services) {
        List<ServiceEdge> edges = new ArrayList<>();
        Map<String, ServiceNode> serviceMap = services.stream()
                .collect(Collectors.toMap(ServiceNode::getServiceId, s -> s));

        for (ServiceNode service : services) {
            if (service.getDependencies() != null) {
                for (String depId : service.getDependencies()) {
                    ServiceNode target = serviceMap.get(depId);
                    if (target != null) {
                        ServiceEdge edge = ServiceEdge.builder()
                                .sourceServiceId(service.getServiceId())
                                .targetServiceId(depId)
                                .callRate(calculateCallRate(service, target))
                                .avgLatencyMs(calculateAvgLatency(service, target))
                                .errorRate(calculateErrorRate(service, target))
                                .weight(calculateEdgeWeight(service, target))
                                .build();
                        edges.add(edge);
                    }
                }
            }
        }
        return edges;
    }

    private double calculateCallRate(ServiceNode source, ServiceNode target) {
        if (source.getMetrics() == null || target.getMetrics() == null) {
            return 10.0;
        }
        return Math.min(source.getMetrics().getAvgQps(), target.getMetrics().getAvgQps()) * 0.3;
    }

    private double calculateAvgLatency(ServiceNode source, ServiceNode target) {
        if (source.getMetrics() == null || target.getMetrics() == null) {
            return 50.0;
        }
        return (source.getMetrics().getAvgLatencyMs() + target.getMetrics().getAvgLatencyMs()) / 2;
    }

    private double calculateErrorRate(ServiceNode source, ServiceNode target) {
        if (source.getMetrics() == null || target.getMetrics() == null) {
            return 0.01;
        }
        return Math.max(source.getMetrics().getErrorRate(), target.getMetrics().getErrorRate());
    }

    private int calculateEdgeWeight(ServiceNode source, ServiceNode target) {
        double qps = calculateCallRate(source, target);
        double latency = calculateAvgLatency(source, target);
        return (int) (qps * latency / 100);
    }

    private Map<String, List<ServiceNode>> buildDependencyChains(List<ServiceNode> services) {
        Map<String, List<ServiceNode>> chains = new HashMap<>();
        Map<String, ServiceNode> serviceMap = services.stream()
                .collect(Collectors.toMap(ServiceNode::getServiceId, s -> s));

        for (ServiceNode service : services) {
            List<ServiceNode> chain = new ArrayList<>();
            Set<String> visited = new HashSet<>();
            buildChain(service, serviceMap, chain, visited, 0, 5);
            chains.put(service.getServiceId(), chain);
        }
        return chains;
    }

    private void buildChain(ServiceNode current, Map<String, ServiceNode> serviceMap,
                            List<ServiceNode> chain, Set<String> visited, int depth, int maxDepth) {
        if (depth >= maxDepth || visited.contains(current.getServiceId())) {
            return;
        }
        visited.add(current.getServiceId());
        chain.add(current);

        if (current.getDependencies() != null) {
            for (String depId : current.getDependencies()) {
                ServiceNode dep = serviceMap.get(depId);
                if (dep != null) {
                    buildChain(dep, serviceMap, chain, visited, depth + 1, maxDepth);
                }
            }
        }
    }

    private List<String> findCriticalPath(List<ServiceNode> services, List<ServiceEdge> edges) {
        Map<String, Double> latencyMap = new HashMap<>();
        Map<String, String> predecessor = new HashMap<>();

        for (ServiceNode service : services) {
            latencyMap.put(service.getServiceId(),
                    service.getMetrics() != null ? service.getMetrics().getAvgLatencyMs() : 50.0);
        }

        for (int i = 0; i < services.size(); i++) {
            boolean updated = false;
            for (ServiceEdge edge : edges) {
                double newLatency = latencyMap.get(edge.getSourceServiceId()) + edge.getAvgLatencyMs();
                if (newLatency > latencyMap.get(edge.getTargetServiceId())) {
                    latencyMap.put(edge.getTargetServiceId(), newLatency);
                    predecessor.put(edge.getTargetServiceId(), edge.getSourceServiceId());
                    updated = true;
                }
            }
            if (!updated) break;
        }

        String maxLatencyService = latencyMap.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse(null);

        List<String> path = new ArrayList<>();
        String current = maxLatencyService;
        while (current != null) {
            path.add(0, current);
            current = predecessor.get(current);
        }

        return path;
    }

    private double calculateOverallHealth(List<ServiceNode> services) {
        if (services.isEmpty()) return 1.0;

        double totalHealth = 0.0;
        for (ServiceNode service : services) {
            totalHealth += calculateServiceHealth(service);
        }
        return totalHealth / services.size();
    }

    private double calculateServiceHealth(ServiceNode service) {
        if (service.getMetrics() == null) return 0.8;

        ServiceMetrics metrics = service.getMetrics();
        double errorScore = Math.max(0, 1 - metrics.getErrorRate() * 10);
        double latencyScore = Math.max(0, 1 - metrics.getP99LatencyMs() / 1000);
        double cpuScore = Math.max(0, 1 - metrics.getCpuUtilization());
        double memoryScore = Math.max(0, 1 - metrics.getMemoryUtilization());

        return (errorScore * 0.4 + latencyScore * 0.3 + cpuScore * 0.15 + memoryScore * 0.15);
    }

    public List<ServiceNode> identifyBottlenecks(ServiceTopology topology) {
        List<ServiceNode> bottlenecks = new ArrayList<>();

        for (ServiceNode node : topology.getNodes()) {
            if (isBottleneck(node, topology.getEdges())) {
                bottlenecks.add(node);
            }
        }

        return bottlenecks;
    }

    private boolean isBottleneck(ServiceNode node, List<ServiceEdge> edges) {
        if (node.getMetrics() == null) return false;

        long incomingCalls = edges.stream()
                .filter(e -> e.getTargetServiceId().equals(node.getServiceId()))
                .mapToDouble(ServiceEdge::getCallRate)
                .sum();

        ServiceMetrics metrics = node.getMetrics();

        return incomingCalls > metrics.getPeakQps() * 0.8 ||
                metrics.getCpuUtilization() > 0.8 ||
                metrics.getP99LatencyMs() > 500;
    }

    public List<ServiceNode> generateSampleServices() {
        List<ServiceNode> services = new ArrayList<>();

        services.add(createServiceNode("gateway", "API Gateway", "1.0.0",
                Arrays.asList("user-service", "order-service", "product-service"),
                createServiceMetrics(500, 800, 45, 120, 250, 0.005, 3, 0.45, 0.6)));

        services.add(createServiceNode("user-service", "User Service", "2.1.0",
                Arrays.asList("db-service", "cache-service"),
                createServiceMetrics(200, 400, 30, 80, 180, 0.002, 2, 0.35, 0.5)));

        services.add(createServiceNode("order-service", "Order Service", "1.5.0",
                Arrays.asList("db-service", "payment-service", "inventory-service"),
                createServiceMetrics(150, 350, 80, 200, 400, 0.008, 2, 0.55, 0.65)));

        services.add(createServiceNode("product-service", "Product Service", "1.2.0",
                Arrays.asList("db-service", "search-service"),
                createServiceMetrics(180, 320, 35, 90, 200, 0.003, 2, 0.40, 0.55)));

        services.add(createServiceNode("payment-service", "Payment Service", "3.0.0",
                Arrays.asList("bank-gateway"),
                createServiceMetrics(80, 200, 150, 350, 600, 0.015, 2, 0.60, 0.70)));

        services.add(createServiceNode("inventory-service", "Inventory Service", "1.0.0",
                Arrays.asList("db-service"),
                createServiceMetrics(100, 250, 50, 130, 280, 0.004, 1, 0.50, 0.55)));

        services.add(createServiceNode("db-service", "Database Service", "1.0.0",
                new ArrayList<>(),
                createServiceMetrics(600, 1200, 25, 60, 120, 0.001, 1, 0.70, 0.75)));

        services.add(createServiceNode("cache-service", "Cache Service", "1.0.0",
                new ArrayList<>(),
                createServiceMetrics(1000, 2000, 5, 10, 20, 0.0005, 1, 0.30, 0.40)));

        services.add(createServiceNode("search-service", "Search Service", "1.0.0",
                Arrays.asList("db-service"),
                createServiceMetrics(80, 180, 100, 250, 450, 0.006, 1, 0.65, 0.60)));

        services.add(createServiceNode("bank-gateway", "Bank Gateway", "1.0.0",
                new ArrayList<>(),
                createServiceMetrics(80, 200, 150, 350, 600, 0.015, 1, 0.45, 0.50)));

        return services;
    }

    private ServiceNode createServiceNode(String id, String name, String version,
                                          List<String> dependencies, ServiceMetrics metrics) {
        Map<String, ApiEndpoint> endpoints = new HashMap<>();

        endpoints.put("GET /api/" + id, ApiEndpoint.builder()
                .path("/api/" + id)
                .method("GET")
                .description("Get " + name)
                .metrics(ApiMetrics.builder()
                        .avgQps(metrics.getAvgQps() * 0.4)
                        .peakQps(metrics.getPeakQps() * 0.4)
                        .avgLatencyMs(metrics.getAvgLatencyMs() * 0.8)
                        .p95LatencyMs(metrics.getP95LatencyMs() * 0.8)
                        .p99LatencyMs(metrics.getP99LatencyMs() * 0.8)
                        .errorRate(metrics.getErrorRate())
                        .build())
                .lastUpdate(LocalDateTime.now())
                .build());

        endpoints.put("POST /api/" + id, ApiEndpoint.builder()
                .path("/api/" + id)
                .method("POST")
                .description("Create " + name)
                .metrics(ApiMetrics.builder()
                        .avgQps(metrics.getAvgQps() * 0.3)
                        .peakQps(metrics.getPeakQps() * 0.3)
                        .avgLatencyMs(metrics.getAvgLatencyMs() * 1.2)
                        .p95LatencyMs(metrics.getP95LatencyMs() * 1.2)
                        .p99LatencyMs(metrics.getP99LatencyMs() * 1.2)
                        .errorRate(metrics.getErrorRate() * 1.5)
                        .build())
                .lastUpdate(LocalDateTime.now())
                .build());

        endpoints.put("PUT /api/" + id + "/{id}", ApiEndpoint.builder()
                .path("/api/" + id + "/{id}")
                .method("PUT")
                .description("Update " + name)
                .metrics(ApiMetrics.builder()
                        .avgQps(metrics.getAvgQps() * 0.2)
                        .peakQps(metrics.getPeakQps() * 0.2)
                        .avgLatencyMs(metrics.getAvgLatencyMs() * 1.1)
                        .p95LatencyMs(metrics.getP95LatencyMs() * 1.1)
                        .p99LatencyMs(metrics.getP99LatencyMs() * 1.1)
                        .errorRate(metrics.getErrorRate() * 1.2)
                        .build())
                .lastUpdate(LocalDateTime.now())
                .build());

        endpoints.put("DELETE /api/" + id + "/{id}", ApiEndpoint.builder()
                .path("/api/" + id + "/{id}")
                .method("DELETE")
                .description("Delete " + name)
                .metrics(ApiMetrics.builder()
                        .avgQps(metrics.getAvgQps() * 0.1)
                        .peakQps(metrics.getPeakQps() * 0.1)
                        .avgLatencyMs(metrics.getAvgLatencyMs() * 0.9)
                        .p95LatencyMs(metrics.getP95LatencyMs() * 0.9)
                        .p99LatencyMs(metrics.getP99LatencyMs() * 0.9)
                        .errorRate(metrics.getErrorRate() * 0.8)
                        .build())
                .lastUpdate(LocalDateTime.now())
                .build());

        return ServiceNode.builder()
                .serviceId(id)
                .serviceName(name)
                .version(version)
                .status("HEALTHY")
                .dependencies(dependencies)
                .dependents(new ArrayList<>())
                .endpoints(endpoints)
                .metrics(metrics)
                .lastUpdate(LocalDateTime.now())
                .build();
    }

    private ServiceMetrics createServiceMetrics(double avgQps, double peakQps,
                                                double avgLatency, double p95Latency, double p99Latency,
                                                double errorRate, int instances,
                                                double cpu, double memory) {
        return ServiceMetrics.builder()
                .avgQps(avgQps)
                .peakQps(peakQps)
                .avgLatencyMs(avgLatency)
                .p95LatencyMs(p95Latency)
                .p99LatencyMs(p99Latency)
                .errorRate(errorRate)
                .instanceCount(instances)
                .cpuUtilization(cpu)
                .memoryUtilization(memory)
                .totalRequests((long) (avgQps * 3600 * 24))
                .totalErrors((long) (avgQps * 3600 * 24 * errorRate))
                .build();
    }
}
