package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.SyncTopology;
import com.datasync.model.ValidationResult;
import com.datasync.model.Watermark;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.search.Search;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.lang.management.OperatingSystemMXBean;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
public class TopologyService {

    private final SyncConfig syncConfig;
    private final MetricsService metricsService;
    private final CheckpointService checkpointService;
    private final WatermarkManager watermarkManager;
    private final DataValidationService validationService;
    private final MeterRegistry meterRegistry;

    private final Map<String, AtomicLong> tableLatencyMap = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> tableThroughputMap = new ConcurrentHashMap<>();

    @Value("${spring.application.name:mysql-to-clickhouse-sync}")
    private String applicationName;

    @Value("${sync.canal.host:localhost}")
    private String canalHost;

    @Value("${sync.canal.port:11111}")
    private int canalPort;

    @Value("${spring.kafka.bootstrap-servers:localhost:9092}")
    private String kafkaServers;

    @Value("${sync.clickhouse.url:jdbc:clickhouse://localhost:8123/default}")
    private String clickhouseUrl;

    @Autowired
    public TopologyService(SyncConfig syncConfig,
                           MetricsService metricsService,
                           CheckpointService checkpointService,
                           WatermarkManager watermarkManager,
                           DataValidationService validationService,
                           MeterRegistry meterRegistry) {
        this.syncConfig = syncConfig;
        this.metricsService = metricsService;
        this.checkpointService = checkpointService;
        this.watermarkManager = watermarkManager;
        this.validationService = validationService;
        this.meterRegistry = meterRegistry;
    }

    public SyncTopology buildTopology() {
        SyncTopology topology = SyncTopology.builder()
                .syncId(UUID.randomUUID().toString())
                .timestamp(System.currentTimeMillis())
                .status("RUNNING")
                .version("1.0.0")
                .nodes(new ArrayList<>())
                .links(new ArrayList<>())
                .stats(new HashMap<>())
                .build();

        int xPos = 100;
        int yPos = 200;

        SyncTopology.Node mysqlNode = createMySQLNode(xPos, yPos);
        topology.getNodes().add(mysqlNode);

        xPos += 250;
        SyncTopology.Node canalNode = createCanalNode(xPos, yPos);
        topology.getNodes().add(canalNode);

        SyncTopology.Link mysqlToCanalLink = createLink(
                mysqlNode.getId(),
                canalNode.getId(),
                SyncTopology.LinkType.BINLOG,
                "Binlog streaming"
        );
        topology.getLinks().add(mysqlToCanalLink);

        xPos += 250;
        SyncTopology.Node syncServiceNode = createSyncServiceNode(xPos, yPos);
        topology.getNodes().add(syncServiceNode);

        SyncTopology.Link canalToSyncLink = createLink(
                canalNode.getId(),
                syncServiceNode.getId(),
                SyncTopology.LinkType.BINLOG,
                "Canal client"
        );
        topology.getLinks().add(canalToSyncLink);

        if (syncConfig.getKafka().isEnabled()) {
            xPos += 250;
            SyncTopology.Node kafkaNode = createKafkaNode(xPos, yPos);
            topology.getNodes().add(kafkaNode);

            SyncTopology.Link syncToKafkaLink = createLink(
                    syncServiceNode.getId(),
                    kafkaNode.getId(),
                    SyncTopology.LinkType.KAFKA_PRODUCE,
                    "Kafka produce"
            );
            topology.getLinks().add(syncToKafkaLink);

            xPos += 250;
            SyncTopology.Node afterKafkaSyncNode = createSyncServiceNode(xPos, yPos);
            afterKafkaSyncNode.setId("sync_consumer");
            afterKafkaSyncNode.setName("Sync Consumer");
            topology.getNodes().add(afterKafkaSyncNode);

            SyncTopology.Link kafkaToSyncLink = createLink(
                    kafkaNode.getId(),
                    afterKafkaSyncNode.getId(),
                    SyncTopology.LinkType.KAFKA_CONSUME,
                    "Kafka consume"
            );
            topology.getLinks().add(kafkaToSyncLink);

            xPos += 250;
            SyncTopology.Node clickhouseNode = createClickHouseNode(xPos, yPos);
            topology.getNodes().add(clickhouseNode);

            SyncTopology.Link syncToChLink = createLink(
                    afterKafkaSyncNode.getId(),
                    clickhouseNode.getId(),
                    SyncTopology.LinkType.DATA_WRITE,
                    "ClickHouse write"
            );
            topology.getLinks().add(syncToChLink);
        } else {
            xPos += 250;
            SyncTopology.Node clickhouseNode = createClickHouseNode(xPos, yPos);
            topology.getNodes().add(clickhouseNode);

            SyncTopology.Link syncToChLink = createLink(
                    syncServiceNode.getId(),
                    clickhouseNode.getId(),
                    SyncTopology.LinkType.DATA_WRITE,
                    "ClickHouse write"
            );
            topology.getLinks().add(syncToChLink);
        }

        xPos += 250;
        SyncTopology.Node monitoringNode = createMonitoringNode(xPos, yPos);
        topology.getNodes().add(monitoringNode);

        addTableNodes(topology);
        updateTopologyStats(topology);

        return topology;
    }

