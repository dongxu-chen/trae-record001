package com.apiversion.gateway.strategy.impl;

import com.apiversion.gateway.strategy.HeaderParseStrategy;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class DirectParseStrategy implements HeaderParseStrategy {

    @Override
    public String getStrategyName() {
        return "DIRECT";
    }

    @Override
    public String parse(String headerValue, String pattern) {
        if (!StringUtils.hasText(headerValue)) {
            return null;
        }
        return headerValue.trim();
    }
}
