package com.servicetopology.tracing;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.servicetopology.config.DiscoveryProperties;
import com.servicetopology.model.ConsumerGroup;
import com.servicetopology.model.ServiceNode;
import com.servicetopology.model.TraceContext;
import com.servicetopology.neo4j.ConsumerGroupRepository;
import com.servicetopology.neo4j.ServiceNodeRepository;
import com.servicetopology.neo4j.TraceContextRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TracingAnalyzer {

    private final ServiceNodeRepository serviceNodeRepository;
    private final ConsumerGroupRepository consumerGroupRepository;
    private final TraceContextRepository traceContextRepository;
    private final DiscoveryProperties discoveryProperties;
    private final ObjectMapper objectMapper;

    private static final List<String> TRACE_HEADERS = Arrays.asList(
        "traceparent", "tracestate", "X-Request-ID", "X-Correlation-ID",
        "X-B3-TraceId", "X-B3-SpanId", "X-B3-ParentSpanId", "uber-trace-id"
    );

    public void analyzeTrace(TraceData traceData) {
        log.debug("Analyzing trace: {}", traceData.getTraceId());

        List<SpanData> spans = traceData.getSpans();
        if (spans == null || spans.isEmpty()) {
            return;
        }

        spans.sort((a, b) -> {
            long aStart = a.getStartTime() != null ? a.getStartTime() : 0;
            long bStart = b.getStartTime() != null ? b.getStartTime() : 0;
            return Long.compare(aStart, bStart);
        });

        createOrUpdateTraceContext(traceData, spans);

        Map<String, List<SpanData>> producerSpans = new HashMap<>();
        Map<String, List<SpanData>> consumerSpans = new HashMap<>();

        for (SpanData span : spans) {
            extractTraceHeaders(span);
            
            String messageQueue = detectMessageQueue(span);
            if (messageQueue != null) {
                String spanKind = span.getSpanKind() != null ? span.getSpanKind().toUpperCase() : "";
                if (spanKind.contains("PRODUCER")) {
                    String key = messageQueue + "-" + (span.getMessageTopic() != null ? span.getMessageTopic() : "default");
                    producerSpans.computeIfAbsent(key, k -> new ArrayList<>()).add(span);
                } else if (spanKind.contains("CONSUMER")) {
                    String key = messageQueue + "-" + (span.getConsumerGroup() != null ? span.getConsumerGroup() : "default") 
                               + "-" + (span.getMessageTopic() != null ? span.getMessageTopic() : "default");
                    consumerSpans.computeIfAbsent(key, k -> new ArrayList<>()).add(span);
                }
            }

            analyzeSpan(span, spans, traceData.getTraceId());
        }

        correlateProducerConsumer(producerSpans, consumerSpans, traceData.getTraceId());
    }

    private void createOrUpdateTraceContext(TraceData traceData, List<SpanData> spans) {
        String traceId = traceData.getTraceId();
        if (traceId == null || traceId.isEmpty()) {
            return;
        }

        try {
            LocalDateTime startTime = spans.stream()
                .filter(s -> s.getStartTime() != null)
                .min(Comparator.comparingLong(SpanData::getStartTime))
                .map(s -> LocalDateTime.now())
                .orElse(LocalDateTime.now());

            LocalDateTime endTime = spans.stream()
                .filter(s -> s.getEndTime() != null)
                .max(Comparator.comparingLong(SpanData::getEndTime))
                .map(s -> LocalDateTime.now())
                .orElse(LocalDateTime.now());

            long errorCount = spans.stream().filter(SpanData::isError).count();
            double durationMs = spans.stream()
                .filter(s -> s.getStartTime() != null && s.getEndTime() != null)
                .mapToDouble(s -> (s.getEndTime() - s.getStartTime()) / 1_000_000.0)
                .sum();

            TraceContext traceContext = traceContextRepository.findById(traceId).orElseGet(() ->
                TraceContext.builder()
                    .traceId(traceId)
                    .status(errorCount > 0 ? "ERROR" : "SUCCESS")
                    .startTime(startTime)
                    .endTime(endTime)
                    .durationMs(durationMs)
                    .spanCount(spans.size())
                    .errorCount((int) errorCount)
                    .createdAt(startTime)
                    .build()
            );

            traceContext.setSpanCount(spans.size());
            traceContext.setErrorCount((int) errorCount);
            traceContext.setEndTime(endTime);
            traceContext.setDurationMs(durationMs);
            traceContext.setStatus(errorCount > 0 ? "ERROR" : "SUCCESS");

            traceContextRepository.save(traceContext);

            Set<String> serviceIds = spans.stream()
                .map(s -> extractServiceId(s.getServiceName()))
                .collect(Collectors.toSet());
            for (String serviceId : serviceIds) {
                traceContextRepository.linkServiceToTrace(traceId, serviceId);
            }

        } catch (Exception e) {
            log.warn("Failed to create/update trace context: {}", e.getMessage());
        }
    }

    private void extractTraceHeaders(SpanData span) {
        Map<String, String> tags = span.getTags();
        if (tags == null) {
            return;
        }

        Map<String, String> traceHeaders = new HashMap<>();
        for (String header : TRACE_HEADERS) {
            String value = tags.get(header);
            if (value != null) {
                traceHeaders.put(header, value);
            }
            String lowerValue = tags.get(header.toLowerCase());
            if (lowerValue != null) {
                traceHeaders.put(header.toLowerCase(), lowerValue);
            }
        }

        if (!traceHeaders.isEmpty()) {
            String serviceId = extractServiceId(span.getServiceName());
            serviceNodeRepository.findById(serviceId).ifPresent(service -> {
                try {
                    service.setTraceHeaders(objectMapper.writeValueAsString(traceHeaders));
                    service.setLastUpdated(LocalDateTime.now());
                    serviceNodeRepository.save(service);
                } catch (JsonProcessingException e) {
                    log.warn("Failed to serialize trace headers: {}", e.getMessage());
                }
            });
        }

        String correlationId = tags.get("X-Correlation-ID");
        if (correlationId != null && span.getTraceId() != null) {
            span.setCorrelationId(correlationId);
        }
    }

    private void correlateProducerConsumer(
            Map<String, List<SpanData>> producerSpans,
            Map<String, List<SpanData>> consumerSpans,
            String traceId) {

        for (Map.Entry<String, List<SpanData>> entry : consumerSpans.entrySet()) {
            String key = entry.getKey();
            List<SpanData> consumers = entry.getValue();

            if (consumers.isEmpty()) continue;

            String[] parts = key.split("-", 3);
            if (parts.length < 3) continue;

            String messageQueue = parts[0];
            String consumerGroupName = parts[1];
            String topic = parts.length > 2 ? parts[2] : "default";

            String producerKey = messageQueue + "-" + topic;
            List<SpanData> producers = producerSpans.getOrDefault(producerKey, new ArrayList<>());

            ConsumerGroup consumerGroup = createOrGetConsumerGroup(
                consumerGroupName, messageQueue, topic, consumers.get(0).getServiceNamespace());

            for (SpanData consumer : consumers) {
                String consumerId = extractServiceId(consumer.getServiceName());
                ensureServiceExists(consumerId, consumer.getServiceName(), consumer.getServiceNamespace());
                consumerGroupRepository.linkProducerConsumerGroup(
                    "placeholder-producer",
                    consumerGroup.getId(),
                    consumerId
                );
            }

            for (SpanData producer : producers) {
                String producerId = extractServiceId(producer.getServiceName());
                ensureServiceExists(producerId, producer.getServiceName(), producer.getServiceNamespace());
                consumerGroupRepository.linkProducerConsumerGroup(
                    producerId,
                    consumerGroup.getId(),
                    "placeholder-consumer"
                );
            }

            Set<String> uniqueConsumerIds = consumers.stream()
                .map(s -> extractServiceId(s.getServiceName()))
                .collect(Collectors.toSet());
            consumerGroupRepository.updateConsumerCount(
                consumerGroup.getId(),
                uniqueConsumerIds.size(),
                LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
            );
        }
    }

    private ConsumerGroup createOrGetConsumerGroup(String name, String messageQueue, String topic, String namespace) {
        if (namespace == null) {
            namespace = "default";
        }

        String groupId = namespace + "-" + name + "-" + messageQueue + "-" + topic;

        return consumerGroupRepository.findById(groupId).orElseGet(() -> {
            ConsumerGroup group = ConsumerGroup.builder()
                .id(groupId)
                .name(name)
                .namespace(namespace)
                .messageQueue(messageQueue)
                .topic(topic)
                .status("ACTIVE")
                .discoveredAt(LocalDateTime.now())
                .lastUpdated(LocalDateTime.now())
                .build();
            return consumerGroupRepository.save(group);
        });
    }

    private void analyzeSpan(SpanData span, List<SpanData> allSpans, String traceId) {
        String sourceService = span.getServiceName();
        String targetService = extractTargetService(span);

        if (sourceService == null || targetService == null || sourceService.equals(targetService)) {
            return;
        }

        boolean isAsync = isAsyncCall(span);
        String messageQueue = detectMessageQueue(span);
        String protocol = detectProtocol(span);
        String callType = determineCallType(span, isAsync, messageQueue);

        String sourceId = extractServiceId(sourceService);
        String targetId = extractServiceId(targetService);

        ensureServiceExists(sourceId, sourceService, span.getServiceNamespace());
        ensureServiceExists(targetId, targetService, null);

        String callId = generateCallId(sourceId, targetId, span);
        String now = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
        long successCount = span.isError() ? 0 : 1;
        long errorCount = span.isError() ? 1 : 0;
        double qps = calculateQps(span);
        long windowSeconds = 60;

        serviceNodeRepository.mergeServiceCallWithTrace(
            sourceId,
            targetId,
            callId,
            callType,
            protocol,
            isAsync,
            messageQueue,
            span.getHttpMethod(),
            span.getPath(),
            1,
            errorCount,
            successCount,
            calculateLatency(span),
            now,
            now,
            traceId,
            span.getSpanId(),
            span.getParentSpanId(),
            span.getCorrelationId(),
            span.getConsumerGroup(),
            span.getMessageTopic(),
            qps,
            windowSeconds
        );

        log.debug("Recorded service call: {} -> {} (type: {}, async: {}, queue: {}, trace: {})",
            sourceService, targetService, callType, isAsync, messageQueue, traceId);
    }

    private String extractTargetService(SpanData span) {
        if (span.getTargetService() != null) {
            return span.getTargetService();
        }

        if (span.getHttpUrl() != null) {
            return extractServiceFromUrl(span.getHttpUrl());
        }

        if (span.getPeerService() != null) {
            return span.getPeerService();
        }

        if (span.getDbInstance() != null) {
            return span.getDbInstance();
        }

        if (span.getMessageQueue() != null) {
            return span.getMessageQueue();
        }

        return null;
    }

    private String extractServiceFromUrl(String url) {
        try {
            if (url.startsWith("http://") || url.startsWith("https://")) {
                String withoutProtocol = url.substring(url.indexOf("://") + 3);
                String host = withoutProtocol.split("/")[0].split(":")[0];

                if (host.endsWith(".svc.cluster.local")) {
                    String[] parts = host.split("\\.");
                    return parts[0];
                }

                if (host.matches("[a-zA-Z0-9-]+\\.[a-zA-Z0-9-]+")) {
                    return host.split("\\.")[0];
                }

                return host;
            }
        } catch (Exception e) {
            log.debug("Failed to extract service from URL: {}", url);
        }
        return null;
    }

    private boolean isAsyncCall(SpanData span) {
        if (!discoveryProperties.getAsyncCallDetection().isEnabled()) {
            return false;
        }

        List<String> asyncHeaders = discoveryProperties.getAsyncCallDetection().getAsyncHeaders();
        Map<String, String> tags = span.getTags();

        if (tags != null) {
            for (String header : asyncHeaders) {
                if (tags.containsKey(header) || tags.containsKey(header.toLowerCase())) {
                    return true;
                }
            }
        }

        if (span.getSpanKind() != null) {
            String kind = span.getSpanKind().toUpperCase();
            return kind.contains("PRODUCER") || kind.contains("CONSUMER");
        }

        return false;
    }

    private String detectMessageQueue(SpanData span) {
        if (!discoveryProperties.getTracing().getMessageQueueDetection().isEnabled()) {
            return null;
        }

        List<String> queuePrefixes = discoveryProperties.getTracing().getMessageQueueDetection().getQueuePrefixes();

        if (span.getMessageQueue() != null) {
            return span.getMessageQueue();
        }

        if (span.getSpanKind() != null) {
            String kind = span.getSpanKind().toUpperCase();
            if (kind.contains("PRODUCER") || kind.contains("CONSUMER")) {
                Map<String, String> tags = span.getTags();
                if (tags != null) {
                    for (Map.Entry<String, String> entry : tags.entrySet()) {
                        String key = entry.getKey().toLowerCase();
                        String value = entry.getValue().toLowerCase();

                        for (String prefix : queuePrefixes) {
                            if (key.contains(prefix) || value.contains(prefix)) {
                                return prefix;
                            }
                        }
                    }
                }
            }
        }

        return null;
    }

    private String detectProtocol(SpanData span) {
        if (span.getHttpMethod() != null) {
            return "HTTP";
        }

        if (span.getDbType() != null) {
            return span.getDbType().toUpperCase();
        }

        if (span.getMessageQueue() != null) {
            return "MQ";
        }

        if (span.getGrpcService() != null) {
            return "gRPC";
        }

        return "UNKNOWN";
    }

    private String determineCallType(SpanData span, boolean isAsync, String messageQueue) {
        if (messageQueue != null) {
            return "MESSAGE_QUEUE";
        }

        if (span.getDbType() != null) {
            return "DATABASE";
        }

        if (span.getGrpcService() != null) {
            return "GRPC";
        }

        if (isAsync) {
            return "ASYNC_HTTP";
        }

        return "SYNC_HTTP";
    }

    private String extractServiceId(String serviceName) {
        if (serviceName == null) {
            return "unknown";
        }
        String namespace = "default";

        if (serviceName.contains("-")) {
            String[] parts = serviceName.split("-", 2);
            if (parts.length > 1) {
                return serviceName;
            }
        }

        return namespace + "-" + serviceName;
    }

    private void ensureServiceExists(String serviceId, String serviceName, String namespace) {
        if (namespace == null) {
            namespace = "default";
        }

        serviceNodeRepository.findById(serviceId).orElseGet(() -> {
            ServiceNode node = ServiceNode.builder()
                .id(serviceId)
                .name(serviceName)
                .namespace(namespace)
                .type("DISCOVERED_VIA_TRACING")
                .status("ACTIVE")
                .discoveredAt(LocalDateTime.now())
                .lastUpdated(LocalDateTime.now())
                .build();
            return serviceNodeRepository.save(node);
        });
    }

    private String generateCallId(String sourceId, String targetId, SpanData span) {
        String base = sourceId + "-" + targetId;
        String suffix = span.getHttpMethod() != null ? "-" + span.getHttpMethod() : "";
        String pathHash = span.getPath() != null ? "-" + Math.abs(span.getPath().hashCode()) : "";
        return UUID.nameUUIDFromBytes((base + suffix + pathHash).getBytes()).toString();
    }

    private double calculateLatency(SpanData span) {
        if (span.getEndTime() != null && span.getStartTime() != null) {
            return (span.getEndTime() - span.getStartTime()) / 1_000_000.0;
        }
        return 0;
    }

    private double calculateQps(SpanData span) {
        if (span.getEndTime() != null && span.getStartTime() != null) {
            long durationNs = span.getEndTime() - span.getStartTime();
            if (durationNs > 0) {
                double durationSec = durationNs / 1_000_000_000.0;
                return Math.round(1.0 / durationSec * 100.0) / 100.0;
            }
        }
        return 1.0;
    }

    public void recordDirectCall(CallRequest request) {
        String sourceId = extractServiceId(request.getSourceService());
        String targetId = extractServiceId(request.getTargetService());

        ensureServiceExists(sourceId, request.getSourceService(), request.getSourceNamespace());
        ensureServiceExists(targetId, request.getTargetService(), request.getTargetNamespace());

        String callId = UUID.nameUUIDFromBytes((sourceId + targetId + request.getPath() + request.getMethod()).getBytes()).toString();
        String now = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
        long successCount = request.getErrorCount() > 0 ? request.getCallCount() - request.getErrorCount() : request.getCallCount();

        double qps = request.getCallCount() > 0 ? (double) request.getCallCount() / 60.0 : 1.0;
        long windowSeconds = 60;

        serviceNodeRepository.mergeServiceCallWithTrace(
            sourceId,
            targetId,
            callId,
            request.isAsync() ? "ASYNC_HTTP" : "SYNC_HTTP",
            request.getProtocol() != null ? request.getProtocol() : "HTTP",
            request.isAsync(),
            request.getMessageQueue(),
            request.getMethod(),
            request.getPath(),
            request.getCallCount() > 0 ? request.getCallCount() : 1,
            request.getErrorCount(),
            successCount,
            request.getAvgLatencyMs(),
            now,
            now,
            null,
            null,
            null,
            null,
            null,
            null,
            qps,
            windowSeconds
        );

        log.info("Recorded direct call: {} -> {}", request.getSourceService(), request.getTargetService());
    }

    public static class TraceData {
        private String traceId;
        private List<SpanData> spans;

        public String getTraceId() { return traceId; }
        public void setTraceId(String traceId) { this.traceId = traceId; }
        public List<SpanData> getSpans() { return spans; }
        public void setSpans(List<SpanData> spans) { this.spans = spans; }
    }

    public static class SpanData {
        private String spanId;
        private String parentSpanId;
        private String traceId;
        private String serviceName;
        private String serviceNamespace;
        private String targetService;
        private String spanKind;
        private String operationName;
        private Long startTime;
        private Long endTime;
        private boolean error;
        private String httpMethod;
        private String httpUrl;
        private Integer httpStatusCode;
        private String path;
        private String peerService;
        private String dbType;
        private String dbInstance;
        private String dbStatement;
        private String messageQueue;
        private String messageTopic;
        private String consumerGroup;
        private String grpcService;
        private String grpcMethod;
        private String correlationId;
        private Map<String, String> tags;

        public String getSpanId() { return spanId; }
        public void setSpanId(String spanId) { this.spanId = spanId; }
        public String getParentSpanId() { return parentSpanId; }
        public void setParentSpanId(String parentSpanId) { this.parentSpanId = parentSpanId; }
        public String getTraceId() { return traceId; }
        public void setTraceId(String traceId) { this.traceId = traceId; }
        public String getServiceName() { return serviceName; }
        public void setServiceName(String serviceName) { this.serviceName = serviceName; }
        public String getServiceNamespace() { return serviceNamespace; }
        public void setServiceNamespace(String serviceNamespace) { this.serviceNamespace = serviceNamespace; }
        public String getTargetService() { return targetService; }
        public void setTargetService(String targetService) { this.targetService = targetService; }
        public String getSpanKind() { return spanKind; }
        public void setSpanKind(String spanKind) { this.spanKind = spanKind; }
        public String getOperationName() { return operationName; }
        public void setOperationName(String operationName) { this.operationName = operationName; }
        public Long getStartTime() { return startTime; }
        public void setStartTime(Long startTime) { this.startTime = startTime; }
        public Long getEndTime() { return endTime; }
        public void setEndTime(Long endTime) { this.endTime = endTime; }
        public boolean isError() { return error; }
        public void setError(boolean error) { this.error = error; }
        public String getHttpMethod() { return httpMethod; }
        public void setHttpMethod(String httpMethod) { this.httpMethod = httpMethod; }
        public String getHttpUrl() { return httpUrl; }
        public void setHttpUrl(String httpUrl) { this.httpUrl = httpUrl; }
        public Integer getHttpStatusCode() { return httpStatusCode; }
        public void setHttpStatusCode(Integer httpStatusCode) { this.httpStatusCode = httpStatusCode; }
        public String getPath() { return path; }
        public void setPath(String path) { this.path = path; }
        public String getPeerService() { return peerService; }
        public void setPeerService(String peerService) { this.peerService = peerService; }
        public String getDbType() { return dbType; }
        public void setDbType(String dbType) { this.dbType = dbType; }
        public String getDbInstance() { return dbInstance; }
        public void setDbInstance(String dbInstance) { this.dbInstance = dbInstance; }
        public String getDbStatement() { return dbStatement; }
        public void setDbStatement(String dbStatement) { this.dbStatement = dbStatement; }
        public String getMessageQueue() { return messageQueue; }
        public void setMessageQueue(String messageQueue) { this.messageQueue = messageQueue; }
        public String getMessageTopic() { return messageTopic; }
        public void setMessageTopic(String messageTopic) { this.messageTopic = messageTopic; }
        public String getConsumerGroup() { return consumerGroup; }
        public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
        public String getGrpcService() { return grpcService; }
        public void setGrpcService(String grpcService) { this.grpcService = grpcService; }
        public String getGrpcMethod() { return grpcMethod; }
        public void setGrpcMethod(String grpcMethod) { this.grpcMethod = grpcMethod; }
        public String getCorrelationId() { return correlationId; }
        public void setCorrelationId(String correlationId) { this.correlationId = correlationId; }
        public Map<String, String> getTags() { return tags; }
        public void setTags(Map<String, String> tags) { this.tags = tags; }
    }

    public static class CallRequest {
        private String sourceService;
        private String sourceNamespace;
        private String targetService;
        private String targetNamespace;
        private String method;
        private String path;
        private String protocol;
        private boolean async;
        private String messageQueue;
        private String topic;
        private String consumerGroup;
        private String traceId;
        private String correlationId;
        private long callCount;
        private long errorCount;
        private double avgLatencyMs;

        public String getSourceService() { return sourceService; }
        public void setSourceService(String sourceService) { this.sourceService = sourceService; }
        public String getSourceNamespace() { return sourceNamespace; }
        public void setSourceNamespace(String sourceNamespace) { this.sourceNamespace = sourceNamespace; }
        public String getTargetService() { return targetService; }
        public void setTargetService(String targetService) { this.targetService = targetService; }
        public String getTargetNamespace() { return targetNamespace; }
        public void setTargetNamespace(String targetNamespace) { this.targetNamespace = targetNamespace; }
        public String getMethod() { return method; }
        public void setMethod(String method) { this.method = method; }
        public String getPath() { return path; }
        public void setPath(String path) { this.path = path; }
        public String getProtocol() { return protocol; }
        public void setProtocol(String protocol) { this.protocol = protocol; }
        public boolean isAsync() { return async; }
        public void setAsync(boolean async) { this.async = async; }
        public String getMessageQueue() { return messageQueue; }
        public void setMessageQueue(String messageQueue) { this.messageQueue = messageQueue; }
        public String getTopic() { return topic; }
        public void setTopic(String topic) { this.topic = topic; }
        public String getConsumerGroup() { return consumerGroup; }
        public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
        public String getTraceId() { return traceId; }
        public void setTraceId(String traceId) { this.traceId = traceId; }
        public String getCorrelationId() { return correlationId; }
        public void setCorrelationId(String correlationId) { this.correlationId = correlationId; }
        public long getCallCount() { return callCount; }
        public void setCallCount(long callCount) { this.callCount = callCount; }
        public long getErrorCount() { return errorCount; }
        public void setErrorCount(long errorCount) { this.errorCount = errorCount; }
        public double getAvgLatencyMs() { return avgLatencyMs; }
        public void setAvgLatencyMs(double avgLatencyMs) { this.avgLatencyMs = avgLatencyMs; }
    }
}
