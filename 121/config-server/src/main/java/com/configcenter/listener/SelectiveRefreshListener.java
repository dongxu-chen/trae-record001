package com.configcenter.listener;

import com.configcenter.event.SelectiveRefreshRemoteApplicationEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.bus.event.RefreshRemoteApplicationEvent;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class SelectiveRefreshListener {

    private static final Logger logger = LoggerFactory.getLogger(SelectiveRefreshListener.class);

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private ApplicationEventPublisher eventPublisher;

    @Value("${spring.cloud.bus.id:config-server}")
    private String serviceId;

    @EventListener
    public void handleSelectiveRefresh(SelectiveRefreshRemoteApplicationEvent event) {
        logger.info("Received selective refresh event for service: {}, branch: {}",
                event.getServiceName(), event.getBranch());

        String serviceName = event.getServiceName();

        if ("**".equals(serviceName) || "*".equals(serviceName)) {
            publishRefreshEvent(null);
            logger.info("Published refresh event for all services");
        } else {
            String[] services = serviceName.split(",");
            for (String service : services) {
                publishRefreshEvent(service.trim());
                logger.info("Published refresh event for service: {}", service.trim());
            }
        }
    }

    private void publishRefreshEvent(String destinationService) {
        RefreshRemoteApplicationEvent refreshEvent = new RefreshRemoteApplicationEvent(
                this,
                serviceId,
                destinationService
        );
        eventPublisher.publishEvent(refreshEvent);
    }
}
