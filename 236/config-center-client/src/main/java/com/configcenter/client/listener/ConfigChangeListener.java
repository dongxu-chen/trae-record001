package com.configcenter.client.listener;

import com.configcenter.event.ConfigChangeEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.bus.event.RefreshRemoteApplicationEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class ConfigChangeListener {

    private static final Logger logger = LoggerFactory.getLogger(ConfigChangeListener.class);

    @EventListener
    public void onConfigChange(ConfigChangeEvent event) {
        logger.info("Received config change event: application={}, profile={}, version={}",
                event.getApplication(), event.getProfile(), event.getVersion());
    }

    @EventListener
    public void onRefreshEvent(RefreshRemoteApplicationEvent event) {
        logger.info("Received refresh event from: {}", event.getOriginService());
    }
}
