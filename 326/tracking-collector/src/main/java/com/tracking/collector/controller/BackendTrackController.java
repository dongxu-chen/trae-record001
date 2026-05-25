package com.tracking.collector.controller;

import com.tracking.collector.service.EventCollectorService;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.EventValidator;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/v1/backend")
public class BackendTrackController {

    private final EventCollectorService collectorService;

    public BackendTrackController(EventCollectorService collectorService) {
        this.collectorService = collectorService;
    }

    @PostMapping("/track")
    public ResponseEntity<Map<String, Object>> backendTrack(@RequestBody TrackEvent event,
                                                            @RequestHeader(value = "X-App-Secret", required = false) String appSecret,
                                                            HttpServletRequest request) {
        Map<String, Object> response = new HashMap<>();
        try {
            event.setSource(TrackingConstants.SOURCE_BACKEND);
            EventValidator.ValidationResult result = collectorService.collect(event, request);
            if (result.isValid()) {
                response.put("code", 0);
                response.put("message", "success");
                response.put("eventId", event.getId());
                return ResponseEntity.ok(response);
            } else {
                response.put("code", 400);
                response.put("message", "validation failed");
                response.put("errors", result.getErrors());
                return ResponseEntity.badRequest().body(response);
            }
        } catch (Exception e) {
            log.error("Error processing backend track event", e);
            response.put("code", 500);
            response.put("message", "internal server error");
            return ResponseEntity.status(500).body(response);
        }
    }

    @PostMapping("/track/batch")
    public ResponseEntity<Map<String, Object>> backendTrackBatch(@RequestBody List<TrackEvent> events,
                                                                 HttpServletRequest request) {
        Map<String, Object> response = new HashMap<>();
        try {
            events.forEach(event -> event.setSource(TrackingConstants.SOURCE_BACKEND));
            EventValidator.ValidationResult result = collectorService.collectBatch(events, request);
            response.put("code", result.isValid() ? 0 : 400);
            response.put("message", result.isValid() ? "success" : "partial success");
            response.put("total", events.size());
            if (!result.getErrors().isEmpty()) {
                response.put("errors", result.getErrors());
            }
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error processing backend batch track events", e);
            response.put("code", 500);
            response.put("message", "internal server error");
            return ResponseEntity.status(500).body(response);
        }
    }
}
