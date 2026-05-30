package com.tracing.staining.context;

import com.tracing.staining.constant.TraceConstant;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.SpanContext;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Context;
import io.opentelemetry.context.Scope;
import org.slf4j.MDC;

import java.util.Map;
import java.util.UUID;

public class TraceContextHolder {

    private static final ThreadLocal<StainingContext> STAINING_CONTEXT_THREAD_LOCAL = new TransmittableThreadLocal<>();

    private static final ThreadLocal<Context> OTEL_CONTEXT_THREAD_LOCAL = new TransmittableThreadLocal<>();

    private static final ThreadLocal<Scope> OTEL_SCOPE_THREAD_LOCAL = new TransmittableThreadLocal<>();

    private static OpenTelemetry openTelemetry;

    private static Tracer tracer;

    private TraceContextHolder() {
    }

    public static void setOpenTelemetry(OpenTelemetry openTelemetry) {
        TraceContextHolder.openTelemetry = openTelemetry;
        TraceContextHolder.tracer = openTelemetry.getTracer("trace-staining", "1.0.0");
    }

    public static StainingContext getContext() {
        return STAINING_CONTEXT_THREAD_LOCAL.get();
    }

    public static void setContext(StainingContext context) {
        STAINING_CONTEXT_THREAD_LOCAL.set(context);
        bindToMdc(context);
    }

    public static void removeContext() {
        StainingContext context = STAINING_CONTEXT_THREAD_LOCAL.get();
        STAINING_CONTEXT_THREAD_LOCAL.remove();
        clearMdc();
        Scope scope = OTEL_SCOPE_THREAD_LOCAL.get();
        if (scope != null) {
            scope.close();
            OTEL_SCOPE_THREAD_LOCAL.remove();
        }
        OTEL_CONTEXT_THREAD_LOCAL.remove();
    }

    public static Context getOtelContext() {
        return OTEL_CONTEXT_THREAD_LOCAL.get();
    }

    public static Scope getOtelScope() {
        return OTEL_SCOPE_THREAD_LOCAL.get();
    }

    public static StainingContext createContext(Map<String, String> headers) {
        String traceId = headers.get(TraceConstant.TRACE_ID);
        String spanId = headers.get(TraceConstant.SPAN_ID);
        String parentSpanId = headers.get(TraceConstant.PARENT_SPAN_ID);
        String stainingFlagStr = headers.get(TraceConstant.STAINING_FLAG);
        String stainingColor = headers.get(TraceConstant.STAINING_COLOR);
        String userId = headers.get(TraceConstant.STAINING_USER_ID);
        String bizType = headers.get(TraceConstant.STAINING_BIZ_TYPE);
        String bizTag = headers.get(TraceConstant.STAINING_BIZ_TAG);
        String bizTagVersion = headers.get(TraceConstant.STAINING_BIZ_TAG_VERSION);
        String sampledStr = headers.get(TraceConstant.SAMPLED);
        String requestId = headers.get(TraceConstant.REQUEST_ID);
        String cloudProvider = headers.get(TraceConstant.CLOUD_PROVIDER);
        String cloudRegion = headers.get(TraceConstant.CLOUD_REGION);
        String cloudAZ = headers.get(TraceConstant.CLOUD_AVAILABILITY_ZONE);
        String cloudAccountId = headers.get(TraceConstant.CLOUD_ACCOUNT_ID);
        String cloudServiceName = headers.get(TraceConstant.CLOUD_SERVICE_NAME);
        String originTraceId = headers.get(TraceConstant.ORIGIN_TRACE_ID);
        String crossCloudTraceId = headers.get(TraceConstant.CROSS_CLOUD_TRACE_ID);

        if (traceId == null || traceId.isEmpty()) {
            traceId = generateTraceId();
        }
        if (requestId == null || requestId.isEmpty()) {
            requestId = generateRequestId();
        }

        StainingContext context = StainingContext.builder()
                .traceId(traceId)
                .spanId(spanId)
                .parentSpanId(parentSpanId)
                .stainingFlag(Boolean.parseBoolean(stainingFlagStr != null ? stainingFlagStr : "false"))
                .stainingColor(stainingColor)
                .userId(userId)
                .bizType(bizType)
                .bizTag(bizTag)
                .bizTagVersion(bizTagVersion)
                .sampled(Boolean.parseBoolean(sampledStr != null ? sampledStr : "true"))
                .requestId(requestId)
                .timestamp(System.currentTimeMillis())
                .cloudProvider(cloudProvider)
                .cloudRegion(cloudRegion)
                .cloudAZ(cloudAZ)
                .cloudAccountId(cloudAccountId)
                .cloudServiceName(cloudServiceName)
                .originTraceId(originTraceId)
                .crossCloudTraceId(crossCloudTraceId)
                .build();

        for (Map.Entry<String, String> entry : headers.entrySet()) {
            if (isBizTagHeader(entry.getKey())) {
                context.addBizTag(entry.getKey(), entry.getValue());
            } else if (isExtraHeader(entry.getKey())) {
                context.addExtraAttribute(entry.getKey(), entry.getValue());
            }
        }

        return context;
    }

