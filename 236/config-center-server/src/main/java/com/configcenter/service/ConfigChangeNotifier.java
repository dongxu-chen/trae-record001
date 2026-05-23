package com.configcenter.service;

import com.configcenter.event.ConfigChangeEvent;
import org.springframework.cloud.bus.BusProperties;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

@Service
public class ConfigChangeNotifier {

    private final ApplicationEventPublisher eventPublisher;
    private final BusProperties busProperties;
    private final LongPollingService longPollingService;

    public ConfigChangeNotifier(ApplicationEventPublisher eventPublisher,
                                BusProperties busProperties,
                                LongPollingService longPollingService) {
        this.eventPublisher = eventPublisher;
        this.busProperties = busProperties;
        this.longPollingService = longPollingService;
    }

    public void notifyChange(String application, String profile, String version) {
        String destinationService = application + ":**";

        ConfigChangeEvent event = new ConfigChangeEvent(
                this,
                busProperties.getId(),
                destinationService,
                application,
                profile,
                version
        );

        eventPublisher.publishEvent(event);

        longPollingService.notifyConfigChange(application, profile, version);
    }
}
