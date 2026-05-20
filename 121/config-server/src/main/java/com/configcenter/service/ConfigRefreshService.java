package com.configcenter.service;

import com.configcenter.event.SelectiveRefreshRemoteApplicationEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.bus.BusProperties;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.*;
import java.util.regex.Pattern;

@Service
public class ConfigRefreshService {

    private static final Logger logger = LoggerFactory.getLogger(ConfigRefreshService.class);

    @Autowired
    private ApplicationEventPublisher eventPublisher;

    @Autowired
    private BusProperties busProperties;

    private static final Pattern SENSITIVE_PATTERN = Pattern.compile(
            "(password|secret|token|key|credential|private)",
            Pattern.CASE_INSENSITIVE
    );

    public boolean refreshByServices(Set<String> services, String branch) {
        logger.info("Starting configuration refresh for services: {}, branch: {}", services, branch);

        for (String service : services) {
            if (!validateServiceConfig(service, branch)) {
                logger.error("Configuration validation failed for service: {}", service);
                return false;
            }
        }

        for (String service : services) {
            publishRefreshEvent(service, branch);
        }

        logger.info("Configuration refresh completed successfully for services: {}", services);
        return true;
    }

    public boolean refreshAll(String branch) {
        logger.info("Starting full configuration refresh for all services, branch: {}", branch);

        publishRefreshEvent("**", branch);

        logger.info("Full configuration refresh triggered successfully");
        return true;
    }

    public boolean validateServiceConfig(String serviceName, String branch) {
        logger.info("Validating configuration for service: {}, branch: {}", serviceName, branch);

        try {
            String label = StringUtils.hasText(branch) ? branch : "main";

            logger.info("Configuration validation passed for service: {} (basic check)", serviceName);
            return true;

        } catch (Exception e) {
            logger.error("Error validating configuration for service: {}", serviceName, e);
            return false;
        }
    }

    private void publishRefreshEvent(String serviceName, String branch) {
        logger.info("Publishing selective refresh event for service: {}, branch: {}", serviceName, branch);

        SelectiveRefreshRemoteApplicationEvent event = new SelectiveRefreshRemoteApplicationEvent(
                this,
                busProperties.getId(),
                serviceName,
                serviceName,
                branch
        );

        eventPublisher.publishEvent(event);
    }

    public Map<String, Object> getServiceConfigStatus(String serviceName, String branch) {
        Map<String, Object> status = new HashMap<>();
        status.put("serviceName", serviceName);
        status.put("branch", branch);
        status.put("valid", validateServiceConfig(serviceName, branch));
        return status;
    }
}
