package com.migration.report;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.model.PerformanceMetrics;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Component
public class PerformanceReporter {

    private final EurekaClient eurekaClient;
    private final NacosClient nacosClient;

    private final List<PerformanceMetrics> metricsHistory = Collections.synchronizedList(new ArrayList<>());

    public PerformanceReporter(EurekaClient eurekaClient, NacosClient nacosClient) {
        this.eurekaClient = eurekaClient;
        this.nacosClient = nacosClient;
    }

    public PerformanceMetrics benchmarkService(String serviceId) {
        PerformanceMetrics metrics = PerformanceMetrics.builder()
                .serviceId(serviceId)
                .timestamp(System.currentTimeMillis())
                .build();

        metrics.setEurekaRegistrationTimeMs(benchmarkEurekaRegistration(serviceId));
        metrics.setNacosRegistrationTimeMs(benchmarkNacosRegistration(serviceId));
        metrics.setEurekaDiscoveryTimeMs(benchmarkEurekaDiscovery(serviceId));
        metrics.setNacosDiscoveryTimeMs(benchmarkNacosDiscovery(serviceId));
        metrics.setEurekaHeartbeatTimeMs(benchmarkEurekaHeartbeat(serviceId));
        metrics.setNacosHeartbeatTimeMs(benchmarkNacosHeartbeat(serviceId));
        metrics.setEurekaThroughput(benchmarkEurekaThroughput(serviceId));
        metrics.setNacosThroughput(benchmarkNacosThroughput(serviceId));
        metrics.setEurekaP99Latency(measureEurekaP99Latency(serviceId));
        metrics.setNacosP99Latency(measureNacosP99Latency(serviceId));

        metricsHistory.add(metrics);
        log.info("Performance benchmark completed for service {}", serviceId);
        return metrics;
    }

    public Map<String, Object> generateComparisonReport() {
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("generatedAt", System.currentTimeMillis());

        if (metricsHistory.isEmpty()) {
            report.put("message", "No performance data available. Run benchmarks first.");
            return report;
        }

        List<String> serviceIds = eurekaClient.getAllServiceIds();
        for (String serviceId : serviceIds) {
            benchmarkService(serviceId);
        }

        double avgEurekaRegTime = metricsHistory.stream()
                .mapToLong(PerformanceMetrics::getEurekaRegistrationTimeMs).average().orElse(0);
        double avgNacosRegTime = metricsHistory.stream()
                .mapToLong(PerformanceMetrics::getNacosRegistrationTimeMs).average().orElse(0);

        double avgEurekaDiscTime = metricsHistory.stream()
                .mapToLong(PerformanceMetrics::getEurekaDiscoveryTimeMs).average().orElse(0);
        double avgNacosDiscTime = metricsHistory.stream()
                .mapToLong(PerformanceMetrics::getNacosDiscoveryTimeMs).average().orElse(0);

        double avgEurekaHbTime = metricsHistory.stream()
                .mapToLong(PerformanceMetrics::getEurekaHeartbeatTimeMs).average().orElse(0);
        double avgNacosHbTime = metricsHistory.stream()
                .mapToLong(PerformanceMetrics::getNacosHeartbeatTimeMs).average().orElse(0);

        double avgEurekaThroughput = metricsHistory.stream()
                .mapToDouble(PerformanceMetrics::getEurekaThroughput).average().orElse(0);
        double avgNacosThroughput = metricsHistory.stream()
                .mapToDouble(PerformanceMetrics::getNacosThroughput).average().orElse(0);

        double avgEurekaP99 = metricsHistory.stream()
                .mapToDouble(PerformanceMetrics::getEurekaP99Latency).average().orElse(0);
        double avgNacosP99 = metricsHistory.stream()
                .mapToDouble(PerformanceMetrics::getNacosP99Latency).average().orElse(0);

        Map<String, Object> registration = new LinkedHashMap<>();
        registration.put("eurekaAvgMs", avgEurekaRegTime);
        registration.put("nacosAvgMs", avgNacosRegTime);
        registration.put("improvement", calculateImprovement(avgEurekaRegTime, avgNacosRegTime));
        report.put("registration", registration);

        Map<String, Object> discovery = new LinkedHashMap<>();
        discovery.put("eurekaAvgMs", avgEurekaDiscTime);
        discovery.put("nacosAvgMs", avgNacosDiscTime);
        discovery.put("improvement", calculateImprovement(avgEurekaDiscTime, avgNacosDiscTime));
        report.put("discovery", discovery);

        Map<String, Object> heartbeat = new LinkedHashMap<>();
        heartbeat.put("eurekaAvgMs", avgEurekaHbTime);
        heartbeat.put("nacosAvgMs", avgNacosHbTime);
        heartbeat.put("improvement", calculateImprovement(avgEurekaHbTime, avgNacosHbTime));
        report.put("heartbeat", heartbeat);

        Map<String, Object> throughput = new LinkedHashMap<>();
        throughput.put("eurekaAvgOps", avgEurekaThroughput);
        throughput.put("nacosAvgOps", avgNacosThroughput);
        throughput.put("improvement", calculateThroughputImprovement(avgEurekaThroughput, avgNacosThroughput));
        report.put("throughput", throughput);

        Map<String, Object> latency = new LinkedHashMap<>();
        latency.put("eurekaP99Ms", avgEurekaP99);
        latency.put("nacosP99Ms", avgNacosP99);
        latency.put("improvement", calculateImprovement(avgEurekaP99, avgNacosP99));
        report.put("latency", latency);

        report.put("overallVerdict", generateVerdict(report));

        report.put("benchmarkedServices", metricsHistory.size());
        report.put("details", metricsHistory.stream()
                .map(this::metricsToMap)
                .collect(Collectors.toList()));

        return report;
    }

