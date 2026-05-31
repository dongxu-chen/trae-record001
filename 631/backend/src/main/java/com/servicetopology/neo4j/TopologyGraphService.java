package com.servicetopology.neo4j;

import com.servicetopology.model.ServiceNode;
import com.servicetopology.model.ConsumerGroup;
import com.servicetopology.model.ServiceGroup;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Result;
import org.neo4j.driver.Session;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TopologyGraphService {

    private final Driver neo4jDriver;
    private final ServiceNodeRepository serviceNodeRepository;

    public TopologyData getFullTopology() {
        log.debug("Getting full topology graph");

        List<TopologyNode> nodes = new ArrayList<>();
        List<TopologyEdge> edges = new ArrayList<>();

        try (Session session = neo4jDriver.session()) {
            Result nodeResult = session.run(
                "MATCH (s:Service) RETURN s.id AS id, s.name AS name, s.namespace AS namespace, " +
                "s.type AS type, s.language AS language, s.version AS version, s.status AS status, " +
                "s.serviceType AS serviceType, s.clusterIp AS clusterIp"
            );

            while (nodeResult.hasNext()) {
                Record record = nodeResult.next();
                nodes.add(TopologyNode.builder()
                    .id(record.get("id").asString())
                    .name(record.get("name").asString())
                    .namespace(record.get("namespace").asString())
                    .type(record.get("type").asString(null))
                    .language(record.get("language").asString(null))
                    .version(record.get("version").asString(null))
                    .status(record.get("status").asString(null))
                    .serviceType(record.get("serviceType").asString(null))
                    .clusterIp(record.get("clusterIp").asString(null))
                    .build());
            }

            Result edgeResult = session.run(
                "MATCH (source:Service)-[c:CALLS]->(target:Service) " +
                "RETURN source.id AS source, target.id AS target, " +
                "c.callType AS callType, c.protocol AS protocol, " +
                "c.isAsync AS isAsync, c.messageQueue AS messageQueue, " +
                "c.httpMethod AS httpMethod, c.path AS path, " +
                "c.callCount AS callCount, c.errorCount AS errorCount, " +
                "c.avgLatencyMs AS avgLatencyMs, c.lastSeen AS lastSeen"
            );

            while (edgeResult.hasNext()) {
                Record record = edgeResult.next();
                edges.add(TopologyEdge.builder()
                    .source(record.get("source").asString())
                    .target(record.get("target").asString())
                    .callType(record.get("callType").asString(null))
                    .protocol(record.get("protocol").asString(null))
                    .isAsync(record.get("isAsync").asBoolean(false))
                    .messageQueue(record.get("messageQueue").asString(null))
                    .httpMethod(record.get("httpMethod").asString(null))
                    .path(record.get("path").asString(null))
                    .callCount(record.get("callCount").asLong(0))
                    .errorCount(record.get("errorCount").asLong(0))
                    .avgLatencyMs(record.get("avgLatencyMs").asDouble(0))
                    .lastSeen(record.get("lastSeen").asString(null))
                    .build());
            }
        }

        return TopologyData.builder()
            .nodes(nodes)
            .edges(edges)
            .build();
    }

    public TopologyData getTopologyByNamespace(String namespace) {
        log.debug("Getting topology for namespace: {}", namespace);

        List<TopologyNode> nodes = new ArrayList<>();
        List<TopologyEdge> edges = new ArrayList<>();

        try (Session session = neo4jDriver.session()) {
            Result nodeResult = session.run(
                "MATCH (s:Service {namespace: $namespace}) " +
                "RETURN s.id AS id, s.name AS name, s.namespace AS namespace, " +
                "s.type AS type, s.language AS language, s.version AS version, s.status AS status, " +
                "s.serviceType AS serviceType, s.clusterIp AS clusterIp",
                Map.of("namespace", namespace)
            );

            Set<String> nodeIds = new HashSet<>();
            while (nodeResult.hasNext()) {
                Record record = nodeResult.next();
                String id = record.get("id").asString();
                nodeIds.add(id);
                nodes.add(TopologyNode.builder()
                    .id(id)
                    .name(record.get("name").asString())
                    .namespace(record.get("namespace").asString())
                    .type(record.get("type").asString(null))
                    .language(record.get("language").asString(null))
                    .version(record.get("version").asString(null))
                    .status(record.get("status").asString(null))
                    .serviceType(record.get("serviceType").asString(null))
                    .clusterIp(record.get("clusterIp").asString(null))
                    .build());
            }

            Result edgeResult = session.run(
                "MATCH (source:Service)-[c:CALLS]->(target:Service) " +
                "WHERE source.namespace = $namespace AND target.namespace = $namespace " +
                "RETURN source.id AS source, target.id AS target, " +
                "c.callType AS callType, c.protocol AS protocol, " +
                "c.isAsync AS isAsync, c.messageQueue AS messageQueue, " +
                "c.httpMethod AS httpMethod, c.path AS path, " +
                "c.callCount AS callCount, c.errorCount AS errorCount, " +
                "c.avgLatencyMs AS avgLatencyMs, c.lastSeen AS lastSeen",
                Map.of("namespace", namespace)
            );

            while (edgeResult.hasNext()) {
                Record record = edgeResult.next();
                String sourceId = record.get("source").asString();
                String targetId = record.get("target").asString();
                if (nodeIds.contains(sourceId) && nodeIds.contains(targetId)) {
                    edges.add(TopologyEdge.builder()
                        .source(sourceId)
                        .target(targetId)
                        .callType(record.get("callType").asString(null))
                        .protocol(record.get("protocol").asString(null))
                        .isAsync(record.get("isAsync").asBoolean(false))
                        .messageQueue(record.get("messageQueue").asString(null))
                        .httpMethod(record.get("httpMethod").asString(null))
                        .path(record.get("path").asString(null))
                        .callCount(record.get("callCount").asLong(0))
                        .errorCount(record.get("errorCount").asLong(0))
                        .avgLatencyMs(record.get("avgLatencyMs").asDouble(0))
                        .lastSeen(record.get("lastSeen").asString(null))
                        .build());
                }
            }
        }

        return TopologyData.builder()
            .nodes(nodes)
            .edges(edges)
            .build();
    }

    public ServiceNodeDetail getServiceDetail(String serviceId) {
        log.debug("Getting service detail for: {}", serviceId);

        ServiceNodeDetail detail = new ServiceNodeDetail();

        try (Session session = neo4jDriver.session()) {
            Result nodeResult = session.run(
                "MATCH (s:Service {id: $id}) " +
                "RETURN s.id AS id, s.name AS name, s.namespace AS namespace, " +
                "s.type AS type, s.language AS language, s.version AS version, s.status AS status, " +
                "s.serviceType AS serviceType, s.clusterIp AS clusterIp, s.ports AS ports, " +
                "s.labels AS labels, s.annotations AS annotations, " +
                "s.discoveredAt AS discoveredAt, s.lastUpdated AS lastUpdated",
                Map.of("id", serviceId)
            );

            if (nodeResult.hasNext()) {
                Record record = nodeResult.next();
                detail.setId(record.get("id").asString());
                detail.setName(record.get("name").asString());
                detail.setNamespace(record.get("namespace").asString());
                detail.setType(record.get("type").asString(null));
                detail.setLanguage(record.get("language").asString(null));
                detail.setVersion(record.get("version").asString(null));
                detail.setStatus(record.get("status").asString(null));
                detail.setServiceType(record.get("serviceType").asString(null));
                detail.setClusterIp(record.get("clusterIp").asString(null));
                detail.setPorts(record.get("ports").asString(null));
                detail.setLabels(record.get("labels").asString(null));
                detail.setAnnotations(record.get("annotations").asString(null));
                detail.setDiscoveredAt(record.get("discoveredAt").asString(null));
                detail.setLastUpdated(record.get("lastUpdated").asString(null));
            }

            List<ServiceCallDetail> incomingCalls = new ArrayList<>();
            Result incomingResult = session.run(
                "MATCH (source:Service)-[c:CALLS]->(target:Service {id: $id}) " +
                "RETURN source.id AS sourceId, source.name AS sourceName, " +
                "c.callType AS callType, c.protocol AS protocol, " +
                "c.isAsync AS isAsync, c.messageQueue AS messageQueue, " +
                "c.httpMethod AS httpMethod, c.path AS path, " +
                "c.callCount AS callCount, c.errorCount AS errorCount, " +
                "c.avgLatencyMs AS avgLatencyMs",
                Map.of("id", serviceId)
            );

            while (incomingResult.hasNext()) {
                Record record = incomingResult.next();
                incomingCalls.add(ServiceCallDetail.builder()
                    .serviceId(record.get("sourceId").asString())
                    .serviceName(record.get("sourceName").asString())
                    .callType(record.get("callType").asString(null))
                    .protocol(record.get("protocol").asString(null))
                    .isAsync(record.get("isAsync").asBoolean(false))
                    .messageQueue(record.get("messageQueue").asString(null))
                    .httpMethod(record.get("httpMethod").asString(null))
                    .path(record.get("path").asString(null))
                    .callCount(record.get("callCount").asLong(0))
                    .errorCount(record.get("errorCount").asLong(0))
                    .avgLatencyMs(record.get("avgLatencyMs").asDouble(0))
                    .build());
            }
            detail.setIncomingCalls(incomingCalls);

            List<ServiceCallDetail> outgoingCalls = new ArrayList<>();
            Result outgoingResult = session.run(
                "MATCH (source:Service {id: $id})-[c:CALLS]->(target:Service) " +
                "RETURN target.id AS targetId, target.name AS targetName, " +
                "c.callType AS callType, c.protocol AS protocol, " +
                "c.isAsync AS isAsync, c.messageQueue AS messageQueue, " +
                "c.httpMethod AS httpMethod, c.path AS path, " +
                "c.callCount AS callCount, c.errorCount AS errorCount, " +
                "c.avgLatencyMs AS avgLatencyMs",
                Map.of("id", serviceId)
            );

            while (outgoingResult.hasNext()) {
                Record record = outgoingResult.next();
                outgoingCalls.add(ServiceCallDetail.builder()
                    .serviceId(record.get("targetId").asString())
                    .serviceName(record.get("targetName").asString())
                    .callType(record.get("callType").asString(null))
                    .protocol(record.get("protocol").asString(null))
                    .isAsync(record.get("isAsync").asBoolean(false))
                    .messageQueue(record.get("messageQueue").asString(null))
                    .httpMethod(record.get("httpMethod").asString(null))
                    .path(record.get("path").asString(null))
                    .callCount(record.get("callCount").asLong(0))
                    .errorCount(record.get("errorCount").asLong(0))
                    .avgLatencyMs(record.get("avgLatencyMs").asDouble(0))
                    .build());
            }
            detail.setOutgoingCalls(outgoingCalls);
        }

        return detail;
    }

    public TopologyStats getTopologyStats() {
        log.debug("Getting topology statistics");

        try (Session session = neo4jDriver.session()) {
            Result statsResult = session.run(
                "MATCH (s:Service) " +
                "WITH count(s) AS totalServices, " +
                "collect(DISTINCT s.namespace) AS namespaces, " +
                "collect(DISTINCT s.language) AS languages, " +
                "collect(DISTINCT s.type) AS types " +
                "MATCH ()-[c:CALLS]->() " +
                "RETURN totalServices, namespaces, languages, types, " +
                "count(c) AS totalCalls, " +
                "sum(c.callCount) AS totalCallCount, " +
                "sum(c.errorCount) AS totalErrorCount, " +
                "avg(c.avgLatencyMs) AS avgLatencyMs"
            );

            if (statsResult.hasNext()) {
                Record record = statsResult.next();
                return TopologyStats.builder()
                    .totalServices(record.get("totalServices").asLong(0))
                    .namespaces(record.get("namespaces").asList(org.neo4j.driver.Value::asString, new ArrayList<>()))
                    .languages(record.get("languages").asList(org.neo4j.driver.Value::asString, new ArrayList<>()))
                    .serviceTypes(record.get("types").asList(org.neo4j.driver.Value::asString, new ArrayList<>()))
                    .totalCallRelationships(record.get("totalCalls").asLong(0))
                    .totalCallCount(record.get("totalCallCount").asLong(0))
                    .totalErrorCount(record.get("totalErrorCount").asLong(0))
                    .averageLatencyMs(record.get("avgLatencyMs").asDouble(0))
                    .build();
            }
        }

        return TopologyStats.builder().build();
    }

    public void clearAllData() {
        log.warn("Clearing all topology data");
        serviceNodeRepository.deleteAllServices();
    }

    public GroupedTopologyData getGroupedTopology() {
        log.debug("Getting grouped topology with hierarchy");

        List<TopologyNode> nodes = new ArrayList<>();
        List<TopologyEdge> edges = new ArrayList<>();
        List<TopologyGroup> groups = new ArrayList<>();
        List<ConsumerGroupNode> consumerGroups = new ArrayList<>();

        try (Session session = neo4jDriver.session()) {
            Result nodeResult = session.run(
                "MATCH (s:Service) " +
                "OPTIONAL MATCH (s)-[:MEMBER_OF]->(g:ServiceGroup) " +
                "RETURN s.id AS id, s.name AS name, s.namespace AS namespace, " +
                "s.type AS type, s.language AS language, s.version AS version, s.status AS status, " +
                "s.serviceType AS serviceType, s.clusterIp AS clusterIp, " +
                "g.id AS groupId, g.name AS groupName"
            );

            Map<String, List<TopologyNode>> groupMembers = new HashMap<>();
            while (nodeResult.hasNext()) {
                Record record = nodeResult.next();
                TopologyNode node = TopologyNode.builder()
                    .id(record.get("id").asString())
                    .name(record.get("name").asString())
                    .namespace(record.get("namespace").asString())
                    .type(record.get("type").asString(null))
                    .language(record.get("language").asString(null))
                    .version(record.get("version").asString(null))
                    .status(record.get("status").asString(null))
                    .serviceType(record.get("serviceType").asString(null))
                    .clusterIp(record.get("clusterIp").asString(null))
                    .groupId(record.get("groupId").asString(null))
                    .groupName(record.get("groupName").asString(null))
                    .build();
                nodes.add(node);

                String groupId = record.get("groupId").asString(null);
                if (groupId != null) {
                    groupMembers.computeIfAbsent(groupId, k -> new ArrayList<>()).add(node);
                }
            }

            Result edgeResult = session.run(
                "MATCH (source:Service)-[c:CALLS]->(target:Service) " +
                "RETURN source.id AS source, target.id AS target, " +
                "c.callType AS callType, c.protocol AS protocol, " +
                "c.isAsync AS isAsync, c.messageQueue AS messageQueue, " +
                "c.httpMethod AS httpMethod, c.path AS path, " +
                "c.callCount AS callCount, c.errorCount AS errorCount, " +
                "c.successCount AS successCount, c.avgLatencyMs AS avgLatencyMs, " +
                "c.lastSeen AS lastSeen, c.traceId AS traceId, " +
                "c.consumerGroup AS consumerGroup, c.messageTopic AS messageTopic"
            );

            while (edgeResult.hasNext()) {
                Record record = edgeResult.next();
                edges.add(TopologyEdge.builder()
                    .source(record.get("source").asString())
                    .target(record.get("target").asString())
                    .callType(record.get("callType").asString(null))
                    .protocol(record.get("protocol").asString(null))
                    .isAsync(record.get("isAsync").asBoolean(false))
                    .messageQueue(record.get("messageQueue").asString(null))
                    .httpMethod(record.get("httpMethod").asString(null))
                    .path(record.get("path").asString(null))
                    .callCount(record.get("callCount").asLong(0))
                    .errorCount(record.get("errorCount").asLong(0))
                    .successCount(record.get("successCount").asLong(0))
                    .avgLatencyMs(record.get("avgLatencyMs").asDouble(0))
                    .lastSeen(record.get("lastSeen").asString(null))
                    .traceId(record.get("traceId").asString(null))
                    .consumerGroup(record.get("consumerGroup").asString(null))
                    .messageTopic(record.get("messageTopic").asString(null))
                    .build());
            }

            Result groupResult = session.run(
                "MATCH (g:ServiceGroup) " +
                "OPTIONAL MATCH (parent:ServiceGroup)-[:CONTAINS_GROUP]->(g) " +
                "RETURN g.id AS id, g.name AS name, g.namespace AS namespace, " +
                "g.groupType AS groupType, g.description AS description, " +
                "g.collapsed AS collapsed, parent.id AS parentId"
            );

            while (groupResult.hasNext()) {
                Record record = groupResult.next();
                String groupId = record.get("id").asString();
                List<TopologyNode> members = groupMembers.getOrDefault(groupId, new ArrayList<>());
                groups.add(TopologyGroup.builder()
                    .id(groupId)
                    .name(record.get("name").asString())
                    .namespace(record.get("namespace").asString(null))
                    .groupType(record.get("groupType").asString(null))
                    .description(record.get("description").asString(null))
                    .collapsed(record.get("collapsed").asBoolean(false))
                    .parentId(record.get("parentId").asString(null))
                    .serviceCount(members.size())
                    .serviceIds(members.stream().map(TopologyNode::getId).collect(Collectors.toList()))
                    .build());
            }

            Result cgResult = session.run(
                "MATCH (cg:ConsumerGroup) " +
                "OPTIONAL MATCH (producer:Service)-[:PRODUCES_TO]->(cg) " +
                "OPTIONAL MATCH (cg)-[:HAS_CONSUMER]->(consumer:Service) " +
                "RETURN cg.id AS id, cg.name AS name, cg.namespace AS namespace, " +
                "cg.messageQueue AS messageQueue, cg.topic AS topic, " +
                "cg.consumerCount AS consumerCount, cg.status AS status, " +
                "collect(DISTINCT producer.id) AS producerIds, " +
                "collect(DISTINCT consumer.id) AS consumerIds"
            );

            while (cgResult.hasNext()) {
                Record record = cgResult.next();
                consumerGroups.add(ConsumerGroupNode.builder()
                    .id(record.get("id").asString())
                    .name(record.get("name").asString())
                    .namespace(record.get("namespace").asString(null))
                    .messageQueue(record.get("messageQueue").asString(null))
                    .topic(record.get("topic").asString(null))
                    .consumerCount(record.get("consumerCount").asInt(0))
                    .status(record.get("status").asString(null))
                    .producerIds(record.get("producerIds").asList(org.neo4j.driver.Value::asString, new ArrayList<>()))
                    .consumerIds(record.get("consumerIds").asList(org.neo4j.driver.Value::asString, new ArrayList<>()))
                    .build());
            }
        }

        return GroupedTopologyData.builder()
            .nodes(nodes)
            .edges(edges)
            .groups(groups)
            .consumerGroups(consumerGroups)
            .build();
    }

    public List<TopologyGroup> getAllGroups() {
        log.debug("Getting all service groups");

        List<TopologyGroup> groups = new ArrayList<>();
        try (Session session = neo4jDriver.session()) {
            Result groupResult = session.run(
                "MATCH (g:ServiceGroup) " +
                "OPTIONAL MATCH (parent:ServiceGroup)-[:CONTAINS_GROUP]->(g) " +
                "OPTIONAL MATCH (g)-[:CONTAINS]->(s:Service) " +
                "RETURN g.id AS id, g.name AS name, g.namespace AS namespace, " +
                "g.groupType AS groupType, g.description AS description, " +
                "g.collapsed AS collapsed, parent.id AS parentId, " +
                "count(DISTINCT s) AS serviceCount, " +
                "collect(DISTINCT s.id) AS serviceIds " +
                "ORDER BY g.name"
            );

            while (groupResult.hasNext()) {
                Record record = groupResult.next();
                groups.add(TopologyGroup.builder()
                    .id(record.get("id").asString())
                    .name(record.get("name").asString())
                    .namespace(record.get("namespace").asString(null))
                    .groupType(record.get("groupType").asString(null))
                    .description(record.get("description").asString(null))
                    .collapsed(record.get("collapsed").asBoolean(false))
                    .parentId(record.get("parentId").asString(null))
                    .serviceCount(record.get("serviceCount").asInt(0))
                    .serviceIds(record.get("serviceIds").asList(org.neo4j.driver.Value::asString, new ArrayList<>()))
                    .build());
            }
        }
        return groups;
    }

    public List<ConsumerGroupNode> getAllConsumerGroups() {
        log.debug("Getting all consumer groups");

        List<ConsumerGroupNode> consumerGroups = new ArrayList<>();
        try (Session session = neo4jDriver.session()) {
            Result cgResult = session.run(
                "MATCH (cg:ConsumerGroup) " +
                "OPTIONAL MATCH (producer:Service)-[:PRODUCES_TO]->(cg) " +
                "OPTIONAL MATCH (cg)-[:HAS_CONSUMER]->(consumer:Service) " +
                "RETURN cg.id AS id, cg.name AS name, cg.namespace AS namespace, " +
                "cg.messageQueue AS messageQueue, cg.topic AS topic, " +
                "cg.consumerCount AS consumerCount, cg.status AS status, " +
                "collect(DISTINCT producer.id) AS producerIds, " +
                "collect(DISTINCT consumer.id) AS consumerIds " +
                "ORDER BY cg.name"
            );

            while (cgResult.hasNext()) {
                Record record = cgResult.next();
                consumerGroups.add(ConsumerGroupNode.builder()
                    .id(record.get("id").asString())
                    .name(record.get("name").asString())
                    .namespace(record.get("namespace").asString(null))
                    .messageQueue(record.get("messageQueue").asString(null))
                    .topic(record.get("topic").asString(null))
                    .consumerCount(record.get("consumerCount").asInt(0))
                    .status(record.get("status").asString(null))
                    .producerIds(record.get("producerIds").asList(org.neo4j.driver.Value::asString, new ArrayList<>()))
                    .consumerIds(record.get("consumerIds").asList(org.neo4j.driver.Value::asString, new ArrayList<>()))
                    .build());
            }
        }
        return consumerGroups;
    }

    public TopologyGroup createGroup(TopologyGroup group) {
        log.debug("Creating service group: {}", group.getName());

        String namespace = group.getNamespace() != null ? group.getNamespace() : "default";
        String groupId = namespace + "-" + group.getName();

        String now = LocalDateTime.now().toString();

        try (Session session = neo4jDriver.session()) {
            session.run(
                "MERGE (g:ServiceGroup {id: $id}) " +
                "SET g.name = $name, g.namespace = $namespace, " +
                "g.groupType = $groupType, g.description = $description, " +
                "g.collapsed = coalesce(g.collapsed, false), " +
                "g.createdAt = CASE WHEN g.createdAt IS NULL THEN $now ELSE g.createdAt END, " +
                "g.lastUpdated = $now",
                Map.of(
                    "id", groupId,
                    "name", group.getName(),
                    "namespace", namespace,
                    "groupType", group.getGroupType() != null ? group.getGroupType() : "custom",
                    "description", group.getDescription() != null ? group.getDescription() : "",
                    "now", now
                )
            );

            if (group.getParentId() != null) {
                session.run(
                    "MATCH (parent:ServiceGroup {id: $parentId}) " +
                    "MATCH (child:ServiceGroup {id: $childId}) " +
                    "MERGE (parent)-[:CONTAINS_GROUP]->(child) " +
                    "MERGE (child)-[:PARENT_GROUP]->(parent)",
                    Map.of("parentId", group.getParentId(), "childId", groupId)
                );
            }

            if (group.getServiceIds() != null) {
                for (String serviceId : group.getServiceIds()) {
                    session.run(
                        "MATCH (g:ServiceGroup {id: $groupId}) " +
                        "MATCH (s:Service {id: $serviceId}) " +
                        "MERGE (g)-[:CONTAINS]->(s) " +
                        "MERGE (s)-[:MEMBER_OF]->(g)",
                        Map.of("groupId", groupId, "serviceId", serviceId)
                    );
                }
            }
        }

        return TopologyGroup.builder()
            .id(groupId)
            .name(group.getName())
            .namespace(namespace)
            .groupType(group.getGroupType())
            .description(group.getDescription())
            .collapsed(false)
            .parentId(group.getParentId())
            .serviceIds(group.getServiceIds())
            .serviceCount(group.getServiceIds() != null ? group.getServiceIds().size() : 0)
            .build();
    }

    public void updateGroupCollapsed(String groupId, boolean collapsed) {
        log.debug("Updating group {} collapsed status to {}", groupId, collapsed);

        try (Session session = neo4jDriver.session()) {
            session.run(
                "MATCH (g:ServiceGroup {id: $groupId}) " +
                "SET g.collapsed = $collapsed, g.lastUpdated = $now",
                Map.of(
                    "groupId", groupId,
                    "collapsed", collapsed,
                    "now", LocalDateTime.now().toString()
                )
            );
        }
    }

    public void deleteGroup(String groupId) {
        log.debug("Deleting service group: {}", groupId);

        try (Session session = neo4jDriver.session()) {
            session.run(
                "MATCH (g:ServiceGroup {id: $groupId}) DETACH DELETE g",
                Map.of("groupId", groupId)
            );
        }
    }

    public void addServiceToGroup(String groupId, String serviceId) {
        log.debug("Adding service {} to group {}", serviceId, groupId);

        try (Session session = neo4jDriver.session()) {
            session.run(
                "MATCH (g:ServiceGroup {id: $groupId}) " +
                "MATCH (s:Service {id: $serviceId}) " +
                "MERGE (g)-[:CONTAINS]->(s) " +
                "MERGE (s)-[:MEMBER_OF]->(g) " +
                "SET g.lastUpdated = $now",
                Map.of(
                    "groupId", groupId,
                    "serviceId", serviceId,
                    "now", LocalDateTime.now().toString()
                )
            );
        }
    }

    public void removeServiceFromGroup(String groupId, String serviceId) {
        log.debug("Removing service {} from group {}", serviceId, groupId);

        try (Session session = neo4jDriver.session()) {
            session.run(
                "MATCH (g:ServiceGroup {id: $groupId})-[r1:CONTAINS]->(s:Service {id: $serviceId}) " +
                "MATCH (s)-[r2:MEMBER_OF]->(g) " +
                "DELETE r1, r2 " +
                "SET g.lastUpdated = $now",
                Map.of(
                    "groupId", groupId,
                    "serviceId", serviceId,
                    "now", LocalDateTime.now().toString()
                )
            );
        }
    }

    public List<TraceInfo> getTraceInfoList(int limit) {
        log.debug("Getting recent trace info list");

        List<TraceInfo> traces = new ArrayList<>();
        try (Session session = neo4jDriver.session()) {
            Result result = session.run(
                "MATCH (t:Trace) " +
                "RETURN t.traceId AS traceId, t.status AS status, " +
                "t.startTime AS startTime, t.endTime AS endTime, " +
                "t.durationMs AS durationMs, t.spanCount AS spanCount, " +
                "t.errorCount AS errorCount " +
                "ORDER BY t.startTime DESC " +
                "LIMIT $limit",
                Map.of("limit", limit)
            );

            while (result.hasNext()) {
                Record record = result.next();
                traces.add(TraceInfo.builder()
                    .traceId(record.get("traceId").asString())
                    .status(record.get("status").asString(null))
                    .startTime(record.get("startTime").asString(null))
                    .endTime(record.get("endTime").asString(null))
                    .durationMs(record.get("durationMs").asDouble(0))
                    .spanCount(record.get("spanCount").asInt(0))
                    .errorCount(record.get("errorCount").asInt(0))
                    .build());
            }
        }
        return traces;
    }

    public TraceDetail getTraceDetail(String traceId) {
        log.debug("Getting trace detail for: {}", traceId);

        TraceDetail detail = new TraceDetail();
        List<TraceCall> calls = new ArrayList<>();

        try (Session session = neo4jDriver.session()) {
            Result traceResult = session.run(
                "MATCH (t:Trace {traceId: $traceId}) " +
                "RETURN t.traceId AS traceId, t.status AS status, " +
                "t.startTime AS startTime, t.endTime AS endTime, " +
                "t.durationMs AS durationMs, t.spanCount AS spanCount, " +
                "t.errorCount AS errorCount",
                Map.of("traceId", traceId)
            );

            if (traceResult.hasNext()) {
                Record record = traceResult.next();
                detail.setTraceId(record.get("traceId").asString());
                detail.setStatus(record.get("status").asString(null));
                detail.setStartTime(record.get("startTime").asString(null));
                detail.setEndTime(record.get("endTime").asString(null));
                detail.setDurationMs(record.get("durationMs").asDouble(0));
                detail.setSpanCount(record.get("spanCount").asInt(0));
                detail.setErrorCount(record.get("errorCount").asInt(0));
            }

            Result callsResult = session.run(
                "MATCH (source:Service)-[c:CALLS]->(target:Service) " +
                "WHERE c.traceId = $traceId " +
                "RETURN source.id AS sourceId, source.name AS sourceName, " +
                "target.id AS targetId, target.name AS targetName, " +
                "c.callType AS callType, c.protocol AS protocol, " +
                "c.isAsync AS isAsync, c.messageQueue AS messageQueue, " +
                "c.httpMethod AS httpMethod, c.path AS path, " +
                "c.callCount AS callCount, c.errorCount AS errorCount, " +
                "c.avgLatencyMs AS avgLatencyMs, c.spanId AS spanId, " +
                "c.parentSpanId AS parentSpanId, c.correlationId AS correlationId",
                Map.of("traceId", traceId)
            );

            while (callsResult.hasNext()) {
                Record record = callsResult.next();
                calls.add(TraceCall.builder()
                    .sourceId(record.get("sourceId").asString())
                    .sourceName(record.get("sourceName").asString())
                    .targetId(record.get("targetId").asString())
                    .targetName(record.get("targetName").asString())
                    .callType(record.get("callType").asString(null))
                    .protocol(record.get("protocol").asString(null))
                    .isAsync(record.get("isAsync").asBoolean(false))
                    .messageQueue(record.get("messageQueue").asString(null))
                    .httpMethod(record.get("httpMethod").asString(null))
                    .path(record.get("path").asString(null))
                    .callCount(record.get("callCount").asLong(0))
                    .errorCount(record.get("errorCount").asLong(0))
                    .avgLatencyMs(record.get("avgLatencyMs").asDouble(0))
                    .spanId(record.get("spanId").asString(null))
                    .parentSpanId(record.get("parentSpanId").asString(null))
                    .correlationId(record.get("correlationId").asString(null))
                    .build());
            }
            detail.setCalls(calls);
        }

        return detail;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class GroupedTopologyData {
        private List<TopologyNode> nodes;
        private List<TopologyEdge> edges;
        private List<TopologyGroup> groups;
        private List<ConsumerGroupNode> consumerGroups;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class TopologyGroup {
        private String id;
        private String name;
        private String namespace;
        private String groupType;
        private String description;
        @Builder.Default
        private boolean collapsed = false;
        private String parentId;
        @Builder.Default
        private int serviceCount = 0;
        @Builder.Default
        private List<String> serviceIds = new ArrayList<>();
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class ConsumerGroupNode {
        private String id;
        private String name;
        private String namespace;
        private String messageQueue;
        private String topic;
        @Builder.Default
        private int consumerCount = 0;
        private String status;
        @Builder.Default
        private List<String> producerIds = new ArrayList<>();
        @Builder.Default
        private List<String> consumerIds = new ArrayList<>();
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class TraceInfo {
        private String traceId;
        private String status;
        private String startTime;
        private String endTime;
        private double durationMs;
        private int spanCount;
        private int errorCount;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class TraceCall {
        private String sourceId;
        private String sourceName;
        private String targetId;
        private String targetName;
        private String callType;
        private String protocol;
        private boolean isAsync;
        private String messageQueue;
        private String httpMethod;
        private String path;
        private long callCount;
        private long errorCount;
        private double avgLatencyMs;
        private String spanId;
        private String parentSpanId;
        private String correlationId;
    }

    @lombok.Data
    public static class TraceDetail {
        private String traceId;
        private String status;
        private String startTime;
        private String endTime;
        private double durationMs;
        private int spanCount;
        private int errorCount;
        @Builder.Default
        private List<TraceCall> calls = new ArrayList<>();
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class TopologyData {
        private List<TopologyNode> nodes;
        private List<TopologyEdge> edges;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class TopologyNode {
        private String id;
        private String name;
        private String namespace;
        private String type;
        private String language;
        private String version;
        private String status;
        private String serviceType;
        private String clusterIp;
        private String groupId;
        private String groupName;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class TopologyEdge {
        private String source;
        private String target;
        private String callType;
        private String protocol;
        private boolean isAsync;
        private String messageQueue;
        private String httpMethod;
        private String path;
        private long callCount;
        private long errorCount;
        private long successCount;
        private double avgLatencyMs;
        private String lastSeen;
        private String traceId;
        private String consumerGroup;
        private String messageTopic;
    }

    @lombok.Data
    public static class ServiceNodeDetail {
        private String id;
        private String name;
        private String namespace;
        private String type;
        private String language;
        private String version;
        private String status;
        private String serviceType;
        private String clusterIp;
        private String ports;
        private String labels;
        private String annotations;
        private String discoveredAt;
        private String lastUpdated;
        private List<ServiceCallDetail> incomingCalls;
        private List<ServiceCallDetail> outgoingCalls;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class ServiceCallDetail {
        private String serviceId;
        private String serviceName;
        private String callType;
        private String protocol;
        private boolean isAsync;
        private String messageQueue;
        private String httpMethod;
        private String path;
        private long callCount;
        private long errorCount;
        private double avgLatencyMs;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class TopologyStats {
        @Builder.Default
        private long totalServices = 0;
        @Builder.Default
        private List<String> namespaces = new ArrayList<>();
        @Builder.Default
        private List<String> languages = new ArrayList<>();
        @Builder.Default
        private List<String> serviceTypes = new ArrayList<>();
        @Builder.Default
        private long totalCallRelationships = 0;
        @Builder.Default
        private long totalCallCount = 0;
        @Builder.Default
        private long totalErrorCount = 0;
        @Builder.Default
        private double averageLatencyMs = 0;
    }

    public ImpactAnalysisResult getImpactAnalysis(String serviceId) {
        log.debug("Performing impact analysis for service: {}", serviceId);

        List<String> upstreamServices = new ArrayList<>();
        List<String> downstreamServices = new ArrayList<>();
        List<ImpactEdge> upstreamEdges = new ArrayList<>();
        List<ImpactEdge> downstreamEdges = new ArrayList<>();

        try (Session session = neo4jDriver.session()) {
            Result upstreamResult = session.run(
                "MATCH path = (upstream:Service)-[*1..3]->(target:Service {id: $serviceId}) " +
                "UNWIND relationships(path) AS r " +
                "WITH DISTINCT nodes(path)[0] AS upstream, r, nodes(path)[1] AS next " +
                "WHERE upstream.id <> $serviceId " +
                "RETURN DISTINCT upstream.id AS id, upstream.name AS name, " +
                "r.callCount AS callCount, r.qps AS qps, r.avgLatencyMs AS avgLatencyMs, " +
                "next.id AS targetId",
                Map.of("serviceId", serviceId)
            );

            Set<String> upstreamIds = new HashSet<>();
            while (upstreamResult.hasNext()) {
                Record record = upstreamResult.next();
                String id = record.get("id").asString();
                if (!upstreamIds.contains(id)) {
                    upstreamIds.add(id);
                    upstreamServices.add(id);
                }
                if (record.containsKey("callCount")) {
                    upstreamEdges.add(ImpactEdge.builder()
                        .source(id)
                        .target(record.get("targetId").asString(null))
                        .callCount(record.get("callCount").asLong(0))
                        .qps(record.get("qps").asDouble(0))
                        .avgLatencyMs(record.get("avgLatencyMs").asDouble(0))
                        .build());
                }
            }

            Result downstreamResult = session.run(
                "MATCH path = (source:Service {id: $serviceId})-[*1..3]->(downstream:Service) " +
                "UNWIND relationships(path) AS r " +
                "WITH DISTINCT nodes(path)[-1] AS downstream, r, nodes(path)[-2] AS prev " +
                "WHERE downstream.id <> $serviceId " +
                "RETURN DISTINCT downstream.id AS id, downstream.name AS name, " +
                "r.callCount AS callCount, r.qps AS qps, r.avgLatencyMs AS avgLatencyMs, " +
                "prev.id AS sourceId",
                Map.of("serviceId", serviceId)
            );

            Set<String> downstreamIds = new HashSet<>();
            while (downstreamResult.hasNext()) {
                Record record = downstreamResult.next();
                String id = record.get("id").asString();
                if (!downstreamIds.contains(id)) {
                    downstreamIds.add(id);
                    downstreamServices.add(id);
                }
                if (record.containsKey("callCount")) {
                    downstreamEdges.add(ImpactEdge.builder()
                        .source(record.get("sourceId").asString(null))
                        .target(id)
                        .callCount(record.get("callCount").asLong(0))
                        .qps(record.get("qps").asDouble(0))
                        .avgLatencyMs(record.get("avgLatencyMs").asDouble(0))
                        .build());
                }
            }
        }

        return ImpactAnalysisResult.builder()
            .serviceId(serviceId)
            .upstreamServices(upstreamServices)
            .downstreamServices(downstreamServices)
            .upstreamEdges(upstreamEdges)
            .downstreamEdges(downstreamEdges)
            .totalUpstreamImpact(upstreamServices.size())
            .totalDownstreamImpact(downstreamServices.size())
            .riskLevel(calculateRiskLevel(upstreamServices.size(), downstreamServices.size()))
            .build();
    }

    public ChangePredictionResult predictChangeImpact(String serviceId, String changeType) {
        log.debug("Predicting change impact for service: {}, change type: {}", serviceId, changeType);

        ImpactAnalysisResult impact = getImpactAnalysis(serviceId);

        List<ImpactedService> impactedServices = new ArrayList<>();
        double estimatedDowntimeMinutes = 0;
        double estimatedRecoveryHours = 0;

        try (Session session = neo4jDriver.session()) {
            for (String downstreamId : impact.getDownstreamServices()) {
                Result detailResult = session.run(
                    "MATCH (source:Service {id: $sourceId})-[c:CALLS]->(target:Service {id: $targetId}) " +
                    "RETURN c.callCount AS callCount, c.qps AS qps, c.avgLatencyMs AS avgLatencyMs, " +
                    "c.errorCount AS errorCount, c.protocol AS protocol",
                    Map.of("sourceId", serviceId, "targetId", downstreamId)
                );

                if (detailResult.hasNext()) {
                    Record record = detailResult.next();
                    long callCount = record.get("callCount").asLong(0);
                    double qps = record.get("qps").asDouble(0);
                    double avgLatency = record.get("avgLatencyMs").asDouble(0);
                    String protocol = record.get("protocol").asString("UNKNOWN");

                    ImpactSeverity severity = calculateSeverity(callCount, qps, protocol);
                    double impactScore = calculateImpactScore(callCount, qps, avgLatency);

                    impactedServices.add(ImpactedService.builder()
                        .serviceId(downstreamId)
                        .callCount(callCount)
                        .qps(qps)
                        .avgLatencyMs(avgLatency)
                        .severity(severity.name())
                        .impactScore(impactScore)
                        .build());

                    if (severity == ImpactSeverity.HIGH) {
                        estimatedDowntimeMinutes += 30;
                        estimatedRecoveryHours += 2;
                    } else if (severity == ImpactSeverity.MEDIUM) {
                        estimatedDowntimeMinutes += 10;
                        estimatedRecoveryHours += 0.5;
                    }
                }
            }
        }

        impactedServices.sort((a, b) -> Double.compare(b.getImpactScore(), a.getImpactScore()));

        long highSeverityCount = impactedServices.stream().filter(s -> "HIGH".equals(s.getSeverity())).count();
        long mediumSeverityCount = impactedServices.stream().filter(s -> "MEDIUM".equals(s.getSeverity())).count();
        long lowSeverityCount = impactedServices.stream().filter(s -> "LOW".equals(s.getSeverity())).count();

        return ChangePredictionResult.builder()
            .serviceId(serviceId)
            .changeType(changeType)
            .impactedServices(impactedServices)
            .totalImpactedServices(impactedServices.size())
            .highSeverityCount(highSeverityCount)
            .mediumSeverityCount(mediumSeverityCount)
            .lowSeverityCount(lowSeverityCount)
            .estimatedDowntimeMinutes(estimatedDowntimeMinutes)
            .estimatedRecoveryHours(estimatedRecoveryHours)
            .recommendation(generateRecommendation(changeType, highSeverityCount, impactedServices.size()))
            .build();
    }

    private String calculateRiskLevel(int upstreamCount, int downstreamCount) {
        int total = upstreamCount + downstreamCount;
        if (total >= 10) return "HIGH";
        if (total >= 5) return "MEDIUM";
        return "LOW";
    }

    private ImpactSeverity calculateSeverity(long callCount, double qps, String protocol) {
        double score = 0;
        if (callCount > 10000) score += 3;
        else if (callCount > 1000) score += 2;
        else if (callCount > 100) score += 1;

        if (qps > 100) score += 3;
        else if (qps > 10) score += 2;
        else if (qps > 1) score += 1;

        if ("HTTP".equals(protocol) || "gRPC".equals(protocol)) score += 1;

        if (score >= 5) return ImpactSeverity.HIGH;
        if (score >= 3) return ImpactSeverity.MEDIUM;
        return ImpactSeverity.LOW;
    }

    private double calculateImpactScore(long callCount, double qps, double avgLatency) {
        return (callCount * 0.1) + (qps * 10) + (avgLatency * 0.01);
    }

    private String generateRecommendation(String changeType, long highSeverityCount, int totalImpacted) {
        StringBuilder sb = new StringBuilder();

        if (highSeverityCount > 0) {
            sb.append("【高风险】存在").append(highSeverityCount).append("个高影响服务，建议：");
            sb.append("1. 先在预发布环境充分验证；");
            sb.append("2. 采用灰度发布策略；");
            sb.append("3. 准备回滚方案；");
        } else if (totalImpacted > 0) {
            sb.append("【中风险】影响").append(totalImpacted).append("个服务，建议：");
            sb.append("1. 进行回归测试；");
            sb.append("2. 监控关键指标；");
        } else {
            sb.append("【低风险】无直接依赖服务，可正常发布；");
        }

        if ("database".equals(changeType) || "schema".equals(changeType)) {
            sb.append("数据库变更需额外考虑数据迁移和兼容性；");
        } else if ("api".equals(changeType)) {
            sb.append("API变更需确保向下兼容，提供版本过渡；");
        }

        return sb.toString();
    }

    private enum ImpactSeverity {
        HIGH, MEDIUM, LOW
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class ImpactAnalysisResult {
        private String serviceId;
        @Builder.Default
        private List<String> upstreamServices = new ArrayList<>();
        @Builder.Default
        private List<String> downstreamServices = new ArrayList<>();
        @Builder.Default
        private List<ImpactEdge> upstreamEdges = new ArrayList<>();
        @Builder.Default
        private List<ImpactEdge> downstreamEdges = new ArrayList<>();
        private int totalUpstreamImpact;
        private int totalDownstreamImpact;
        private String riskLevel;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class ImpactEdge {
        private String source;
        private String target;
        private long callCount;
        private double qps;
        private double avgLatencyMs;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class ChangePredictionResult {
        private String serviceId;
        private String changeType;
        @Builder.Default
        private List<ImpactedService> impactedServices = new ArrayList<>();
        private int totalImpactedServices;
        private long highSeverityCount;
        private long mediumSeverityCount;
        private long lowSeverityCount;
        private double estimatedDowntimeMinutes;
        private double estimatedRecoveryHours;
        private String recommendation;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class ImpactedService {
        private String serviceId;
        private long callCount;
        private double qps;
        private double avgLatencyMs;
        private String severity;
        private double impactScore;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class TrafficEstimate {
        private String edgeId;
        private String source;
        private String target;
        private double currentQps;
        private double peakQps;
        private double dailyCalls;
        private double projectedGrowthRate;
        private double projectedQpsNextMonth;
        private String trafficLevel;
    }
}