    private SyncTopology.Node createMySQLNode(int x, int y) {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("type", "MySQL");
        metrics.put("tables", syncConfig.getTables().size());

        return SyncTopology.Node.builder()
                .id(SyncTopology.generateNodeId(SyncTopology.NodeType.MYSQL, "source"))
                .name("MySQL Source")
                .type(SyncTopology.NodeType.MYSQL)
                .status("HEALTHY")
                .metrics(metrics)
                .x(x)
                .y(y)
                .description("MySQL source database")
                .build();
    }

    private SyncTopology.Node createCanalNode(int x, int y) {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("host", canalHost);
        metrics.put("port", canalPort);
        metrics.put("destination", syncConfig.getCanal().getDestination());

        return SyncTopology.Node.builder()
                .id(SyncTopology.generateNodeId(SyncTopology.NodeType.CANAL, "server"))
                .name("Canal Server")
                .type(SyncTopology.NodeType.CANAL)
                .status("HEALTHY")
                .metrics(metrics)
                .x(x)
                .y(y)
                .description("Canal binlog subscriber")
                .build();
    }

    private SyncTopology.Node createSyncServiceNode(int x, int y) {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("mode", syncConfig.getMode().name());
        metrics.put("checkpointEnabled", syncConfig.getCheckpoint().isEnabled());

        MemoryMXBean memoryBean = ManagementFactory.getMemoryMXBean();
        metrics.put("heapUsed", memoryBean.getHeapMemoryUsage().getUsed() / 1024 / 1024 + "MB");
        metrics.put("heapMax", memoryBean.getHeapMemoryUsage().getMax() / 1024 / 1024 + "MB");

        OperatingSystemMXBean osBean = ManagementFactory.getOperatingSystemMXBean();
        metrics.put("processCpuLoad", osBean.getSystemLoadAverage());

        return SyncTopology.Node.builder()
                .id(SyncTopology.generateNodeId(SyncTopology.NodeType.SYNC_SERVICE, "main"))
                .name("Sync Service")
                .type(SyncTopology.NodeType.SYNC_SERVICE)
                .status("HEALTHY")
                .metrics(metrics)
                .x(x)
                .y(y)
                .description("Data sync service")
                .build();
    }

    private SyncTopology.Node createKafkaNode(int x, int y) {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("bootstrapServers", kafkaServers);
        metrics.put("topicPrefix", syncConfig.getKafka().getTopicPrefix());

        return SyncTopology.Node.builder()
                .id(SyncTopology.generateNodeId(SyncTopology.NodeType.KAFKA, "cluster"))
                .name("Kafka Cluster")
                .type(SyncTopology.NodeType.KAFKA)
                .status("HEALTHY")
                .metrics(metrics)
                .x(x)
                .y(y)
                .description("Kafka message queue")
                .build();
    }

