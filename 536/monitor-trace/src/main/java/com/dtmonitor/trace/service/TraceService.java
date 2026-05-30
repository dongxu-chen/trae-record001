package com.dtmonitor.trace.service;

import com.dtmonitor.trace.model.TraceDag;
import com.dtmonitor.trace.model.TraceSpan;
import brave.Span;
import brave.Tracing;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class TraceService {

    private final ZipkinQueryClient zipkinQueryClient;
    private final Tracing tracing;

    public TraceService(ZipkinQueryClient zipkinQueryClient, Tracing tracing) {
        this.zipkinQueryClient = zipkinQueryClient;
        this.tracing = tracing;
    }

    public List<TraceSpan> getTraceSpans(String traceId) {
        Span span = tracing.tracer().newTrace().name("fetch-trace-spans").start();
        span.tag("query.traceId", traceId);
        MDC.put("queryTraceId", traceId);

        try {
            List<TraceSpan> spans = zipkinQueryClient.fetchSpans(traceId);
            if (spans == null || spans.isEmpty()) {
                log.warn("No spans found for traceId: {}", traceId);
                return Collections.emptyList();
            }
            List<TraceSpan> sorted = spans.stream()
                    .sorted(Comparator.comparingLong(TraceSpan::getStartMicros))
                    .collect(Collectors.toList());
            span.tag("span.count", String.valueOf(sorted.size()));
            return sorted;
        } catch (Exception e) {
            span.error(e);
            throw e;
        } finally {
            span.finish();
            MDC.remove("queryTraceId");
        }
    }

    public TraceDag buildDag(String traceId) {
        Span span = tracing.tracer().newTrace().name("build-trace-dag").start();
        span.tag("query.traceId", traceId);
        MDC.put("queryTraceId", traceId);

        try {
            List<TraceSpan> spans = getTraceSpans(traceId);
            if (spans.isEmpty()) {
                return TraceDag.builder().traceId(traceId).build();
            }

            TraceDag dag = TraceDag.builder().traceId(traceId).build();

            Map<String, Integer> spanDepthMap = computeDepth(spans);

            Map<String, TraceDag.DagNode> nodeMap = new LinkedHashMap<>();
            for (TraceSpan traceSpan : spans) {
                String nodeId = traceSpan.getServiceName() + ":" + traceSpan.getName();
                if (!nodeMap.containsKey(nodeId)) {
                    String status = extractStatus(traceSpan);
                    int depth = spanDepthMap.getOrDefault(traceSpan.getSpanId(), 0);
                    TraceDag.DagNode node = TraceDag.DagNode.builder()
                            .id(nodeId)
                            .name(traceSpan.getName())
                            .serviceName(traceSpan.getServiceName())
                            .durationMs(traceSpan.getDurationMicros() / 1000)
                            .status(status)
                            .transactionMode(extractTransactionMode(traceSpan))
                            .branchId(extractBranchId(traceSpan))
                            .depth(depth)
                            .build();
                    nodeMap.put(nodeId, node);
                    dag.addNode(node);
                }
            }

            for (TraceSpan traceSpan : spans) {
                if (traceSpan.getParentSpanId() != null && !traceSpan.getParentSpanId().isEmpty()) {
                    Optional<TraceSpan> parentSpan = spans.stream()
                            .filter(s -> s.getSpanId().equals(traceSpan.getParentSpanId()))
                            .findFirst();

                    if (parentSpan.isPresent()) {
                        TraceSpan parent = parentSpan.get();
                        String sourceId = parent.getServiceName() + ":" + parent.getName();
                        String targetId = traceSpan.getServiceName() + ":" + traceSpan.getName();
                        TraceDag.DagEdge edge = TraceDag.DagEdge.builder()
                                .source(sourceId)
                                .target(targetId)
                                .label(traceSpan.getName())
                                .build();
                        dag.addEdge(edge);
                    }
                }
            }

            span.tag("dag.nodes", String.valueOf(dag.getNodes() != null ? dag.getNodes().size() : 0));
            span.tag("dag.edges", String.valueOf(dag.getEdges() != null ? dag.getEdges().size() : 0));
            return dag;
        } catch (Exception e) {
            span.error(e);
            throw e;
        } finally {
            span.finish();
            MDC.remove("queryTraceId");
        }
    }

    private Map<String, Integer> computeDepth(List<TraceSpan> spans) {
        Map<String, Integer> depthMap = new HashMap<>();
        Map<String, String> parentMap = new HashMap<>();
        for (TraceSpan s : spans) {
            parentMap.put(s.getSpanId(), s.getParentSpanId());
        }
        for (TraceSpan s : spans) {
            computeDepthForSpan(s.getSpanId(), parentMap, depthMap);
        }
        return depthMap;
    }

    private int computeDepthForSpan(String spanId, Map<String, String> parentMap, Map<String, Integer> depthMap) {
        if (depthMap.containsKey(spanId)) {
            return depthMap.get(spanId);
        }
        String parentId = parentMap.get(spanId);
        if (parentId == null || parentId.isEmpty() || !parentMap.containsKey(parentId)) {
            depthMap.put(spanId, 0);
            return 0;
        }
        int parentDepth = computeDepthForSpan(parentId, parentMap, depthMap);
        int depth = parentDepth + 1;
        depthMap.put(spanId, depth);
        return depth;
    }

    private String extractStatus(TraceSpan span) {
        if (span.getTags() == null) return "UNKNOWN";
        return span.getTags().stream()
                .filter(t -> "transaction.status".equals(t.getKey()))
                .map(TraceSpan.KeyValue::getValue)
                .findFirst()
                .orElse("UNKNOWN");
    }

    private String extractTransactionMode(TraceSpan span) {
        if (span.getTags() == null) return null;
        return span.getTags().stream()
                .filter(t -> "transaction.mode".equals(t.getKey()))
                .map(TraceSpan.KeyValue::getValue)
                .findFirst()
                .orElse(null);
    }

    private String extractBranchId(TraceSpan span) {
        if (span.getTags() == null) return null;
        return span.getTags().stream()
                .filter(t -> "transaction.branchId".equals(t.getKey()))
                .map(TraceSpan.KeyValue::getValue)
                .findFirst()
                .orElse(null);
    }
}
