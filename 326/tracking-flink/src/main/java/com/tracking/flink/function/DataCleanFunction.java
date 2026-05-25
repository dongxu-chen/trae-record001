package com.tracking.flink.function;

import com.alibaba.fastjson2.JSONObject;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.EventValidator;
import com.tracking.common.util.IdGenerator;
import com.tracking.common.util.IPUtil;
import com.tracking.common.util.UserAgentUtil;
import org.apache.flink.api.common.functions.RichMapFunction;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.util.StringUtils;

import java.util.HashMap;
import java.util.Map;

public class DataCleanFunction extends ProcessFunction<TrackEvent, TrackEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(DataCleanFunction.class);

    @Override
    public void processElement(TrackEvent event, Context context, Collector<TrackEvent> collector) {
        try {
            if (!EventValidator.isValid(event)) {
                LOG.debug("Invalid event dropped: {}", event);
                return;
            }

            TrackEvent cleaned = cleanEvent(event);

            if (cleaned != null) {
                collector.collect(cleaned);
            }
        } catch (Exception e) {
            LOG.error("Error cleaning event: {}", event, e);
        }
    }

    private TrackEvent cleanEvent(TrackEvent event) {
        if (event.getId() == null) {
            event.setId(IdGenerator.generateEventId());
        }

        if (event.getTimestamp() == null) {
            event.setTimestamp(System.currentTimeMillis());
        }

        if (event.getReceiveTime() == null) {
            event.setReceiveTime(System.currentTimeMillis());
        }

        event.setEvent(event.getEvent().trim().toLowerCase());

        if (event.getPlatform() != null) {
            event.setPlatform(event.getPlatform().trim().toLowerCase());
        }

        if (event.getUserId() != null) {
            event.setUserId(event.getUserId().trim());
        }

        if (event.getAnonymousId() == null && event.getDeviceId() == null) {
            event.setAnonymousId(IdGenerator.generateAnonymousId());
        } else if (event.getAnonymousId() == null && event.getDeviceId() != null) {
            event.setAnonymousId(IdGenerator.generateAnonymousId());
        }

        if (event.getSessionId() == null) {
            event.setSessionId(IdGenerator.generateSessionId());
        }

        if (event.getIp() != null) {
            event.setIp(IPUtil.maskIP(event.getIp()));
        }

        if (event.getUserAgent() != null && !StringUtils.hasText(event.getOs())) {
            JSONObject uaInfo = UserAgentUtil.parse(event.getUserAgent());
            if (event.getOs() == null) {
                event.setOs(uaInfo.getString("os"));
            }
            if (event.getOsVersion() == null) {
                event.setOsVersion(uaInfo.getString("osVersion"));
            }
            if (event.getDeviceModel() == null) {
                event.setDeviceModel(uaInfo.getString("device"));
            }
            if (event.getPlatform() == null) {
                event.setPlatform(uaInfo.getBooleanValue("isMobile") ? "mobile" : "web");
            }
        }

        if (event.getProperties() == null) {
            event.setProperties(new HashMap<>());
        } else {
            Map<String, Object> cleanedProps = new HashMap<>();
            event.getProperties().forEach((key, value) -> {
                if (key != null && !key.isEmpty() && value != null) {
                    cleanedProps.put(key.trim(), value);
                }
            });
            event.setProperties(cleanedProps);
        }

        if (event.getSource() == null) {
            event.setSource(TrackingConstants.SOURCE_FRONTEND);
        }

        if (UserAgentUtil.isBot(event.getUserAgent())) {
            return null;
        }

        return event;
    }
}