    private long benchmarkEurekaRegistration(String serviceId) {
        ServiceInstance testInstance = ServiceInstance.builder()
                .serviceId(serviceId + "-benchmark")
                .instanceId("benchmark-instance")
                .host("127.0.0.1")
                .port(9999)
                .status("UP")
                .metadata(new HashMap<>())
                .build();

        long start = System.currentTimeMillis();
        eurekaClient.registerInstance(testInstance);
        long elapsed = System.currentTimeMillis() - start;

        eurekaClient.deregisterInstance(testInstance.getServiceId(), testInstance.getInstanceId());
        return elapsed;
    }

    private long benchmarkNacosRegistration(String serviceId) {
        ServiceInstance testInstance = ServiceInstance.builder()
                .serviceId(serviceId + "-benchmark")
                .instanceId("benchmark-instance")
                .host("127.0.0.1")
                .port(9999)
                .status("UP")
                .metadata(new HashMap<>())
                .build();

        long start = System.currentTimeMillis();
        nacosClient.registerInstance(testInstance);
        long elapsed = System.currentTimeMillis() - start;

        nacosClient.deregisterInstance(testInstance);
        return elapsed;
    }

    private long benchmarkEurekaDiscovery(String serviceId) {
        long start = System.currentTimeMillis();
        eurekaClient.getInstances(serviceId);
        return System.currentTimeMillis() - start;
    }

    private long benchmarkNacosDiscovery(String serviceId) {
        long start = System.currentTimeMillis();
        nacosClient.getInstances(serviceId);
        return System.currentTimeMillis() - start;
    }

    private long benchmarkEurekaHeartbeat(String serviceId) {
        List<ServiceInstance> instances = eurekaClient.getInstances(serviceId);
        if (instances.isEmpty()) return -1;

        long start = System.currentTimeMillis();
        eurekaClient.sendHeartbeat(serviceId, instances.get(0).getInstanceId());
        return System.currentTimeMillis() - start;
    }

    private long benchmarkNacosHeartbeat(String serviceId) {
        List<ServiceInstance> instances = nacosClient.getInstances(serviceId);
        if (instances.isEmpty()) return -1;

        long start = System.currentTimeMillis();
        nacosClient.sendHeartbeat(instances.get(0));
        return System.currentTimeMillis() - start;
    }

