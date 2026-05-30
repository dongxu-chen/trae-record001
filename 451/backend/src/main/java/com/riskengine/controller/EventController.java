package com.riskengine.controller;

import com.riskengine.kafka.KafkaEventProcessor;
import com.riskengine.model.RiskEvent;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/events")
@CrossOrigin(origins = "*")
public class EventController {

    private final KafkaEventProcessor eventProcessor;

    public EventController(KafkaEventProcessor eventProcessor) {
        this.eventProcessor = eventProcessor;
    }

    @PostMapping("/evaluate")
    public ResponseEntity<Map<String, Object>> evaluateEvent(@RequestBody RiskEvent event) {
        if (event.getTimestamp() == null) {
            event.setTimestamp(System.currentTimeMillis());
        }
        eventProcessor.process(event);
        return ResponseEntity.ok(Map.of("status", "processed", "eventId", event.getEventId()));
    }
}
