package com.risk.engine.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
public class VariableService {

    public Map<String, Object> calculateVariables(Map<String, Object> data) {
        Map<String, Object> variables = new HashMap<>();
        
        try {
            calculateBasicVariables(data, variables);
            calculateAmountVariables(data, variables);
            calculateDeviceVariables(data, variables);
            calculateBehaviorVariables(data, variables);
        } catch (Exception e) {
            log.error("变量计算异常", e);
        }
        
        return variables;
    }

    private void calculateBasicVariables(Map<String, Object> data, Map<String, Object> variables) {
        Integer loginDays = getIntegerValue(data, "loginDays");
        if (loginDays != null) {
            variables.put("isNewUser", loginDays <= 7);
            variables.put("userLevel", calculateUserLevel(loginDays));
        }
        
        Integer totalOrders = getIntegerValue(data, "totalOrders");
        if (totalOrders != null) {
            variables.put("orderCountLevel", calculateOrderCountLevel(totalOrders));
        }
    }

    private void calculateAmountVariables(Map<String, Object> data, Map<String, Object> variables) {
        BigDecimal orderAmount = getBigDecimalValue(data, "orderAmount");
        if (orderAmount != null) {
            variables.put("isLargeAmount", orderAmount.compareTo(new BigDecimal("10000")) > 0);
            variables.put("amountLevel", calculateAmountLevel(orderAmount));
        }
        
        BigDecimal avgOrderAmount = getBigDecimalValue(data, "avgOrderAmount");
        if (avgOrderAmount != null && orderAmount != null && avgOrderAmount.compareTo(BigDecimal.ZERO) > 0) {
            BigDecimal ratio = orderAmount.divide(avgOrderAmount, 2, BigDecimal.ROUND_HALF_UP);
            variables.put("amountToAvgRatio", ratio);
            variables.put("isAbnormalAmount", ratio.compareTo(new BigDecimal("3")) > 0);
        }
    }

    private void calculateDeviceVariables(Map<String, Object> data, Map<String, Object> variables) {
        String deviceId = getStringValue(data, "deviceId");
        String userDeviceId = getStringValue(data, "userDeviceId");
        if (deviceId != null && userDeviceId != null) {
            variables.put("isDeviceMatched", deviceId.equals(userDeviceId));
        }
        
        Integer deviceLoginCount = getIntegerValue(data, "deviceLoginCount");
        if (deviceLoginCount != null) {
            variables.put("isMultiAccountDevice", deviceLoginCount > 5);
        }
        
        String ip = getStringValue(data, "ip");
        String userRegisterIp = getStringValue(data, "userRegisterIp");
        if (ip != null && userRegisterIp != null) {
            variables.put("isSameCityIp", isSameCity(ip, userRegisterIp));
        }
    }

    private void calculateBehaviorVariables(Map<String, Object> data, Map<String, Object> variables) {
        Integer failedAttempts = getIntegerValue(data, "failedAttempts");
        if (failedAttempts != null) {
            variables.put("hasHighFailedAttempts", failedAttempts >= 3);
        }
        
        Long orderInterval = getLongValue(data, "orderIntervalSeconds");
        if (orderInterval != null) {
            variables.put("isQuickOrder", orderInterval < 60);
        }
        
        Integer pageViews = getIntegerValue(data, "pageViews");
        Integer duration = getIntegerValue(data, "durationSeconds");
        if (pageViews != null && duration != null && duration > 0) {
            double avgViewTime = (double) duration / pageViews;
            variables.put("avgPageViewTime", avgViewTime);
            variables.put("isQuickBrowser", avgViewTime < 3);
        }
    }

    private String calculateUserLevel(int loginDays) {
        if (loginDays <= 7) return "NEW";
        if (loginDays <= 30) return "NORMAL";
        if (loginDays <= 90) return "SENIOR";
        return "VETERAN";
    }

    private String calculateOrderCountLevel(int orderCount) {
        if (orderCount <= 5) return "LOW";
        if (orderCount <= 20) return "MEDIUM";
        if (orderCount <= 50) return "HIGH";
        return "VERY_HIGH";
    }

    private String calculateAmountLevel(BigDecimal amount) {
        if (amount.compareTo(new BigDecimal("100")) < 0) return "SMALL";
        if (amount.compareTo(new BigDecimal("1000")) < 0) return "MEDIUM";
        if (amount.compareTo(new BigDecimal("10000")) < 0) return "LARGE";
        return "HUGE";
    }

    private boolean isSameCity(String ip1, String ip2) {
        return getCityPrefix(ip1).equals(getCityPrefix(ip2));
    }

    private String getCityPrefix(String ip) {
        String[] parts = ip.split("\\.");
        if (parts.length >= 2) {
            return parts[0] + "." + parts[1];
        }
        return ip;
    }

    private Integer getIntegerValue(Map<String, Object> data, String key) {
        Object value = data.get(key);
        if (value == null) return null;
        if (value instanceof Integer) return (Integer) value;
        try {
            return Integer.parseInt(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Long getLongValue(Map<String, Object> data, String key) {
        Object value = data.get(key);
        if (value == null) return null;
        if (value instanceof Long) return (Long) value;
        try {
            return Long.parseLong(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private BigDecimal getBigDecimalValue(Map<String, Object> data, String key) {
        Object value = data.get(key);
        if (value == null) return null;
        if (value instanceof BigDecimal) return (BigDecimal) value;
        try {
            return new BigDecimal(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private String getStringValue(Map<String, Object> data, String key) {
        Object value = data.get(key);
        return value != null ? value.toString() : null;
    }
}
