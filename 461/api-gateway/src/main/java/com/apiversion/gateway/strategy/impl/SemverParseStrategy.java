package com.apiversion.gateway.strategy.impl;

import com.apiversion.gateway.strategy.HeaderParseStrategy;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
public class SemverParseStrategy implements HeaderParseStrategy {

    private static final Pattern SEMVER_PATTERN = Pattern.compile("v?(\\d+)\\.(\\d+)\\.(\\d+)?");

    @Override
    public String getStrategyName() {
        return "SEMVER";
    }

    @Override
    public String parse(String headerValue, String pattern) {
        if (!StringUtils.hasText(headerValue)) {
            return null;
        }
        Matcher matcher = SEMVER_PATTERN.matcher(headerValue);
        if (matcher.find()) {
            String major = matcher.group(1);
            return "v" + major;
        }
        return null;
    }
}