    public static StainingContext createNewContext(boolean stainingFlag, String stainingColor,
                                                   String userId, String bizType) {
        return StainingContext.builder()
                .traceId(generateTraceId())
                .spanId(generateSpanId())
                .stainingFlag(stainingFlag)
                .stainingColor(stainingColor)
                .userId(userId)
                .bizType(bizType)
                .sampled(true)
                .requestId(generateRequestId())
                .timestamp(System.currentTimeMillis())
                .build();
    }

    public static void createAndSetOtelSpan(String spanName) {
        StainingContext stainingContext = getContext();
        if (stainingContext == null || tracer == null) {
            return;
        }

        Span.Builder spanBuilder = tracer.spanBuilder(spanName);

        if (stainingContext.getTraceId() != null && stainingContext.getSpanId() != null) {
            SpanContext parentSpanContext = SpanContext.create(
                    stainingContext.getTraceId(),
                    stainingContext.getSpanId(),
                    stainingContext.getSampled() ? io.opentelemetry.api.trace.TraceFlags.getSampled()
                            : io.opentelemetry.api.trace.TraceFlags.getDefault(),
                    io.opentelemetry.api.trace.TraceState.getDefault()
            );
            spanBuilder.setParent(Context.current().with(Span.wrap(parentSpanContext)));
        }

        if (stainingContext.getStainingFlag() != null) {
            spanBuilder.setAttribute("staining.flag", stainingContext.getStainingFlag());
        }
        if (stainingContext.getStainingColor() != null) {
            spanBuilder.setAttribute("staining.color", stainingContext.getStainingColor());
        }
        if (stainingContext.getUserId() != null) {
            spanBuilder.setAttribute("user.id", stainingContext.getUserId());
        }
        if (stainingContext.getBizType() != null) {
            spanBuilder.setAttribute("biz.type", stainingContext.getBizType());
        }
        if (stainingContext.getBizTag() != null) {
            spanBuilder.setAttribute("biz.tag", stainingContext.getBizTag());
        }
        if (stainingContext.getBizTagVersion() != null) {
            spanBuilder.setAttribute("biz.tag.version", stainingContext.getBizTagVersion());
        }
        if (stainingContext.getRequestId() != null) {
            spanBuilder.setAttribute("request.id", stainingContext.getRequestId());
        }
        if (stainingContext.getCloudProvider() != null) {
            spanBuilder.setAttribute("cloud.provider", stainingContext.getCloudProvider());
        }
        if (stainingContext.getCloudRegion() != null) {
            spanBuilder.setAttribute("cloud.region", stainingContext.getCloudRegion());
        }
        if (stainingContext.getCloudAZ() != null) {
            spanBuilder.setAttribute("cloud.az", stainingContext.getCloudAZ());
        }
        if (stainingContext.getCloudAccountId() != null) {
            spanBuilder.setAttribute("cloud.account.id", stainingContext.getCloudAccountId());
        }
        if (stainingContext.getCloudServiceName() != null) {
            spanBuilder.setAttribute("cloud.service.name", stainingContext.getCloudServiceName());
        }
        if (stainingContext.getCrossCloudTraceId() != null) {
            spanBuilder.setAttribute("cross.cloud.trace.id", stainingContext.getCrossCloudTraceId());
        }
        if (stainingContext.getOriginTraceId() != null) {
            spanBuilder.setAttribute("origin.trace.id", stainingContext.getOriginTraceId());
        }

        Span span = spanBuilder.startSpan();
        Context context = Context.current().with(span);
        Scope scope = context.makeCurrent();

        OTEL_CONTEXT_THREAD_LOCAL.set(context);
        OTEL_SCOPE_THREAD_LOCAL.set(scope);

        stainingContext.setSpanId(span.getSpanContext().getSpanId());
        stainingContext.setTraceId(span.getSpanContext().getTraceId());
        setContext(stainingContext);
    }

    public static void endOtelSpan() {
        Scope scope = OTEL_SCOPE_THREAD_LOCAL.get();
        if (scope != null) {
            scope.close();
            OTEL_SCOPE_THREAD_LOCAL.remove();
        }

        Context context = OTEL_CONTEXT_THREAD_LOCAL.get();
        if (context != null) {
            Span span = Span.fromContext(context);
            if (span != null) {
                span.end();
            }
            OTEL_CONTEXT_THREAD_LOCAL.remove();
        }
    }

