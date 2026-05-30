package com.tracing.staining.interceptor;

import com.tracing.staining.analysis.StainingAnalysisCollector;
import com.tracing.staining.constant.TraceConstant;
import com.tracing.staining.context.BizTagInjector;
import com.tracing.staining.context.CrossCloudTraceManager;
import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import com.tracing.staining.sampler.AdaptiveTraceSampler;
import com.tracing.staining.sampler.TraceSampler;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class TraceEntryInterceptor implements HandlerInterceptor {

    private final TraceSampler traceSampler;
    private final BizTagInjector bizTagInjector;
    private final CrossCloudTraceManager crossCloudTraceManager;
    private final StainingAnalysisCollector analysisCollector;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        try {
            Map<String, String> headers = extractHeaders(request);

            StainingContext context = TraceContextHolder.createContext(headers);

            if (context.getStainingFlag() == null || !context.getStainingFlag()) {
                boolean shouldStain = traceSampler.shouldStain(request, context);
                context.setStainingFlag(shouldStain);
                if (shouldStain) {
                    context.setStainingColor(traceSampler.assignStainingColor(request, context));
                    log.debug("Auto-staining request: traceId={}, color={}",
                            context.getTraceId(), context.getStainingColor());
                }
            }

            if (context.getSampled() == null) {
                context.setSampled(traceSampler.shouldSample(request, context));
            }

            bizTagInjector.injectBizTags(request, context);

            crossCloudTraceManager.handleCrossCloudContext(request, context);

            TraceContextHolder.setContext(context);
            TraceContextHolder.createAndSetOtelSpan(request.getMethod() + ":" + request.getRequestURI());

            enrichResponseHeaders(response, context);

            if (traceSampler instanceof AdaptiveTraceSampler) {
                AdaptiveTraceSampler adaptiveSampler = (AdaptiveTraceSampler) traceSampler;
                response.setHeader("X-Current-Qps", String.valueOf(adaptiveSampler.getCurrentQps()));
                response.setHeader("X-Current-Concurrency", String.valueOf(adaptiveSampler.getCurrentConcurrency()));
                response.setHeader("X-Current-Sample-Rate", String.format("%.2f", adaptiveSampler.getCurrentSampleRate()));
                response.setHeader("X-Current-Staining-Rate", String.format("%.2f", adaptiveSampler.getCurrentStainingRate()));
            }

            if (Boolean.TRUE.equals(context.getStainingFlag())) {
                analysisCollector.collectRequest(context, request.getRequestURI(), request.getMethod());
            }

            log.debug("Trace context set: traceId={}, spanId={}, staining={}, color={}, bizTag={}, crossCloudTraceId={}",
                    context.getTraceId(), context.getSpanId(),
                    context.getStainingFlag(), context.getStainingColor(),
                    context.getBizTag(), context.getCrossCloudTraceId());

        } catch (Exception e) {
            log.error("Failed to set trace context", e);
        }
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                Object handler, Exception ex) {
        try {
            TraceContextHolder.endOtelSpan();

            StainingContext context = TraceContextHolder.getContext();
            if (context != null && Boolean.TRUE.equals(context.getStainingFlag())) {
                String errorMessage = ex != null ? ex.getMessage() : null;
                if (errorMessage == null && response.getStatus() >= 400) {
                    errorMessage = "HTTP " + response.getStatus();
                }
                analysisCollector.collectResponse(context.getTraceId(), response.getStatus(), errorMessage);
            }
        } finally {
            TraceContextHolder.removeContext();
            if (traceSampler instanceof AdaptiveTraceSampler) {
                ((AdaptiveTraceSampler) traceSampler).decrementRequest();
            }
        }
    }

    private Map<String, String> extractHeaders(HttpServletRequest request) {
        Map<String, String> headers = new HashMap<>();
        Enumeration<String> headerNames = request.getHeaderNames();
        while (headerNames.hasMoreElements()) {
            String headerName = headerNames.nextElement();
            headers.put(headerName, request.getHeader(headerName));
        }
        return headers;
    }

    private void enrichResponseHeaders(HttpServletResponse response, StainingContext context) {
        if (context.getTraceId() != null) {
            response.setHeader(TraceConstant.TRACE_ID, context.getTraceId());
        }
        if (context.getSpanId() != null) {
            response.setHeader(TraceConstant.SPAN_ID, context.getSpanId());
        }
        if (context.getRequestId() != null) {
            response.setHeader(TraceConstant.REQUEST_ID, context.getRequestId());
        }
        if (context.getStainingFlag() != null) {
            response.setHeader(TraceConstant.STAINING_FLAG, context.getStainingFlag().toString());
        }
        if (context.getStainingColor() != null) {
            response.setHeader(TraceConstant.STAINING_COLOR, context.getStainingColor());
        }
    }
}
