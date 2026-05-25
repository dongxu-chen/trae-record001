package com.riskcontrol.flink.alarm;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class AlarmListener {

    private static final Logger logger = LoggerFactory.getLogger(AlarmListener.class);

    private static final String ALARM_CACHE_PREFIX = "risk:alarm:";
    private static final long ALARM_EXPIRE_HOURS = 24;

    private final StringRedisTemplate stringRedisTemplate;

    @Autowired(required = false)
    public AlarmListener(StringRedisTemplate stringRedisTemplate) {
        this.stringRedisTemplate = stringRedisTemplate;
    }

    @KafkaListener(topics = "risk-alarms", groupId = "risk-control-alarm-group")
    public void handleAlarm(ConsumerRecord<String, String> record) {
        try {
            String alarmJson = record.value();
            JSONObject alarm = JSON.parseObject(alarmJson);

            String type = alarm.getString("type");
            String severity = alarm.getString("severity");
            long timestamp = alarm.getLongValue("timestamp");

            logger.warn("Received risk alarm - Type: {}, Severity: {}, Timestamp: {}",
                    type, severity, timestamp);
            logger.debug("Alarm details: {}", alarmJson);

            cacheAlarm(alarm);
            processAlarm(alarm);

        } catch (Exception e) {
            logger.error("Error processing alarm: {}", record.value(), e);
        }
    }

    private void cacheAlarm(JSONObject alarm) {
        if (stringRedisTemplate == null) {
            return;
        }

        try {
            String type = alarm.getString("type");
            String key = type != null ? type : "UNKNOWN";
            long timestamp = alarm.getLongValue("timestamp");
            String cacheKey = ALARM_CACHE_PREFIX + key + ":" + timestamp;

            stringRedisTemplate.opsForValue().set(
                    cacheKey,
                    alarm.toJSONString(),
                    ALARM_EXPIRE_HOURS,
                    TimeUnit.HOURS
            );

            String countKey = ALARM_CACHE_PREFIX + "count:" + key;
            stringRedisTemplate.opsForValue().increment(countKey);
            stringRedisTemplate.expire(countKey, ALARM_EXPIRE_HOURS, TimeUnit.HOURS);

        } catch (Exception e) {
            logger.error("Error caching alarm", e);
        }
    }

    private void processAlarm(JSONObject alarm) {
        String type = alarm.getString("type");
        String severity = alarm.getString("severity");

        if ("CRITICAL".equals(severity)) {
            String userId = alarm.getString("userId");
            String deviceId = alarm.getString("deviceId");
            if (userId != null) {
                logger.error("CRITICAL alarm for user {}: {}", userId, alarm.toJSONString());
            }
            if (deviceId != null) {
                logger.error("CRITICAL alarm for device {}: {}", deviceId, alarm.toJSONString());
            }
        }

        switch (type) {
            case "IP_CHANGE_DETECTION":
                handleIpChangeAlarm(alarm);
                break;
            case "DEVICE_SHARING_DETECTION":
                handleDeviceSharingAlarm(alarm);
                break;
            case "LOGIN_FREQUENCY_ALARM":
                handleLoginFrequencyAlarm(alarm);
                break;
            case "ANOMALY_EVENT_FREQUENCY":
                handleAnomalyAlarm(alarm);
                break;
            default:
                logger.debug("No specific handler for alarm type: {}", type);
        }
    }

    private void handleIpChangeAlarm(JSONObject alarm) {
        String userId = alarm.getString("userId");
        int ipCount = alarm.getIntValue("ipCount");
        if (ipCount >= 5) {
            logger.error("Extreme IP changes detected for user {}: {} IPs", userId, ipCount);
        }
    }

    private void handleDeviceSharingAlarm(JSONObject alarm) {
        String deviceId = alarm.getString("deviceId");
        int userCount = alarm.getIntValue("userCount");
        if (userCount >= 10) {
            logger.error("Massive device sharing detected for device {}: {} users", deviceId, userCount);
        }
    }

    private void handleLoginFrequencyAlarm(JSONObject alarm) {
        String userId = alarm.getString("userId");
        int loginCount = alarm.getIntValue("loginCount");
        logger.warn("High login frequency for user {}: {} logins in 5 minutes", userId, loginCount);
    }

    private void handleAnomalyAlarm(JSONObject alarm) {
        String key = alarm.getString("key");
        int count = alarm.getIntValue("count");
        logger.warn("Anomaly event frequency detected for key {}: {} events", key, count);
    }
}