    private double benchmarkEurekaThroughput(String serviceId) {
        int iterations = 10;
        long start = System.currentTimeMillis();
        for (int i = 0; i < iterations; i++) {
            eurekaClient.getInstances(serviceId);
        }
        long elapsed = System.currentTimeMillis() - start;
        return elapsed > 0 ? (iterations * 1000.0 / elapsed) : 0;
    }

    private double benchmarkNacosThroughput(String serviceId) {
        int iterations = 10;
        long start = System.currentTimeMillis();
        for (int i = 0; i < iterations; i++) {
            nacosClient.getInstances(serviceId);
        }
        long elapsed = System.currentTimeMillis() - start;
        return elapsed > 0 ? (iterations * 1000.0 / elapsed) : 0;
    }

    private double measureEurekaP99Latency(String serviceId) {
        List<Long> latencies = new ArrayList<>();
        for (int i = 0; i < 50; i++) {
            long start = System.nanoTime();
            eurekaClient.getInstances(serviceId);
            latencies.add((System.nanoTime() - start) / 1_000_000);
        }
        Collections.sort(latencies);
        int p99Index = (int) Math.ceil(latencies.size() * 0.99) - 1;
        return latencies.get(Math.min(p99Index, latencies.size() - 1));
    }

    private double measureNacosP99Latency(String serviceId) {
        List<Long> latencies = new ArrayList<>();
        for (int i = 0; i < 50; i++) {
            long start = System.nanoTime();
            nacosClient.getInstances(serviceId);
            latencies.add((System.nanoTime() - start) / 1_000_000);
        }
        Collections.sort(latencies);
        int p99Index = (int) Math.ceil(latencies.size() * 0.99) - 1;
        return latencies.get(Math.min(p99Index, latencies.size() - 1));
    }

    private String calculateImprovement(double eurekaValue, double nacosValue) {
        if (eurekaValue == 0) return "N/A";
        double improvement = ((eurekaValue - nacosValue) / eurekaValue) * 100;
        return String.format("%.1f%%", improvement);
    }

    private String calculateThroughputImprovement(double eurekaValue, double nacosValue) {
        if (eurekaValue == 0) return "N/A";
        double improvement = ((nacosValue - eurekaValue) / eurekaValue) * 100;
        return String.format("%.1f%%", improvement);
    }

    private String generateVerdict(Map<String, Object> report) {
        int nacosBetter = 0;
        int eurekaBetter = 0;

        for (String key : Arrays.asList("registration", "discovery", "heartbeat", "latency")) {
            @SuppressWarnings("unchecked")
            Map<String, Object> section = (Map<String, Object>) report.get(key);
            String improvement = (String) section.get("improvement");
            if (improvement != null && !improvement.equals("N/A")) {
                double value = Double.parseDouble(improvement.replace("%", ""));
                if (value > 0) nacosBetter++;
                else if (value < 0) eurekaBetter++;
            }
        }

        if (nacosBetter > eurekaBetter) {
            return "NACOS_PERFORMS_BETTER - Nacos outperforms Eureka in " + nacosBetter + " out of 4 categories. Migration recommended.";
        } else if (eurekaBetter > nacosBetter) {
            return "EUREKA_PERFORMS_BETTER - Eureka outperforms Nacos in " + eurekaBetter + " out of 4 categories. Review migration necessity.";
        } else {
            return "COMPARABLE - Both registries show similar performance. Migration is safe from a performance perspective.";
        }
    }

    private Map<String, Object> metricsToMap(PerformanceMetrics m) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("serviceId", m.getServiceId());
        map.put("eurekaRegistrationMs", m.getEurekaRegistrationTimeMs());
        map.put("nacosRegistrationMs", m.getNacosRegistrationTimeMs());
        map.put("eurekaDiscoveryMs", m.getEurekaDiscoveryTimeMs());
        map.put("nacosDiscoveryMs", m.getNacosDiscoveryTimeMs());
        map.put("eurekaThroughput", m.getEurekaThroughput());
        map.put("nacosThroughput", m.getNacosThroughput());
        map.put("eurekaP99Ms", m.getEurekaP99Latency());
        map.put("nacosP99Ms", m.getNacosP99Latency());
        return map;
    }
}
