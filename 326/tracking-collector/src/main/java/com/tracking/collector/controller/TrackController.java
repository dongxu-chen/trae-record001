package com.tracking.collector.controller;

import com.tracking.collector.service.EventCollectorService;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.EventValidator;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/v1")
@CrossOrigin(origins = "*", maxAge = 3600)
public class TrackController {

    private final EventCollectorService collectorService;

    public TrackController(EventCollectorService collectorService) {
        this.collectorService = collectorService;
    }

    @PostMapping("/track")
    public ResponseEntity<Map<String, Object>> track(@Validated @RequestBody TrackEvent event,
                                                     HttpServletRequest request) {
        Map<String, Object> response = new HashMap<>();
        try {
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
            log.error("Error processing track event", e);
            response.put("code", 500);
            response.put("message", "internal server error");
            return ResponseEntity.status(500).body(response);
        }
    }

    @PostMapping("/track/batch")
    public ResponseEntity<Map<String, Object>> trackBatch(@Validated @RequestBody List<TrackEvent> events,
                                                          HttpServletRequest request) {
        Map<String, Object> response = new HashMap<>();
        try {
            EventValidator.ValidationResult result = collectorService.collectBatch(events, request);
            response.put("code", result.isValid() ? 0 : 400);
            response.put("message", result.isValid() ? "success" : "partial success");
            response.put("total", events.size());
            if (!result.getErrors().isEmpty()) {
                response.put("errors", result.getErrors());
            }
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error processing batch track events", e);
            response.put("code", 500);
            response.put("message", "internal server error");
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> response = new HashMap<>();
        response.put("code", 0);
        response.put("message", "ok");
        response.put("timestamp", System.currentTimeMillis());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/ping")
    public ResponseEntity<Map<String, Object>> ping() {
        Map<String, Object> response = new HashMap<>();
        response.put("code", 0);
        response.put("message", "pong");
        return ResponseEntity.ok(response);
    }
}
