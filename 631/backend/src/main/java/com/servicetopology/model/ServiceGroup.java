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
@Node("ServiceGroup")
public class ServiceGroup {

    @Id
    private String id;

    @Property("name")
    private String name;

    @Property("namespace")
    private String namespace;

    @Property("groupType")
    private String groupType;

    @Property("description")
    private String description;

    @Property("collapsed")
    @Builder.Default
    private boolean collapsed = false;

    @Property("createdAt")
    private LocalDateTime createdAt;

    @Property("lastUpdated")
    private LocalDateTime lastUpdated;

    @Relationship(type = "CONTAINS", direction = Relationship.Direction.OUTGOING)
    @Builder.Default
    private List<ServiceNode> services = new ArrayList<>();

    @Relationship(type = "CONTAINS_GROUP", direction = Relationship.Direction.OUTGOING)
    @Builder.Default
    private List<ServiceGroup> subgroups = new ArrayList<>();

    @Relationship(type = "PARENT_GROUP", direction = Relationship.Direction.INCOMING)
    private ServiceGroup parent;
}
