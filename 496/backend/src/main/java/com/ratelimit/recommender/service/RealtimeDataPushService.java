package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class RealtimeDataPushService {

    private final SimpMessagingTemplate messagingTemplate;
    private final CoordinatedRateLimitService coordinationService;
    private final MultiPeakTrafficGenerator trafficGenerator;
    private final TopologyAnalysisService topologyService;
    private final QueueingTheoryService queueingService;

    public RealtimeDataPushService(SimpMessagingTemplate messagingTemplate,
                                    CoordinatedRateLimitService coordinationService,
                                    MultiPeakTrafficGenerator trafficGenerator,
                                    TopologyAnalysisService topologyService,
                                    QueueingTheoryService queueingService) {
        this.messagingTemplate = messagingTemplate;
        this.coordinationService = coordinationService;
        this.trafficGenerator = trafficGenerator;
        this.topologyService = topologyService;
        this.queueingService = queueingService;
    }

    @Scheduled(fixedRate = 100)
    public void pushWaterLevelUpdates() {
        WaterLevelUpdate update = generateWaterLevelUpdate();
        messagingTemplate.convertAndSend("/topic/water-levels", update);
    }

    private WaterLevelUpdate generateWaterLevelUpdate() {
        List<ServiceNode> services = topologyService.generateSampleServices();
        Map<String, ServiceNode> serviceMap = services.stream()
                .collect(Collectors.toMap(ServiceNode::getServiceId, s -> s));

        Map<String, Double> waterLevels = new HashMap<>();
        Map<String, Double> currentQps = new HashMap<>();
        Map<String, Double> limitQps = new HashMap<>();
        Map<String, Double> adjustedQps = new HashMap<>();

        for (ServiceNode service : services) {
            String serviceId = service.getServiceId();

            double qps = trafficGenerator.getCurrentQps(serviceId);
            currentQps.put(serviceId, round(qps));

            RateLimitRecommendation recommendation = queueingService.recommendServiceRateLimit(service);
            double threshold = recommendation.getRecommendedServiceRule().getQpsThreshold();
            limitQps.put(serviceId, threshold);

            double adjusted = coordinationService.getAdjustedQpsThreshold(serviceId, threshold);
            adjustedQps.put(serviceId, round(adjusted));

            double waterLevel = qps / adjusted;
            waterLevels.put(serviceId, round(Math.min(2.0, waterLevel)));

            if (waterLevel >= 0.9) {
                coordinationService.checkAndTriggerCoordination(serviceId, qps, adjusted);
            }
        }

        List<CoordinatedRateLimit> coordinations = coordinationService.getActiveCoordinations();
        Map<String, Object> coordinationSummary = new HashMap<>();
        for (CoordinatedRateLimit coord : coordinations) {
            Map<String, Object> coordInfo = new HashMap<>();
            coordInfo.put("triggerService", coord.getTriggerServiceId());
            coordInfo.put("reason", coord.getTriggerReason());
            coordInfo.put("reduction", coord.getReductionPercentage());
            coordInfo.put("affectedCount", coord.getAffectedUpstreamServices().size());
            coordInfo.put("status", coord.getStatus());
            coordinationSummary.put(coord.getCoordinationId(), coordInfo);
        }

        return WaterLevelUpdate.builder()
                .type("WATER_LEVEL_UPDATE")
                .timestamp(LocalDateTime.now())
                .waterLevels(waterLevels)
                .currentQps(currentQps)
                .limitQps(limitQps)
                .adjustedQps(adjustedQps)
                .activeCoordinations(coordinations.size())
                .coordinations(coordinationSummary)
                .build();
    }

    private double round(double value) {
        return Math.round(value * 100.0) / 100.0;
    }

    public void pushCoordinationEvent(CoordinatedRateLimit coordination) {
        Map<String, Object> event = new HashMap<>();
        event.put("type", "COORDINATION_TRIGGERED");
        event.put("coordination", coordination);
        event.put("timestamp", LocalDateTime.now());
        messagingTemplate.convertAndSend("/topic/coordination-events", event);
    }

    public void pushAlert(String serviceId, String level, String message) {
        Map<String, Object> alert = new HashMap<>();
        alert.put("serviceId", serviceId);
        alert.put("level", level);
        alert.put("message", message);
        alert.put("timestamp", LocalDateTime.now());
        messagingTemplate.convertAndSend("/topic/alerts", alert);
    }

    public Map<String, Object> getCurrentStatus() {
        WaterLevelUpdate update = generateWaterLevelUpdate();
        Map<String, Object> status = new HashMap<>();
        status.put("waterLevels", update.getWaterLevels());
        status.put("currentQps", update.getCurrentQps());
        status.put("adjustedQps", update.getAdjustedQps());
        status.put("activeCoordinations", update.getActiveCoordinations());
        status.put("coordinations", update.getCoordinations());
        return status;
    }
}
