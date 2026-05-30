package com.tracing.staining.sampler;

import com.tracing.staining.constant.TraceConstant;
import com.tracing.staining.context.StainingContext;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.ThreadLocalRandom;

@Slf4j
@Component
public class DefaultTraceSampler implements TraceSampler {

    @Value("${tracing.sample.rate:1.0}")
    private double sampleRate;

    @Value("${tracing.staining.rate:0.1}")
    private double stainingRate;

    @Value("${tracing.staining.user-ids:}")
    private Set<String> stainingUserIds;

    @Value("${tracing.staining.biz-types:}")
    private Set<String> stainingBizTypes;

    @Value("${tracing.staining.paths:}")
    private List<String> stainingPaths;

    private static final String[] COLORS = {"RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "ORANGE"};

    @Override
    public boolean shouldSample(HttpServletRequest request, StainingContext context) {
        if (context != null && context.getSampled() != null) {
            return context.getSampled();
        }

        if (isStainingRequest(request, context)) {
            return true;
        }

        if (sampleRate >= 1.0) {
            return true;
        }

        if (sampleRate <= 0) {
            return false;
        }

        double random = ThreadLocalRandom.current().nextDouble();
        boolean sampled = random < sampleRate;
        log.debug("Sampling decision: random={}, rate={}, sampled={}", random, sampleRate, sampled);
        return sampled;
    }

    @Override
    public boolean shouldStain(HttpServletRequest request, StainingContext context) {
        if (context != null && Boolean.TRUE.equals(context.getStainingFlag())) {
            return true;
        }

        if (isStainingRequest(request, context)) {
            return true;
        }

        if (stainingRate >= 1.0) {
            return true;
        }

        if (stainingRate <= 0) {
            return false;
        }

        double random = ThreadLocalRandom.current().nextDouble();
        boolean shouldStain = random < stainingRate;
        log.debug("Staining decision: random={}, rate={}, shouldStain={}", random, stainingRate, shouldStain);
        return shouldStain;
    }

    @Override
    public String assignStainingColor(HttpServletRequest request, StainingContext context) {
        if (context != null && context.getStainingColor() != null) {
            return context.getStainingColor();
        }

        if (context != null && context.getUserId() != null && !stainingUserIds.isEmpty()) {
            if (stainingUserIds.contains(context.getUserId())) {
                return "RED";
            }
        }

        if (context != null && context.getBizType() != null && !stainingBizTypes.isEmpty()) {
            if (stainingBizTypes.contains(context.getBizType())) {
                return "BLUE";
            }
        }

        Random random = new Random();
        return COLORS[random.nextInt(COLORS.length)];
    }

    private boolean isStainingRequest(HttpServletRequest request, StainingContext context) {
        if (context != null && context.getUserId() != null && !stainingUserIds.isEmpty()) {
            if (stainingUserIds.contains(context.getUserId())) {
                log.debug("Staining by user ID: {}", context.getUserId());
                return true;
            }
        }

        if (context != null && context.getBizType() != null && !stainingBizTypes.isEmpty()) {
            if (stainingBizTypes.contains(context.getBizType())) {
                log.debug("Staining by biz type: {}", context.getBizType());
                return true;
            }
        }

        if (request != null && !stainingPaths.isEmpty()) {
            String path = request.getRequestURI();
            for (String stainingPath : stainingPaths) {
                if (path.startsWith(stainingPath)) {
                    log.debug("Staining by path: {}", path);
                    return true;
                }
            }
        }

        if (request != null) {
            String stainingFlagHeader = request.getHeader(TraceConstant.STAINING_FLAG);
            if ("true".equalsIgnoreCase(stainingFlagHeader)) {
                log.debug("Staining by header flag");
                return true;
            }
        }

        return false;
    }
}
