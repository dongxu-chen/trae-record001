package com.servicetopology.model;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.RelationshipProperties;
import org.springframework.data.neo4j.core.schema.TargetNode;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@RelationshipProperties
public class ServiceCall {

    @Id
    private String id;

    @TargetNode
    private ServiceNode target;

    private String callType;

    private String protocol;

    private boolean isAsync;

    private String messageQueue;

    private String httpMethod;

    private String path;

    private long callCount;

    private long errorCount;

    private double avgLatencyMs;

    private String firstSeen;

    private String lastSeen;

    private String sourceLanguage;

    private String targetLanguage;

    private String traceId;

    private String parentSpanId;

    private String spanId;

    private String consumerGroup;

    private String messageTopic;

    private String correlationId;

    private String baggage;

    private long successCount;

    private double qps;

    private double peakQps;

    private long windowSeconds;
}
