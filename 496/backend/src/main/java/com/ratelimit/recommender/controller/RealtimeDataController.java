package com.ratelimit.recommender.controller;

import com.ratelimit.recommender.model.CoordinatedRateLimit;
import com.ratelimit.recommender.model.MultiPeakTrafficPattern;
import com.ratelimit.recommender.model.TimeSeriesPoint;
import com.ratelimit.recommender.service.CoordinatedRateLimitService;
import com.ratelimit.recommender.service.MultiPeakTrafficGenerator;
import com.ratelimit.recommender.service.RealtimeDataPushService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/realtime")
@CrossOrigin(origins = "*")
public class RealtimeDataController {

    private final CoordinatedRateLimitService coordinationService;
    private final MultiPeakTrafficGenerator trafficGenerator;
    private final RealtimeDataPushService pushService;

    public RealtimeDataController(CoordinatedRateLimitService coordinationService,
                                   MultiPeakTrafficGenerator trafficGenerator,
                                   RealtimeDataPushService pushService) {
        this.coordinationService = coordinationService;
        this.trafficGenerator = trafficGenerator;
        this.pushService = pushService;
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getCurrentStatus() {
        return ResponseEntity.ok(pushService.getCurrentStatus());
    }

    @GetMapping("/water-levels")
    public ResponseEntity<Map<String, Double>> getWaterLevels() {
        return ResponseEntity.ok(coordinationService.getAllWaterLevels());
    }

    @GetMapping("/coordinations")
    public ResponseEntity<List<CoordinatedRateLimit>> getActiveCoordinations() {
        return ResponseEntity.ok(coordinationService.getActiveCoordinations());
    }

    @PostMapping("/coordination/trigger/{serviceId}")
    public ResponseEntity<CoordinatedRateLimit> triggerCoordination(
            @PathVariable String serviceId,
            @RequestParam(defaultValue = "0.95") double waterLevel,
            @RequestParam(defaultValue = "MANUAL_TRIGGER") String reason) {
        CoordinatedRateLimit coordination = coordinationService.triggerCoordination(serviceId, waterLevel, reason);
        pushService.pushCoordinationEvent(coordination);
        return ResponseEntity.ok(coordination);
    }

    @PostMapping("/coordination/release/{coordinationId}")
    public ResponseEntity<Boolean> releaseCoordination(@PathVariable String coordinationId) {
        boolean released = coordinationService.releaseCoordination(coordinationId);
        return ResponseEntity.ok(released);
    }

    @GetMapping("/coordination/{coordinationId}/impact")
    public ResponseEntity<Map<String, Object>> getCoordinationImpact(@PathVariable String coordinationId) {
        Map<String, Object> impact = coordinationService.getCoordinationImpact(coordinationId);
        if (impact == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(impact);
    }

    @GetMapping("/traffic-pattern/{serviceId}")
    public ResponseEntity<MultiPeakTrafficPattern> getTrafficPattern(@PathVariable String serviceId) {
        return ResponseEntity.ok(trafficGenerator.generateTrafficPattern(serviceId));
    }

    @GetMapping("/traffic-pattern/{serviceId}/summary")
    public ResponseEntity<Map<String, Object>> getTrafficPatternSummary(@PathVariable String serviceId) {
        return ResponseEntity.ok(trafficGenerator.getTrafficPatternSummary(serviceId));
    }

    @GetMapping("/traffic-series/{serviceId}")
    public ResponseEntity<List<TimeSeriesPoint>> getTrafficTimeSeries(
            @PathVariable String serviceId,
            @RequestParam(defaultValue = "120") int minutes) {
        return ResponseEntity.ok(trafficGenerator.generateMultiPeakTimeSeries(serviceId, minutes));
    }

    @PostMapping("/traffic-burst/{serviceId}")
    public ResponseEntity<Void> triggerBurst(
            @PathVariable String serviceId,
            @RequestParam(defaultValue = "3.0") double intensity,
            @RequestParam(defaultValue = "10") int durationMinutes) {
        trafficGenerator.triggerManualBurst(serviceId, intensity, durationMinutes);
        return ResponseEntity.ok().build();
    }
}
