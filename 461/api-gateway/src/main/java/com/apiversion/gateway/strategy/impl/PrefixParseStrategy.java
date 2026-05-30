package com.apiversion.gateway.strategy.impl;

import com.apiversion.gateway.strategy.HeaderParseStrategy;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class PrefixParseStrategy implements HeaderParseStrategy {

    @Override
    public String getStrategyName() {
        return "PREFIX";
    }

    @Override
    public String parse(String headerValue, String pattern) {
        if (!StringUtils.hasText(headerValue) || !StringUtils.hasText(pattern)) {
            return null;
        }
        if (headerValue.startsWith(pattern)) {
            return headerValue.substring(pattern.length()).trim();
        }
        return null;
    }
}