    private SyncTopology.Node createClickHouseNode(int x, int y) {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("url", clickhouseUrl);
        metrics.put("database", syncConfig.getClickhouse().getDatabase());
        metrics.put("batchSize", syncConfig.getClickhouse().getBatchSize());

        return SyncTopology.Node.builder()
                .id(SyncTopology.generateNodeId(SyncTopology.NodeType.CLICKHOUSE, "target"))
                .name("ClickHouse Target")
                .type(SyncTopology.NodeType.CLICKHOUSE)
                .status("HEALTHY")
                .metrics(metrics)
                .x(x)
                .y(y)
                .description("ClickHouse target database")
                .build();
    }

    private SyncTopology.Node createMonitoringNode(int x, int y) {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("prometheusEnabled", true);
        metrics.put("endpoint", "/actuator/prometheus");

        return SyncTopology.Node.builder()
                .id(SyncTopology.generateNodeId(SyncTopology.NodeType.MONITORING, "prometheus"))
                .name("Monitoring")
                .type(SyncTopology.NodeType.MONITORING)
                .status("HEALTHY")
                .metrics(metrics)
                .x(x)
                .y(y)
                .description("Prometheus metrics")
                .build();
    }

    private SyncTopology.Link createLink(String sourceId, String targetId,
                                          SyncTopology.LinkType type, String description) {
        return SyncTopology.Link.builder()
                .id(SyncTopology.generateLinkId(sourceId, targetId))
                .source(sourceId)
                .target(targetId)
                .type(type)
                .status("HEALTHY")
                .description(description)
                .metrics(new HashMap<>())
                .build();
    }

    private void addTableNodes(SyncTopology topology) {
        int baseX = 100;
        int baseY = 400;
        int spacing = 200;

        for (int i = 0; i < syncConfig.getTables().size(); i++) {
            SyncConfig.TableMapping tableMapping = syncConfig.getTables().get(i);
            int x = baseX + i * spacing;

            String tableKey = tableMapping.getSourceSchema() + "." + tableMapping.getSourceTable();
            Map<String, Object> tableMetrics = getTableMetrics(tableMapping);

            SyncTopology.Node tableNode = SyncTopology.Node.builder()
                    .id("table_" + tableMapping.getSourceSchema() + "_" + tableMapping.getSourceTable())
                    .name(tableMapping.getSourceTable())
                    .type(SyncTopology.NodeType.MYSQL)
                    .status(getTableStatus(tableMapping))
                    .metrics(tableMetrics)
                    .x(x)
                    .y(baseY)
                    .description("Sync table: " + tableMapping.getSourceSchema() + "." + tableMapping.getSourceTable()
                            + " -> " + tableMapping.getTargetDatabase() + "." + tableMapping.getTargetTable())
                    .build();

            topology.getNodes().add(tableNode);
        }
    }

    private Map<String, Object> getTableMetrics(SyncConfig.TableMapping tableMapping) {
        Map<String, Object> metrics = new HashMap<>();
        String schema = tableMapping.getSourceSchema();
        String table = tableMapping.getSourceTable();

        metrics.put("source", schema + "." + table);
        metrics.put("target", tableMapping.getTargetDatabase() + "." + tableMapping.getTargetTable());
        metrics.put("syncMode", tableMapping.getSyncMode().name());
        metrics.put("conflictStrategy", tableMapping.getConflictStrategy().name());
        metrics.put("primaryKeys", tableMapping.getPrimaryKeys());
        metrics.put("columns", tableMapping.getColumnMapping().size());

        Watermark.TableWatermark watermark = watermarkManager.getWatermark(schema, table);
        if (watermark != null) {
            metrics.put("watermarkStatus", watermark.getStatus());
            metrics.put("watermarkBinlog", watermark.getBinlogFileName() + "@" + watermark.getBinlogPosition());
            metrics.put("fullSyncCompleted", watermarkManager.isFullSyncCompleted(schema, table));
        }

        ValidationResult validationResult = validationService.getLastValidationResult(schema, table);
        if (validationResult != null) {
            metrics.put("lastValidation", validationResult.getStatus().name());
            metrics.put("matchRate", String.format("%.2f%%", validationResult.getMatchRate()));
            metrics.put("diffCount", validationResult.getDiffCount());
        }

        return metrics;
    }

