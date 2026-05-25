package com.coupon.notification.service;

import com.alibaba.fastjson2.JSON;
import com.coupon.model.CouponDistribution;
import com.coupon.clickhouse.repository.CouponDistributionRepository;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class CouponNotificationService {

    private static final String NOTIFICATION_RECORD_KEY = "notify:record:";
    private static final String NOTIFICATION_STATS_KEY = "notify:stats:";
    private static final String USER_PUSH_CHANNEL_KEY = "notify:channel:";

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHH");

    public enum ReminderStage {
        THREE_DAYS(3, ChronoUnit.DAYS, "expire_3d", "优惠券还有3天过期"),
        ONE_DAY(1, ChronoUnit.DAYS, "expire_1d", "优惠券还有1天过期"),
        TWO_HOURS(2, ChronoUnit.HOURS, "expire_2h", "优惠券还有2小时过期，马上使用！");

        private final long value;
        private final ChronoUnit unit;
        private final String code;
        private final String defaultMessage;

        ReminderStage(long value, ChronoUnit unit, String code, String defaultMessage) {
            this.value = value;
            this.unit = unit;
            this.code = code;
            this.defaultMessage = defaultMessage;
        }

        public long getValue() { return value; }
        public ChronoUnit getUnit() { return unit; }
        public String getCode() { return code; }
        public String getDefaultMessage() { return defaultMessage; }
    }

    public enum NotificationChannel {
        APP_PUSH("app_push", "APP推送"),
        SMS("sms", "短信"),
        EMAIL("email", "邮件"),
        WECHAT("wechat", "微信"),
        IN_APP("in_app", "站内信");

        private final String code;
        private final String name;

        NotificationChannel(String code, String name) {
            this.code = code;
            this.name = name;
        }

        public String getCode() { return code; }
        public String getName() { return name; }
    }

    private final CouponDistributionRepository distributionRepository;
    private final StringRedisTemplate redisTemplate;

    @Value("${coupon.notification.enable:true}")
    private boolean enableNotification;

    @Value("${coupon.notification.batch-size:100}")
    private int batchSize;

    @Value("${coupon.notification.default-channels:app_push,in_app}")
    private String defaultChannels;

    public CouponNotificationService(CouponDistributionRepository distributionRepository,
                                     StringRedisTemplate redisTemplate) {
        this.distributionRepository = distributionRepository;
        this.redisTemplate = redisTemplate;
    }

    @Scheduled(cron = "0 0 * * * *")
    public void scheduledExpiryReminders() {
        if (!enableNotification) {
            log.debug("Notification is disabled");
            return;
        }

        log.info("Starting scheduled expiry reminder job");
        try {
            for (ReminderStage stage : ReminderStage.values()) {
                sendExpiryRemindersForStage(stage);
            }
        } catch (Exception e) {
            log.error("Failed to run scheduled expiry reminders", e);
        }
    }

    public void sendExpiryRemindersForStage(ReminderStage stage) {
        log.info("Processing expiry reminders for stage: {}", stage.getCode());

        LocalDateTime now = LocalDateTime.now();
        LocalDateTime targetTime = now.plus(stage.getValue(), stage.getUnit());
        LocalDateTime startTime = targetTime.truncatedTo(ChronoUnit.HOURS);
        LocalDateTime endTime = startTime.plusHours(1);

        int offset = 0;
        int totalSent = 0;

        while (true) {
            try {
                List<CouponDistribution> expiringCoupons = distributionRepository
                        .findExpiringCoupons(startTime, endTime, offset, batchSize);

                if (expiringCoupons == null || expiringCoupons.isEmpty()) {
                    break;
                }

                for (CouponDistribution coupon : expiringCoupons) {
                    try {
                        boolean sent = sendExpiryReminder(coupon, stage);
                        if (sent) {
                            totalSent++;
                        }
                    } catch (Exception e) {
                        log.error("Failed to send reminder for distribution: {}",
                                coupon.getDistributionId(), e);
                    }
                }

                offset += batchSize;

                if (expiringCoupons.size() < batchSize) {
                    break;
                }

            } catch (Exception e) {
                log.error("Failed to fetch expiring coupons for stage: {}", stage.getCode(), e);
                break;
            }
        }

        log.info("Completed expiry reminders for stage {}: sent {} reminders",
                stage.getCode(), totalSent);

        updateNotificationStats(stage.getCode(), totalSent);
    }

    public boolean sendExpiryReminder(CouponDistribution coupon, ReminderStage stage) {
        String distributionId = coupon.getDistributionId();
        String userId = coupon.getUserId();

        if (hasAlreadySentNotification(distributionId, stage.getCode())) {
            log.debug("Notification already sent for coupon {} stage {}", distributionId, stage.getCode());
            return false;
        }

        if (coupon.getStatus() != com.coupon.model.enums.CouponStatus.ISSUED) {
            log.debug("Coupon {} is not in ISSUED status, skipping reminder", distributionId);
            return false;
        }

        List<NotificationChannel> channels = getUserPreferredChannels(userId);
        if (channels.isEmpty()) {
            channels = getDefaultChannels();
        }

        NotificationContent content = buildNotificationContent(coupon, stage, channels);
        boolean allSent = true;

        for (NotificationChannel channel : channels) {
            try {
                boolean sent = sendNotification(userId, channel, content);
                if (sent) {
                    recordNotificationSend(distributionId, userId, stage.getCode(), channel);
                } else {
                    allSent = false;
                }
            } catch (Exception e) {
                log.error("Failed to send {} notification for coupon {}", channel.getCode(), distributionId, e);
                allSent = false;
            }
        }

        markNotificationSent(distributionId, stage.getCode());

        log.debug("Sent expiry reminder for coupon {} stage {} via channels: {}",
                distributionId, stage.getCode(),
                channels.stream().map(NotificationChannel::getCode).collect(Collectors.toList()));

        return allSent;
    }

    private NotificationContent buildNotificationContent(CouponDistribution coupon,
                                                         ReminderStage stage,
                                                         List<NotificationChannel> channels) {
        BigDecimal denomination = coupon.getDenomination();
        LocalDateTime expireTime = coupon.getExpireTime();

        Map<String, String> templates = new HashMap<>();
        templates.put("expire_3d", "您的{amount}元优惠券还有3天过期，满{minAmount}元可用，快去使用吧！");
        templates.put("expire_1d", "提醒！您的{amount}元优惠券明天就要过期了，立即使用享受优惠！");
        templates.put("expire_2h", "最后机会！您的{amount}元优惠券还有2小时过期，手慢无！");

        String template = templates.getOrDefault(stage.getCode(), stage.getDefaultMessage());
        String message = template
                .replace("{amount}", denomination.toString())
                .replace("{minAmount}", coupon.getMinOrderAmount() != null
                        ? coupon.getMinOrderAmount().toString() : "0");

        String title = "优惠券过期提醒";
        if (stage == ReminderStage.TWO_HOURS) {
            title = "⚠️ 优惠券即将过期";
        } else if (stage == ReminderStage.ONE_DAY) {
            title = "优惠券明天过期";
        }

        return NotificationContent.builder()
                .title(title)
                .message(message)
                .couponCode(coupon.getCouponCode())
                .denomination(denomination)
                .expireTime(expireTime)
                .stage(stage.getCode())
                .distributionId(coupon.getDistributionId())
                .deepLink("coupon://detail/" + coupon.getDistributionId())
                .build();
    }

    private boolean sendNotification(String userId, NotificationChannel channel,
                                     NotificationContent content) {
        switch (channel) {
            case APP_PUSH:
                return sendAppPush(userId, content);
            case SMS:
                return sendSms(userId, content);
            case EMAIL:
                return sendEmail(userId, content);
            case WECHAT:
                return sendWechat(userId, content);
            case IN_APP:
                return sendInAppMessage(userId, content);
            default:
                log.warn("Unsupported notification channel: {}", channel);
                return false;
        }
    }

    private boolean sendAppPush(String userId, NotificationContent content) {
        log.info("📱 Sending APP push to user {}: {}", userId, content.getTitle());
        simulateSendDelay();
        return true;
    }

    private boolean sendSms(String userId, NotificationContent content) {
        log.info("📱 Sending SMS to user {}: {}", userId, content.getMessage());
        simulateSendDelay();
        return true;
    }

    private boolean sendEmail(String userId, NotificationContent content) {
        log.info("📧 Sending EMAIL to user {}: {}", userId, content.getTitle());
        simulateSendDelay();
        return true;
    }

    private boolean sendWechat(String userId, NotificationContent content) {
        log.info("💬 Sending WECHAT to user {}: {}", userId, content.getTitle());
        simulateSendDelay();
        return true;
    }

    private boolean sendInAppMessage(String userId, NotificationContent content) {
        String inAppKey = "notify:inapp:" + userId + ":" + System.currentTimeMillis();
        try {
            String json = JSON.toJSONString(content);
            redisTemplate.opsForList().leftPush(inAppKey, json);
            redisTemplate.expire(inAppKey, 7, TimeUnit.DAYS);
            log.info("📝 Sent IN-APP message to user {}: {}", userId, content.getTitle());
            return true;
        } catch (Exception e) {
            log.error("Failed to send in-app message", e);
            return false;
        }
    }

    private void simulateSendDelay() {
        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private boolean hasAlreadySentNotification(String distributionId, String stage) {
        String key = NOTIFICATION_RECORD_KEY + distributionId;
        try {
            return Boolean.TRUE.equals(redisTemplate.opsForHash().hasKey(key, stage));
        } catch (Exception e) {
            log.error("Failed to check notification record", e);
            return false;
        }
    }

    private void markNotificationSent(String distributionId, String stage) {
        String key = NOTIFICATION_RECORD_KEY + distributionId;
        try {
            redisTemplate.opsForHash().put(key, stage, String.valueOf(System.currentTimeMillis()));
            redisTemplate.expire(key, 7, TimeUnit.DAYS);
        } catch (Exception e) {
            log.error("Failed to mark notification sent", e);
        }
    }

    private void recordNotificationSend(String distributionId, String userId, String stage,
                                        NotificationChannel channel) {
        String key = NOTIFICATION_STATS_KEY + LocalDateTime.now().format(DATE_FORMATTER);
        try {
            redisTemplate.opsForHash().increment(key, "total", 1);
            redisTemplate.opsForHash().increment(key, stage, 1);
            redisTemplate.opsForHash().increment(key, channel.getCode(), 1);
            redisTemplate.expire(key, 30, TimeUnit.DAYS);
        } catch (Exception e) {
            log.error("Failed to record notification stats", e);
        }
    }

    private List<NotificationChannel> getUserPreferredChannels(String userId) {
        String key = USER_PUSH_CHANNEL_KEY + userId;
        List<NotificationChannel> channels = new ArrayList<>();
        try {
            String channelsStr = redisTemplate.opsForValue().get(key);
            if (channelsStr != null && !channelsStr.isEmpty()) {
                String[] codes = channelsStr.split(",");
                for (String code : codes) {
                    try {
                        channels.add(NotificationChannel.valueOf(code.toUpperCase()));
                    } catch (Exception e) {
                        log.debug("Invalid channel code: {}", code);
                    }
                }
            }
        } catch (Exception e) {
            log.debug("No user preferred channels for user: {}", userId);
        }
        return channels;
    }

    private List<NotificationChannel> getDefaultChannels() {
        List<NotificationChannel> channels = new ArrayList<>();
        String[] codes = defaultChannels.split(",");
        for (String code : codes) {
            try {
                channels.add(NotificationChannel.valueOf(code.trim().toUpperCase()));
            } catch (Exception e) {
                log.warn("Invalid default channel: {}", code);
            }
        }
        return channels;
    }

    public void setUserPreferredChannels(String userId, List<NotificationChannel> channels) {
        String key = USER_PUSH_CHANNEL_KEY + userId;
        try {
            String channelsStr = channels.stream()
                    .map(NotificationChannel::getCode)
                    .collect(Collectors.joining(","));
            redisTemplate.opsForValue().set(key, channelsStr, 90, TimeUnit.DAYS);
            log.info("Set user {} preferred channels: {}", userId, channelsStr);
        } catch (Exception e) {
            log.error("Failed to set user preferred channels: {}", userId, e);
        }
    }

    public List<NotificationChannel> getCurrentUserChannels(String userId) {
        List<NotificationChannel> preferred = getUserPreferredChannels(userId);
        return preferred.isEmpty() ? getDefaultChannels() : preferred;
    }

    public void updateNotificationStats(String stage, int count) {
    }

    public NotificationStatistics getNotificationStatistics() {
        NotificationStatistics stats = new NotificationStatistics();
        String todayKey = NOTIFICATION_STATS_KEY + LocalDateTime.now().format(DATE_FORMATTER);

        try {
            Map<Object, Object> data = redisTemplate.opsForHash().entries(todayKey);
            Map<String, Integer> channelStats = new HashMap<>();
            Map<String, Integer> stageStats = new HashMap<>();

            int total = 0;

            for (Map.Entry<Object, Object> entry : data.entrySet()) {
                String key = entry.getKey().toString();
                int value = Integer.parseInt(entry.getValue().toString());

                if ("total".equals(key)) {
                    total = value;
                } else if (key.startsWith("expire_")) {
                    stageStats.put(key, value);
                } else {
                    channelStats.put(key, value);
                }
            }

            stats.setTotalSentToday(total);
            stats.setChannelStats(channelStats);
            stats.setStageStats(stageStats);
            stats.setEnabled(enableNotification);
            stats.setDefaultChannels(getDefaultChannels().stream()
                    .map(NotificationChannel::getCode).collect(Collectors.toList()));

            for (ReminderStage stage : ReminderStage.values()) {
                stageStats.putIfAbsent(stage.getCode(), 0);
            }
            stats.setStageStats(stageStats);

        } catch (Exception e) {
            log.error("Failed to get notification statistics", e);
        }

        return stats;
    }

    public List<NotificationContent> getInAppMessages(String userId, int limit) {
        List<NotificationContent> messages = new ArrayList<>();
        String pattern = "notify:inapp:" + userId + ":*";

        try {
            Set<String> keys = redisTemplate.keys(pattern);
            if (keys != null) {
                List<String> sortedKeys = new ArrayList<>(keys);
                Collections.sort(sortedKeys, Collections.reverseOrder());

                for (String key : sortedKeys.subList(0, Math.min(limit, sortedKeys.size()))) {
                    String json = redisTemplate.opsForList().index(key, 0);
                    if (json != null) {
                        messages.add(JSON.parseObject(json, NotificationContent.class));
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to get in-app messages for user: {}", userId, e);
        }

        return messages;
    }

    public boolean sendCustomExpiryReminder(String distributionId) {
        try {
            Optional<CouponDistribution> opt = distributionRepository.findById(distributionId);
            if (opt.isEmpty()) {
                log.warn("Coupon distribution not found: {}", distributionId);
                return false;
            }

            CouponDistribution coupon = opt.get();
            LocalDateTime now = LocalDateTime.now();
            long hoursUntilExpiry = ChronoUnit.HOURS.between(now, coupon.getExpireTime());

            ReminderStage stage;
            if (hoursUntilExpiry <= 2) {
                stage = ReminderStage.TWO_HOURS;
            } else if (hoursUntilExpiry <= 24) {
                stage = ReminderStage.ONE_DAY;
            } else {
                stage = ReminderStage.THREE_DAYS;
            }

            return sendExpiryReminder(coupon, stage);

        } catch (Exception e) {
            log.error("Failed to send custom expiry reminder: {}", distributionId, e);
            return false;
        }
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class NotificationContent implements Serializable {
        private static final long serialVersionUID = 1L;
        private String title;
        private String message;
        private String couponCode;
        private BigDecimal denomination;
        private LocalDateTime expireTime;
        private String stage;
        private String distributionId;
        private String deepLink;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class NotificationStatistics implements Serializable {
        private static final long serialVersionUID = 1L;
        private int totalSentToday;
        private Map<String, Integer> channelStats;
        private Map<String, Integer> stageStats;
        private boolean enabled;
        private List<String> defaultChannels;
    }
}
