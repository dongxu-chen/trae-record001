package com.servicetopology.model;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Node("Service")
public class ServiceNode {

    @Id
    private String id;

    @Property("name")
    private String name;

    @Property("namespace")
    private String namespace;

    @Property("type")
    private String type;

    @Property("language")
    private String language;

    @Property("version")
    private String version;

    @Property("serviceType")
    private String serviceType;

    @Property("clusterIp")
    private String clusterIp;

    @Property("ports")
    private String ports;

    @Property("labels")
    private String labels;

    @Property("annotations")
    private String annotations;

    @Property("status")
    private String status;

    @Property("discoveredAt")
    private LocalDateTime discoveredAt;

    @Property("lastUpdated")
    private LocalDateTime lastUpdated;

    @Relationship(type = "CALLS", direction = Relationship.Direction.OUTGOING)
    @Builder.Default
    private List<ServiceCall> outgoingCalls = new ArrayList<>();

    @Relationship(type = "CALLS", direction = Relationship.Direction.INCOMING)
    @Builder.Default
    private List<ServiceCall> incomingCalls = new ArrayList<>();

    @Relationship(type = "MEMBER_OF", direction = Relationship.Direction.OUTGOING)
    private ServiceGroup group;

    @Relationship(type = "BELONGS_TO_CONSUMER_GROUP", direction = Relationship.Direction.OUTGOING)
    @Builder.Default
    private List<ConsumerGroup> consumerGroups = new ArrayList<>();

    @Property("traceHeaders")
    @Builder.Default
    private String traceHeaders = "{}";

    @Property("customData")
    @Builder.Default
    private String customData = "{}";

    public void addOutgoingCall(ServiceNode target, ServiceCall call) {
        outgoingCalls.add(call);
    }

    public void addConsumerGroup(ConsumerGroup group) {
        consumerGroups.add(group);
    }
}
