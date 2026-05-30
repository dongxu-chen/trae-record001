package com.tracing.staining.context;

import com.tracing.staining.constant.TraceConstant;
import lombok.extern.slf4j.Slf4j;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@Slf4j
public class TraceHeaderAccessor {

    private TraceHeaderAccessor() {
    }

    public static Map<String, String> extractContextHeaders(Map<String, ?> headers) {
        Map<String, String> contextHeaders = new HashMap<>();
        if (headers == null || headers.isEmpty()) {
            return contextHeaders;
        }

        addIfPresent(contextHeaders, headers, TraceConstant.TRACE_ID);
        addIfPresent(contextHeaders, headers, TraceConstant.SPAN_ID);
        addIfPresent(contextHeaders, headers, TraceConstant.PARENT_SPAN_ID);
        addIfPresent(contextHeaders, headers, TraceConstant.STAINING_FLAG);
        addIfPresent(contextHeaders, headers, TraceConstant.STAINING_COLOR);
        addIfPresent(contextHeaders, headers, TraceConstant.STAINING_USER_ID);
        addIfPresent(contextHeaders, headers, TraceConstant.STAINING_BIZ_TYPE);
        addIfPresent(contextHeaders, headers, TraceConstant.SAMPLED);
        addIfPresent(contextHeaders, headers, TraceConstant.REQUEST_ID);

        for (Map.Entry<String, ?> entry : headers.entrySet()) {
            String key = entry.getKey();
            if (isTraceHeader(key) && !contextHeaders.containsKey(key)) {
                addIfPresent(contextHeaders, headers, key);
            }
        }

        return contextHeaders;
    }

    public static Map<String, byte[]> toBinaryHeaders(StainingContext context) {
        Map<String, byte[]> headers = new HashMap<>();
        if (context == null) {
            return headers;
        }

        addHeaderIfNotNull(headers, TraceConstant.TRACE_ID, context.getTraceId());
        addHeaderIfNotNull(headers, TraceConstant.SPAN_ID, context.getSpanId());
        addHeaderIfNotNull(headers, TraceConstant.PARENT_SPAN_ID, context.getParentSpanId());
        addHeaderIfNotNull(headers, TraceConstant.STAINING_FLAG,
                context.getStainingFlag() != null ? context.getStainingFlag().toString() : null);
        addHeaderIfNotNull(headers, TraceConstant.STAINING_COLOR, context.getStainingColor());
        addHeaderIfNotNull(headers, TraceConstant.STAINING_USER_ID, context.getUserId());
        addHeaderIfNotNull(headers, TraceConstant.STAINING_BIZ_TYPE, context.getBizType());
        addHeaderIfNotNull(headers, TraceConstant.SAMPLED,
                context.getSampled() != null ? context.getSampled().toString() : null);
        addHeaderIfNotNull(headers, TraceConstant.REQUEST_ID, context.getRequestId());

        if (context.getExtraAttributes() != null) {
            for (Map.Entry<String, String> entry : context.getExtraAttributes().entrySet()) {
                addHeaderIfNotNull(headers, entry.getKey(), entry.getValue());
            }
        }

        return headers;
    }

    public static Map<String, String> toStringHeaders(StainingContext context) {
        Map<String, String> headers = new HashMap<>();
        if (context == null) {
            return headers;
        }

        addHeaderIfNotNullString(headers, TraceConstant.TRACE_ID, context.getTraceId());
        addHeaderIfNotNullString(headers, TraceConstant.SPAN_ID, context.getSpanId());
        addHeaderIfNotNullString(headers, TraceConstant.PARENT_SPAN_ID, context.getParentSpanId());
        addHeaderIfNotNullString(headers, TraceConstant.STAINING_FLAG,
                context.getStainingFlag() != null ? context.getStainingFlag().toString() : null);
        addHeaderIfNotNullString(headers, TraceConstant.STAINING_COLOR, context.getStainingColor());
        addHeaderIfNotNullString(headers, TraceConstant.STAINING_USER_ID, context.getUserId());
        addHeaderIfNotNullString(headers, TraceConstant.STAINING_BIZ_TYPE, context.getBizType());
        addHeaderIfNotNullString(headers, TraceConstant.SAMPLED,
                context.getSampled() != null ? context.getSampled().toString() : null);
        addHeaderIfNotNullString(headers, TraceConstant.REQUEST_ID, context.getRequestId());

        if (context.getExtraAttributes() != null) {
            for (Map.Entry<String, String> entry : context.getExtraAttributes().entrySet()) {
                addHeaderIfNotNullString(headers, entry.getKey(), entry.getValue());
            }
        }

        return headers;
    }

    public static <T> void injectToHeaders(T headers, HeaderInjector<T> injector) {
        StainingContext context = TraceContextHolder.getContext();
        if (context == null) {
            log.debug("No staining context available, skipping header injection");
            return;
        }

        StainingContext childContext = TraceContextHolder.createChildContext();
        Map<String, String> headerValues = toStringHeaders(childContext);

        for (Map.Entry<String, String> entry : headerValues.entrySet()) {
            if (!injector.containsHeader(headers, entry.getKey())) {
                injector.injectHeader(headers, entry.getKey(), entry.getValue());
            }
        }

        log.debug("Trace headers injected: traceId={}, spanId={}, staining={}",
                childContext.getTraceId(), childContext.getSpanId(),
                childContext.getStainingFlag());
    }

    public static <T> StainingContext extractFromHeaders(T headers, HeaderExtractor<T> extractor) {
        Map<String, String> headerValues = new HashMap<>();
        extractor.forEachHeader(headers, (key, value) -> {
            if (isTraceHeader(key) && value != null) {
                headerValues.put(key, value.toString());
            }
        });

        if (headerValues.isEmpty()) {
            log.debug("No trace headers found in message");
            return null;
        }

        StainingContext context = TraceContextHolder.createContext(headerValues);
        log.debug("Trace context extracted from headers: traceId={}, spanId={}",
                context.getTraceId(), context.getSpanId());
        return context;
    }

    public static boolean isTraceHeader(String headerName) {
        if (headerName == null) {
            return false;
        }
        String lowerName = headerName.toLowerCase();
        return lowerName.startsWith("x-")
                || lowerName.equals("traceid")
                || lowerName.equals("spanid")
                || lowerName.equals("parentspanid")
                || lowerName.equals("requestid");
    }

    private static void addIfPresent(Map<String, String> target, Map<String, ?> source, String key) {
        Object value = source.get(key);
        if (value != null) {
            target.put(key, value.toString());
        }
    }

    private static void addHeaderIfNotNull(Map<String, byte[]> headers, String key, String value) {
        if (value != null) {
            headers.put(key, value.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static void addHeaderIfNotNullString(Map<String, String> headers, String key, String value) {
        if (value != null) {
            headers.put(key, value);
        }
    }

    public interface HeaderInjector<T> {
        void injectHeader(T headers, String key, String value);

        boolean containsHeader(T headers, String key);
    }

    public interface HeaderExtractor<T> {
        void forEachHeader(T headers, java.util.function.BiConsumer<String, Object> consumer);
    }
}
