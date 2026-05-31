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
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Node("ConsumerGroup")
public class ConsumerGroup {

    @Id
    private String id;

    @Property("name")
    private String name;

    @Property("namespace")
    private String namespace;

    @Property("messageQueue")
    private String messageQueue;

    @Property("topic")
    private String topic;

    @Property("consumerCount")
    @Builder.Default
    private int consumerCount = 0;

    @Property("status")
    private String status;

    @Property("discoveredAt")
    private LocalDateTime discoveredAt;

    @Property("lastUpdated")
    private LocalDateTime lastUpdated;

    @Relationship(type = "HAS_CONSUMER", direction = Relationship.Direction.OUTGOING)
    @Builder.Default
    private List<ServiceNode> consumers = new ArrayList<>();

    @Relationship(type = "PRODUCES_TO", direction = Relationship.Direction.INCOMING)
    @Builder.Default
    private List<ServiceNode> producers = new ArrayList<>();
}
