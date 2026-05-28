package com.configcenter.server.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.core.AmqpTemplate;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.bus.event.RefreshRemoteApplicationEvent;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.ApplicationEventPublisherAware;
import org.springframework.stereotype.Service;

@Service
public class BusRefreshService implements ApplicationEventPublisherAware {

    private static final Logger logger = LoggerFactory.getLogger(BusRefreshService.class);

    private ApplicationEventPublisher applicationEventPublisher;

    @Autowired
    private AmqpTemplate amqpTemplate;

    @Override
    public void setApplicationEventPublisher(ApplicationEventPublisher applicationEventPublisher) {
        this.applicationEventPublisher = applicationEventPublisher;
    }

    public void refreshConfig(String applicationName) {
        logger.info("触发配置刷新, 应用: {}", applicationName);

        String destination = applicationName + ":**";

        RefreshRemoteApplicationEvent event = new RefreshRemoteApplicationEvent(
                this, "config-server", destination);

        applicationEventPublisher.publishEvent(event);

        logger.info("配置刷新事件已发布, 目标: {}", destination);
    }

    public void refreshAllConfigs() {
        logger.info("触发所有应用配置刷新");

        RefreshRemoteApplicationEvent event = new RefreshRemoteApplicationEvent(
                this, "config-server", "**");

        applicationEventPublisher.publishEvent(event);

        logger.info("全局配置刷新事件已发布");
    }

    public void refreshConfigByService(String serviceName) {
        logger.info("触发指定服务配置刷新, 服务: {}", serviceName);

        String destination = serviceName + ":**";

        RefreshRemoteApplicationEvent event = new RefreshRemoteApplicationEvent(
                this, "config-server", destination);

        applicationEventPublisher.publishEvent(event);

        logger.info("服务配置刷新事件已发布, 服务: {}", serviceName);
    }

    public void sendCustomBusMessage(String routingKey, String message) {
        logger.info("发送自定义Bus消息, 路由: {}, 消息: {}", routingKey, message);

        MessageProperties properties = new MessageProperties();
        properties.setContentType(MessageProperties.CONTENT_TYPE_JSON);

        Message busMessage = MessageBuilder
                .withBody(message.getBytes())
                .andProperties(properties)
                .build();

        amqpTemplate.convertAndSend("springCloudBus", routingKey, busMessage);

        logger.info("自定义Bus消息已发送");
    }
}
