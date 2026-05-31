package com.drill.platform.sentinel;

import com.alibaba.csp.sentinel.slots.block.Rule;
import lombok.Data;

@Data
public class SentinelResult {

    private boolean passed;
    private boolean blocked;
    private String fallbackResponse;
    private Rule blockRule;

    private SentinelResult() {}

    public static SentinelResult passed(Object entry) {
        SentinelResult result = new SentinelResult();
        result.setPassed(true);
        result.setBlocked(false);
        return result;
    }

    public static SentinelResult blocked(String fallbackResponse, Rule rule) {
        SentinelResult result = new SentinelResult();
        result.setPassed(false);
        result.setBlocked(true);
        result.setFallbackResponse(fallbackResponse);
        result.setBlockRule(rule);
        return result;
    }
}
