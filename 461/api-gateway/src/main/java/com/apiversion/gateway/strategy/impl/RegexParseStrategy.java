package com.apiversion.gateway.strategy.impl;

import com.apiversion.gateway.strategy.HeaderParseStrategy;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
public class RegexParseStrategy implements HeaderParseStrategy {

    @Override
    public String getStrategyName() {
        return "REGEX";
    }

    @Override
    public String parse(String headerValue, String pattern) {
        if (!StringUtils.hasText(headerValue) || !StringUtils.hasText(pattern)) {
            return null;
        }
        try {
            Pattern regex = Pattern.compile(pattern);
            Matcher matcher = regex.matcher(headerValue);
            if (matcher.find()) {
                if (matcher.groupCount() > 0) {
                    return matcher.group(1);
                }
                return matcher.group();
            }
        } catch (Exception e) {
            return null;
        }
        return null;
    }
}
