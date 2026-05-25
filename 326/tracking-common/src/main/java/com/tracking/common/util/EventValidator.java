package com.tracking.common.util;

import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.TrackEvent;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

public class EventValidator {

    private static final Pattern EVENT_NAME_PATTERN = Pattern.compile("^[a-zA-Z][a-zA-Z0-9_]{1,63}$");
    private static final int MAX_PROPERTIES_SIZE = 100;
    private static final int MAX_PROPERTY_KEY_LENGTH = 64;
    private static final int MAX_PROPERTY_VALUE_LENGTH = 1024;

    public static class ValidationResult {
        private boolean valid;
        private final List<String> errors;

        private ValidationResult(boolean valid, List<String> errors) {
            this.valid = valid;
            this.errors = errors;
        }

        public static ValidationResult ok() {
            return new ValidationResult(true, new ArrayList<>());
        }

        public static ValidationResult error(String message) {
            List<String> errors = new ArrayList<>();
            errors.add(message);
            return new ValidationResult(false, errors);
        }

        public boolean isValid() {
            return valid;
        }

        public List<String> getErrors() {
            return errors;
        }

        public void addError(String error) {
            this.errors.add(error);
            this.valid = false;
        }
    }

    public static ValidationResult validate(TrackEvent event) {
        ValidationResult result = ValidationResult.ok();

        if (event == null) {
            return ValidationResult.error("事件不能为空");
        }

        if (!StringUtils.hasText(event.getEvent())) {
            result.addError("事件名称不能为空");
        } else if (!EVENT_NAME_PATTERN.matcher(event.getEvent()).matches()) {
            result.addError("事件名称格式不正确，必须以字母开头，只能包含字母、数字和下划线，长度2-64");
        }

        if (event.getTimestamp() == null) {
            result.addError("时间戳不能为空");
        } else {
            long now = System.currentTimeMillis();
            long maxDelay = TrackingConstants.EVENT_MAX_DELAY_HOURS * 60 * 60 * 1000L;
            if (event.getTimestamp() > now + 60000) {
                result.addError("时间戳不能晚于当前时间");
            } else if (event.getTimestamp() < now - maxDelay) {
                result.addError("时间戳不能早于" + TrackingConstants.EVENT_MAX_DELAY_HOURS + "小时前");
            }
        }

        if (!StringUtils.hasText(event.getAnonymousId()) && !StringUtils.hasText(event.getUserId())
                && !StringUtils.hasText(event.getDeviceId())) {
            result.addError("anonymousId、userId、deviceId不能同时为空");
        }

        if (event.getProperties() != null && event.getProperties().size() > MAX_PROPERTIES_SIZE) {
            result.addError("属性数量不能超过" + MAX_PROPERTIES_SIZE + "个");
        }

        if (event.getProperties() != null) {
            event.getProperties().forEach((key, value) -> {
                if (key.length() > MAX_PROPERTY_KEY_LENGTH) {
                    result.addError("属性键长度不能超过" + MAX_PROPERTY_KEY_LENGTH + "字符: " + key);
                }
                if (value != null && value.toString().length() > MAX_PROPERTY_VALUE_LENGTH) {
                    result.addError("属性值长度不能超过" + MAX_PROPERTY_VALUE_LENGTH + "字符: " + key);
                }
            });
        }

        if (StringUtils.hasText(event.getAppId()) && event.getAppId().length() > 64) {
            result.addError("appId长度不能超过64字符");
        }

        return result;
    }

    public static boolean isValid(TrackEvent event) {
        return validate(event).isValid();
    }
}
