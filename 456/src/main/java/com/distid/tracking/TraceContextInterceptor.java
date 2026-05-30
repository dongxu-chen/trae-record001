package com.distid.tracking;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@Slf4j
@Component
public class TraceContextInterceptor implements HandlerInterceptor {

    private static final String TRACE_HEADER = "X-Trace-Id";
    private static final String SPAN_HEADER = "X-Span-Id";
    private static final String BIZ_TAG_HEADER = "X-Biz-Tag";
    private static final String SOURCE_HEADER = "X-Source";

    private static final ThreadLocal<TraceContext> CONTEXT_HOLDER = new ThreadLocal<>();

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String traceId = request.getHeader(TRACE_HEADER);
        String spanId = request.getHeader(SPAN_HEADER);
        String bizTag = request.getHeader(BIZ_TAG_HEADER);
        String source = request.getHeader(SOURCE_HEADER);

        if (traceId == null || traceId.isEmpty()) {
            traceId = generateTraceId(request);
        }
        if (spanId == null || spanId.isEmpty()) {
            spanId = generateSpanId();
        }

        TraceContext context = TraceContext.builder()
                .traceId(traceId)
                .spanId(spanId)
                .bizTag(bizTag != null ? bizTag : "")
                .requestPath(request.getRequestURI())
                .source(source != null ? source : request.getRemoteAddr())
                .build();

        CONTEXT_HOLDER.set(context);
        response.setHeader(TRACE_HEADER, traceId);
        response.setHeader(SPAN_HEADER, spanId);
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                 Object handler, Exception ex) {
        CONTEXT_HOLDER.remove();
    }

    public static TraceContext currentContext() {
        TraceContext ctx = CONTEXT_HOLDER.get();
        return ctx != null ? ctx : TraceContext.empty();
    }

    private String generateTraceId(HttpServletRequest request) {
        return System.currentTimeMillis() + "-" + Integer.toHexString(request.getRemoteAddr().hashCode()) + "-" + Long.toHexString(System.nanoTime());
    }

    private String generateSpanId() {
        return Long.toHexString(System.nanoTime());
    }
}
