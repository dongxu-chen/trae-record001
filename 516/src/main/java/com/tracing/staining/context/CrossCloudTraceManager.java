package com.tracing.staining.context;

import com.tracing.staining.constant.TraceConstant;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import jakarta.servlet.http.HttpServletRequest;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class CrossCloudTraceManager {

    private final CloudEnvironmentConfig cloudConfig;

    public void injectCloudInfo(StainingContext context) {
        if (cloudConfig.isCloudConfigured() && context != null) {
            context.setCloudInfo(
                    cloudConfig.getProvider(),
                    cloudConfig.getRegion(),
                    cloudConfig.getAvailabilityZone(),
                    cloudConfig.getAccountId(),
                    cloudConfig.getServiceName()
            );
            log.debug("Cloud info injected: provider={}, region={}, service={}",
                    cloudConfig.getProvider(), cloudConfig.getRegion(), cloudConfig.getServiceName());
        }
    }

    public String generateCrossCloudTraceId() {
        String prefix = cloudConfig.getCrossCloudTraceIdPrefix();
        return prefix + "-" + UUID.randomUUID().toString().replace("-", "");
    }

    public void handleCrossCloudContext(HttpServletRequest request, StainingContext context) {
        if (!cloudConfig.isCrossCloudEnabled()) {
            return;
        }

        String incomingCrossCloudTraceId = request.getHeader(TraceConstant.CROSS_CLOUD_TRACE_ID);
        String incomingOriginTraceId = request.getHeader(TraceConstant.ORIGIN_TRACE_ID);
        String incomingProvider = request.getHeader(TraceConstant.CLOUD_PROVIDER);
        String incomingRegion = request.getHeader(TraceConstant.CLOUD_REGION);

        if (incomingCrossCloudTraceId != null) {
            context.setCrossCloudTraceId(incomingCrossCloudTraceId);
            if (incomingOriginTraceId == null) {
                context.setOriginTraceId(context.getTraceId());
            } else {
                context.setOriginTraceId(incomingOriginTraceId);
            }
            log.info("Cross-cloud request received: crossCloudTraceId={}, from={}/{}",
                    incomingCrossCloudTraceId, incomingProvider, incomingRegion);
        } else {
            String newCrossCloudTraceId = generateCrossCloudTraceId();
            context.setCrossCloudTraceId(newCrossCloudTraceId);
            context.setOriginTraceId(context.getTraceId());
            log.info("New cross-cloud trace created: crossCloudTraceId={}, originTraceId={}",
                    newCrossCloudTraceId, context.getTraceId());
        }

        injectCloudInfo(context);
    }

    public boolean isCrossCloudRequest(HttpServletRequest request) {
        return cloudConfig.isCrossCloudEnabled()
                && request.getHeader(TraceConstant.CROSS_CLOUD_TRACE_ID) != null;
    }

    public CloudEnvironmentConfig getCloudConfig() {
        return cloudConfig;
    }
}
