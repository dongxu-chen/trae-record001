package com.pushplatform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.pushplatform.common.enums.PushChannelEnum;
import com.pushplatform.entity.PushRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class TokenManageService {

    private static final Logger logger = LoggerFactory.getLogger(TokenManageService.class);

    private static final Set<String> TOKEN_INVALID_ERRORS = new HashSet<>(Arrays.asList(
            "InvalidDeviceToken",
            "BadDeviceToken",
            "DeviceTokenNotForTopic",
            "Unregistered",
            "token invalid",
            "User is offline",
            "InvalidRegistration"
    ));

    private final ConcurrentHashMap<String, Long> invalidTokenCache = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        logger.info("Token manage service initialized");
    }

    public boolean isTokenInvalid(String errorMsg) {
        if (errorMsg == null || errorMsg.isEmpty()) {
            return false;
        }
        String lowerError = errorMsg.toLowerCase();
        return TOKEN_INVALID_ERRORS.stream()
                .anyMatch(error -> lowerError.contains(error.toLowerCase()));
    }

    @Async("tokenCleanExecutor")
    public void asyncCleanInvalidToken(String channel, String token) {
        try {
            if (invalidTokenCache.containsKey(token)) {
                logger.debug("Token already in clean queue: {}", token);
                return;
            }

            invalidTokenCache.put(token, System.currentTimeMillis());
            logger.info("Start cleaning invalid token, channel: {}, token: {}", channel, token);

            boolean success = doCleanToken(channel, token);
            if (success) {
                logger.info("Clean invalid token success, channel: {}, token: {}", channel, token);
            } else {
                logger.warn("Clean invalid token failed, channel: {}, token: {}", channel, token);
            }

            invalidTokenCache.remove(token);
        } catch (Exception e) {
            logger.error("Clean invalid token error, channel: {}, token: {}", channel, token, e);
            invalidTokenCache.remove(token);
        }
    }

    private boolean doCleanToken(String channel, String token) {
        try {
            PushChannelEnum channelEnum = PushChannelEnum.getByCode(channel);
            if (channelEnum == null) {
                logger.warn("Unknown channel: {}", channel);
                return false;
            }

            switch (channelEnum) {
                case APNS:
                    return cleanApnsToken(token);
                case FCM:
                    return cleanFcmToken(token);
                case WEBSOCKET:
                    return cleanWebSocketToken(token);
                default:
                    return false;
            }
        } catch (Exception e) {
            logger.error("Do clean token error", e);
            return false;
        }
    }

    private boolean cleanApnsToken(String token) {
        logger.info("Clean APNS invalid token: {}", token);
        return true;
    }

    private boolean cleanFcmToken(String token) {
        logger.info("Clean FCM invalid token: {}", token);
        return true;
    }

    private boolean cleanWebSocketToken(String token) {
        logger.info("Clean WebSocket invalid token: {}", token);
        return true;
    }

    public long getInvalidTokenCount() {
        return invalidTokenCache.size();
    }
}
