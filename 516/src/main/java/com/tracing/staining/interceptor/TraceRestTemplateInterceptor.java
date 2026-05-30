package com.tracing.staining.interceptor;

import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import com.tracing.staining.context.TraceHeaderAccessor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpRequest;
import org.springframework.http.client.ClientHttpRequestExecution;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Map;

@Slf4j
@Component
public class TraceRestTemplateInterceptor implements ClientHttpRequestInterceptor {

    @Override
    public ClientHttpResponse intercept(HttpRequest request, byte[] body,
                                        ClientHttpRequestExecution execution) throws IOException {
        StainingContext context = TraceContextHolder.getContext();

        if (context != null) {
            StainingContext childContext = TraceContextHolder.createChildContext();
            HttpHeaders headers = request.getHeaders();

            Map<String, String> traceHeaders = TraceHeaderAccessor.toStringHeaders(childContext);
            for (Map.Entry<String, String> entry : traceHeaders.entrySet()) {
                if (!headers.containsKey(entry.getKey())) {
                    headers.set(entry.getKey(), entry.getValue());
                }
            }

            log.debug("HTTP headers injected (request body untouched): traceId={}, spanId={}, staining={}, uri={}",
                    childContext.getTraceId(), childContext.getSpanId(),
                    childContext.getStainingFlag(), request.getURI());
        } else {
            log.debug("No trace context found for outbound request to {}", request.getURI());
        }

        return execution.execute(request, body);
    }
}
