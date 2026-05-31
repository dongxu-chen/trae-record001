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
@Node("Trace")
public class TraceContext {

    @Id
    private String traceId;

    @Property("status")
    private String status;

    @Property("startTime")
    private LocalDateTime startTime;

    @Property("endTime")
    private LocalDateTime endTime;

    @Property("durationMs")
    private double durationMs;

    @Property("spanCount")
    @Builder.Default
    private int spanCount = 0;

    @Property("errorCount")
    @Builder.Default
    private int errorCount = 0;

    @Relationship(type = "PART_OF_TRACE", direction = Relationship.Direction.INCOMING)
    @Builder.Default
    private List<ServiceNode> involvedServices = new ArrayList<>();
}
