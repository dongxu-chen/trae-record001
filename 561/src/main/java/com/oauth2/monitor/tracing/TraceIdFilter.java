package com.oauth2.monitor.tracing;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;

@Component
public class TraceIdFilter implements Filter {

    private static final String TRACE_ID_HEADER = "X-Trace-Id";
    private static final String PARENT_SPAN_ID_HEADER = "X-Parent-Span-Id";

    private final ObjectProvider<TraceContext> traceContextProvider;

    public TraceIdFilter(ObjectProvider<TraceContext> traceContextProvider) {
        this.traceContextProvider = traceContextProvider;
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws java.io.IOException, jakarta.servlet.ServletException {

        HttpServletRequest httpRequest = (HttpServletRequest) request;
        HttpServletResponse httpResponse = (HttpServletResponse) response;

        TraceContext traceContext = traceContextProvider.getObject();

        String incomingTraceId = httpRequest.getHeader(TRACE_ID_HEADER);
        String parentSpanId = httpRequest.getHeader(PARENT_SPAN_ID_HEADER);

        if (incomingTraceId != null && !incomingTraceId.isEmpty()) {
            traceContext.setTraceId(incomingTraceId);
        }
        if (parentSpanId != null && !parentSpanId.isEmpty()) {
            traceContext.setParentSpanId(parentSpanId);
        }

        String flowId = extractFlowId(httpRequest);
        if (flowId != null) {
            traceContext.setFlowId(flowId);
        }

        String clientId = httpRequest.getParameter("client_id");
        if (clientId != null) {
            traceContext.setClientId(clientId);
        }

        traceContext.putAttribute("requestUri", httpRequest.getRequestURI());
        traceContext.putAttribute("requestMethod", httpRequest.getMethod());
        traceContext.putAttribute("userAgent", httpRequest.getHeader("User-Agent"));
        traceContext.putAttribute("clientIp", getClientIp(httpRequest));

        Map<String, String> mdcContext = traceContext.toMdcContext();
        try {
            mdcContext.forEach(MDC::put);

            httpResponse.setHeader(TRACE_ID_HEADER, traceContext.getTraceId());
            httpResponse.setHeader("X-Span-Id", traceContext.getSpanId());

            chain.doFilter(request, response);

        } finally {
            mdcContext.keySet().forEach(MDC::remove);
        }
    }

    private String extractFlowId(HttpServletRequest request) {
        String state = request.getParameter("state");
        if (state != null && !state.isEmpty()) {
            return state;
        }
        String sessionId = request.getRequestedSessionId();
        return sessionId != null ? sessionId.substring(0, Math.min(16, sessionId.length())) : null;
    }

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    private String generateId() {
        return UUID.randomUUID().toString().replace("-", "");
    }
}