    public static StainingContext copyContext() {
        StainingContext current = getContext();
        if (current == null) {
            return null;
        }
        return StainingContext.builder()
                .traceId(current.getTraceId())
                .spanId(current.getSpanId())
                .parentSpanId(current.getSpanId())
                .stainingFlag(current.getStainingFlag())
                .stainingColor(current.getStainingColor())
                .userId(current.getUserId())
                .bizType(current.getBizType())
                .sampled(current.getSampled())
                .requestId(current.getRequestId())
                .timestamp(current.getTimestamp())
                .extraAttributes(current.getExtraAttributes())
                .build();
    }

    public static StainingContext createChildContext() {
        StainingContext current = getContext();
        if (current == null) {
            return createNewContext(false, null, null, null);
        }
        return StainingContext.builder()
                .traceId(current.getTraceId())
                .spanId(generateSpanId())
                .parentSpanId(current.getSpanId())
                .stainingFlag(current.getStainingFlag())
                .stainingColor(current.getStainingColor())
                .userId(current.getUserId())
                .bizType(current.getBizType())
                .sampled(current.getSampled())
                .requestId(current.getRequestId())
                .timestamp(System.currentTimeMillis())
                .extraAttributes(current.getExtraAttributes())
                .build();
    }

    public static String generateTraceId() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    public static String generateSpanId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    public static String generateRequestId() {
        return UUID.randomUUID().toString();
    }

    private static boolean isBizTagHeader(String headerName) {
        return headerName.startsWith("X-Biz-") || headerName.startsWith("X-Custom-");
    }

    private static boolean isExtraHeader(String headerName) {
        return !headerName.equalsIgnoreCase(TraceConstant.TRACE_ID)
                && !headerName.equalsIgnoreCase(TraceConstant.SPAN_ID)
                && !headerName.equalsIgnoreCase(TraceConstant.PARENT_SPAN_ID)
                && !headerName.equalsIgnoreCase(TraceConstant.STAINING_FLAG)
                && !headerName.equalsIgnoreCase(TraceConstant.STAINING_COLOR)
                && !headerName.equalsIgnoreCase(TraceConstant.STAINING_USER_ID)
                && !headerName.equalsIgnoreCase(TraceConstant.STAINING_BIZ_TYPE)
                && !headerName.equalsIgnoreCase(TraceConstant.STAINING_BIZ_TAG)
                && !headerName.equalsIgnoreCase(TraceConstant.STAINING_BIZ_TAG_VERSION)
                && !headerName.equalsIgnoreCase(TraceConstant.SAMPLED)
                && !headerName.equalsIgnoreCase(TraceConstant.REQUEST_ID)
                && !headerName.equalsIgnoreCase(TraceConstant.CLOUD_PROVIDER)
                && !headerName.equalsIgnoreCase(TraceConstant.CLOUD_REGION)
                && !headerName.equalsIgnoreCase(TraceConstant.CLOUD_AVAILABILITY_ZONE)
                && !headerName.equalsIgnoreCase(TraceConstant.CLOUD_ACCOUNT_ID)
                && !headerName.equalsIgnoreCase(TraceConstant.CLOUD_SERVICE_NAME)
                && !headerName.equalsIgnoreCase(TraceConstant.ORIGIN_TRACE_ID)
                && !headerName.equalsIgnoreCase(TraceConstant.CROSS_CLOUD_TRACE_ID)
                && !isBizTagHeader(headerName);
    }

    private static void bindToMdc(StainingContext context) {
        if (context == null) {
            return;
        }
        if (context.getTraceId() != null) {
            MDC.put(TraceConstant.TRACE_ID, context.getTraceId());
        }
        if (context.getSpanId() != null) {
            MDC.put(TraceConstant.SPAN_ID, context.getSpanId());
        }
        if (context.getRequestId() != null) {
            MDC.put(TraceConstant.REQUEST_ID, context.getRequestId());
        }
        if (context.getUserId() != null) {
            MDC.put(TraceConstant.STAINING_USER_ID, context.getUserId());
        }
    }

    private static void clearMdc() {
        MDC.remove(TraceConstant.TRACE_ID);
        MDC.remove(TraceConstant.SPAN_ID);
        MDC.remove(TraceConstant.REQUEST_ID);
        MDC.remove(TraceConstant.STAINING_USER_ID);
    }

    public static String getCurrentTraceId() {
        StainingContext context = getContext();
        if (context != null && context.getTraceId() != null) {
            return context.getTraceId();
        }
        Span span = Span.current();
        if (span != null && span.getSpanContext().isValid()) {
            return span.getSpanContext().getTraceId();
        }
        return null;
    }

    public static String getCurrentSpanId() {
        StainingContext context = getContext();
        if (context != null && context.getSpanId() != null) {
            return context.getSpanId();
        }
        Span span = Span.current();
        if (span != null && span.getSpanContext().isValid()) {
            return span.getSpanContext().getSpanId();
        }
        return null;
    }

    public static boolean isStainingEnabled() {
        StainingContext context = getContext();
        return context != null && Boolean.TRUE.equals(context.getStainingFlag());
    }
}
