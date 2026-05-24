package com.abtest.service;

import com.abtest.dto.EventDTO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class EventTrackingService {

    private final ClickHouseMetricsService clickHouseMetricsService;

    public void trackEvent(EventDTO event) {
        try {
            clickHouseMetricsService.trackEvent(event);
            log.debug("Event tracked: {} for experiment {}", event.getEventName(), event.getExperimentId());
        } catch (Exception e) {
            log.error("Failed to track event", e);
        }
    }

    public void trackEvents(List<EventDTO> events) {
        for (EventDTO event : events) {
            trackEvent(event);
        }
    }
}
