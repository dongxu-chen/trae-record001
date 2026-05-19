package com.smartschedule.service.impl;

import com.smartschedule.entity.Notification;
import com.smartschedule.service.PushService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

@Service
@Primary
@Profile("!production")
public class MockPushServiceImpl implements PushService {

    private static final Logger logger = LoggerFactory.getLogger(MockPushServiceImpl.class);

    @Override
    public boolean sendNotification(Notification notification) {
        logger.info("=== MOCK PUSH NOTIFICATION ===");
        logger.info("To employee: {}", notification.getEmployee() != null ?
                notification.getEmployee().getName() : "Unknown");
        logger.info("Channel: {}", notification.getChannel());
        logger.info("Title: {}", notification.getTitle());
        logger.info("Content: {}", notification.getContent());
        logger.info("==============================");

        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }

        return true;
    }
}
