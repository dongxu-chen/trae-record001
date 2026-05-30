package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class CoordinatedRateLimitService {

    private final TopologyAnalysisService topologyService;
    private final Map<String, CoordinatedRateLimit> activeCoordinations = new ConcurrentHashMap<>();
    private final Map<String, Double> originalQpsThresholds = new ConcurrentHashMap<>();
    private final Map<String, Double> serviceWaterLevels = new ConcurrentHashMap<>();

    public CoordinatedRateLimitService(TopologyAnalysisService topologyService) {
        this.topologyService = topologyService;
    }

    public CoordinatedRateLimit checkAndTriggerCoordination(String downstreamServiceId,
                                                              double currentQps,
                                                              double threshold) {
        double waterLevel = currentQps / threshold;

        serviceWaterLevels.put(downstreamServiceId, waterLevel);

        if (waterLevel >= 0.9) {
            return triggerCoordination(downstreamServiceId, waterLevel, "WATER_LEVEL_EXCEEDED");
        }

        return null;
    }

    public CoordinatedRateLimit triggerCoordination(String downstreamServiceId,
                                                     double waterLevel,
                                                     String reason) {
        String coordinationId = UUID.randomUUID().toString();

        List<ServiceNode> services = topologyService.generateSampleServices();
        Map<String, ServiceNode> serviceMap = services.stream()
                .collect(Collectors.toMap(ServiceNode::getServiceId, s -> s));

        List<String> upstreamServices = findUpstreamServices(downstreamServiceId, services);

        double reductionPercentage = calculateReductionPercentage(waterLevel);

        Map<String, Double> upstreamReductions = new HashMap<>();
        for (String upstreamId : upstreamServices) {
            double dependencyWeight = calculateDependencyWeight(upstreamId, downstreamServiceId, services);
            double serviceReduction = reductionPercentage * Math.min(1.0, dependencyWeight + 0.3);
            upstreamReductions.put(upstreamId, serviceReduction);
        }

        CoordinatedRateLimit coordination = CoordinatedRateLimit.builder()
                .coordinationId(coordinationId)
                .triggerServiceId(downstreamServiceId)
                .triggerReason(reason)
                .triggerThreshold(waterLevel)
                .reductionPercentage(reductionPercentage)
                .startTime(LocalDateTime.now())
                .estimatedEndTime(LocalDateTime.now().plusMinutes(5))
                .affectedUpstreamServices(upstreamServices)
                .upstreamReductions(upstreamReductions)
                .status(CoordinatedRateLimit.CoordinationStatus.TRIGGERED)
                .build();

        activeCoordinations.put(coordinationId, coordination);

        applyCoordinatedLimits(coordination, serviceMap);

        return coordination;
    }

    private List<String> findUpstreamServices(String targetServiceId, List<ServiceNode> services) {
        List<String> upstreams = new ArrayList<>();

        for (ServiceNode service : services) {
            if (service.getDependencies() != null && service.getDependencies().contains(targetServiceId)) {
                upstreams.add(service.getServiceId());
                upstreams.addAll(findUpstreamServices(service.getServiceId(), services));
            }
        }

        return upstreams.stream().distinct().collect(Collectors.toList());
    }

    private double calculateDependencyWeight(String upstreamId, String targetId, List<ServiceNode> services) {
        ServiceNode upstream = services.stream()
                .filter(s -> s.getServiceId().equals(upstreamId))
                .findFirst()
                .orElse(null);

        if (upstream == null || upstream.getMetrics() == null) {
            return 0.5;
        }

        int totalDependencies = upstream.getDependencies() != null ? upstream.getDependencies().size() : 1;
        return 1.0 / totalDependencies;
    }

    private double calculateReductionPercentage(double waterLevel) {
        if (waterLevel >= 1.0) {
            return 0.5;
        } else if (waterLevel >= 0.95) {
            return 0.35;
        } else if (waterLevel >= 0.9) {
            return 0.2;
        }
        return 0.1;
    }

    private void applyCoordinatedLimits(CoordinatedRateLimit coordination,
                                         Map<String, ServiceNode> serviceMap) {
        Map<String, Double> reductions = coordination.getUpstreamReductions();

        for (Map.Entry<String, Double> entry : reductions.entrySet()) {
            String serviceId = entry.getKey();
            double reduction = entry.getValue();

            ServiceNode service = serviceMap.get(serviceId);
            if (service != null && service.getMetrics() != null) {
                double originalQps = service.getMetrics().getPeakQps();
                originalQpsThresholds.putIfAbsent(serviceId, originalQps);
            }
        }

        coordination.setStatus(CoordinatedRateLimit.CoordinationStatus.ACTIVE);
    }

    public boolean releaseCoordination(String coordinationId) {
        CoordinatedRateLimit coordination = activeCoordinations.remove(coordinationId);
        if (coordination != null) {
            coordination.setStatus(CoordinatedRateLimit.CoordinationStatus.COMPLETED);
            return true;
        }
        return false;
    }

    public List<CoordinatedRateLimit> getActiveCoordinations() {
        return new ArrayList<>(activeCoordinations.values());
    }

    public double getAdjustedQpsThreshold(String serviceId, double originalThreshold) {
        double totalReduction = 0;

        for (CoordinatedRateLimit coordination : activeCoordinations.values()) {
            if (coordination.getStatus() == CoordinatedRateLimit.CoordinationStatus.ACTIVE) {
                Double reduction = coordination.getUpstreamReductions().get(serviceId);
                if (reduction != null) {
                    totalReduction = Math.max(totalReduction, reduction);
                }
            }
        }

        return originalThreshold * (1 - totalReduction);
    }

    public Map<String, Double> getAllWaterLevels() {
        return new HashMap<>(serviceWaterLevels);
    }

    public void updateWaterLevel(String serviceId, double waterLevel) {
        serviceWaterLevels.put(serviceId, waterLevel);
    }

    public void simulateWaterLevelChanges() {
        List<ServiceNode> services = topologyService.generateSampleServices();
        Random random = new Random();

        for (ServiceNode service : services) {
            double baseLevel = serviceWaterLevels.getOrDefault(service.getServiceId(), 0.5);
            double change = (random.nextDouble() - 0.5) * 0.1;
            double newLevel = Math.max(0.1, Math.min(1.2, baseLevel + change));
            serviceWaterLevels.put(service.getServiceId(), newLevel);
        }
    }

    public Map<String, Object> getCoordinationImpact(String coordinationId) {
        CoordinatedRateLimit coordination = activeCoordinations.get(coordinationId);
        if (coordination == null) {
            return null;
        }

        Map<String, Object> impact = new HashMap<>();
        impact.put("coordination", coordination);
        impact.put("affectedServices", coordination.getAffectedUpstreamServices().size());
        impact.put("totalReduction", coordination.getUpstreamReductions().values().stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(0));

        return impact;
    }
}
