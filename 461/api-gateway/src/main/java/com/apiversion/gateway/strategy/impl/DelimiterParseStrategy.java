package com.apiversion.gateway.strategy.impl;

import com.apiversion.gateway.strategy.HeaderParseStrategy;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class DelimiterParseStrategy implements HeaderParseStrategy {

    @Override
    public String getStrategyName() {
        return "DELIMITER";
    }

    @Override
    public String parse(String headerValue, String pattern) {
        if (!StringUtils.hasText(headerValue) || !StringUtils.hasText(pattern)) {
            return null;
        }
        String[] parts = headerValue.split(pattern);
        if (parts.length > 0) {
            return parts[0].trim();
        }
        return null;
    }
}