    private String getTableStatus(SyncConfig.TableMapping tableMapping) {
        String schema = tableMapping.getSourceSchema();
        String table = tableMapping.getSourceTable();

        if (!watermarkManager.isFullSyncCompleted(schema, table)) {
            if (watermarkManager.getWatermark(schema, table) != null) {
                return "FULL_SYNC";
            }
            return "PENDING";
        }

        ValidationResult validation = validationService.getLastValidationResult(schema, table);
        if (validation != null) {
            if (validation.getStatus() == ValidationResult.ValidationStatus.ERROR
                    || validation.getStatus() == ValidationResult.ValidationStatus.FAILED) {
                return "ERROR";
            }
            if (validation.getMatchRate() < 99.9) {
                return "WARNING";
            }
        }

        return "HEALTHY";
    }

    private void updateTopologyStats(SyncTopology topology) {
        Map<String, Object> stats = topology.getStats();

        stats.put("totalTables", syncConfig.getTables().size());
        stats.put("kafkaEnabled", syncConfig.getKafka().isEnabled());
        stats.put("syncMode", syncConfig.getMode().name());
        stats.put("checkpointEnabled", syncConfig.getCheckpoint().isEnabled());

        int healthyTables = 0;
        int syncingTables = 0;
        int errorTables = 0;

        for (SyncConfig.TableMapping tableMapping : syncConfig.getTables()) {
            String status = getTableStatus(tableMapping);
            switch (status) {
                case "HEALTHY":
                    healthyTables++;
                    break;
                case "FULL_SYNC":
                case "PENDING":
                    syncingTables++;
                    break;
                case "ERROR":
                case "WARNING":
                    errorTables++;
                    break;
            }
        }

        stats.put("healthyTables", healthyTables);
        stats.put("syncingTables", syncingTables);
        stats.put("errorTables", errorTables);
        stats.put("generatedAt", System.currentTimeMillis());
    }

    public void recordTableLatency(String tableKey, long latencyMs) {
        tableLatencyMap.computeIfAbsent(tableKey, k -> new AtomicLong(0))
                .set(latencyMs);
    }

    public void recordTableThroughput(String tableKey, long rows) {
        tableThroughputMap.computeIfAbsent(tableKey, k -> new AtomicLong(0))
                .addAndGet(rows);
    }

    public Map<String, Object> getTopologySummary() {
        Map<String, Object> summary = new HashMap<>();
        summary.put("totalNodes", syncConfig.getTables().size() + 5);
        summary.put("totalLinks", syncConfig.getKafka().isEnabled() ? 8 : 5);
        summary.put("status", "RUNNING");
        summary.put("timestamp", System.currentTimeMillis());

        int healthy = 0;
        int warning = 0;
        int error = 0;

        for (SyncConfig.TableMapping table : syncConfig.getTables()) {
            String status = getTableStatus(table);
            switch (status) {
                case "HEALTHY":
                    healthy++;
                    break;
                case "WARNING":
                    warning++;
                    break;
                case "ERROR":
                    error++;
                    break;
            }
        }

        summary.put("healthyTables", healthy);
        summary.put("warningTables", warning);
        summary.put("errorTables", error);

        return summary;
    }
}
