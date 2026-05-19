package com.logplatform.service;

import com.logplatform.model.ExportTask;
import com.logplatform.model.LogEntry;
import com.logplatform.model.LogQueryRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.zip.GZIPOutputStream;

@Slf4j
@Service
@RequiredArgsConstructor
public class AsyncExportService {

    private final ElasticsearchQueryService elasticsearchQueryService;

    @Value("${export.temp-dir:/tmp/log-exports}")
    private String tempDir;

    @Value("${export.base-url:/api/logs/export/download}")
    private String baseUrl;

    @Value("${export.chunk-size:1000}")
    private int chunkSize;

    private final Map<String, ExportTask> exportTasks = new ConcurrentHashMap<>();

    private static final String[] CSV_HEADERS = {
            "id", "timestamp", "appName", "level", "logger", "thread",
            "message", "stackTrace", "host", "ip", "traceId"
    };

    public ExportTask createExportTask(LogQueryRequest queryRequest,
                                       int maxRecords,
                                       ExportTask.ExportFormat format) {
        String taskId = UUID.randomUUID().toString();
        String fileName = generateFileName(format);

        ExportTask task = ExportTask.builder()
                .taskId(taskId)
                .status(ExportTask.ExportStatus.PENDING)
                .format(format)
                .queryRequest(queryRequest)
                .totalRecords(maxRecords)
                .exportedRecords(0)
                .fileName(fileName)
                .fileUrl(baseUrl + "/" + taskId)
                .createdAt(Instant.now())
                .build();

        exportTasks.put(taskId, task);

        processExportAsync(taskId);

        return task;
    }

    @Async("taskExecutor")
    public void processExportAsync(String taskId) {
        ExportTask task = exportTasks.get(taskId);
        if (task == null) {
            log.warn("Export task not found: {}", taskId);
            return;
        }

        try {
            task.setStatus(ExportTask.ExportStatus.PROCESSING);
            exportTasks.put(taskId, task);

            Path filePath = Paths.get(tempDir, task.getFileName());
            Files.createDirectories(filePath.getParent());

            long exported = switch (task.getFormat()) {
                case CSV -> exportAsCsv(task, filePath);
                case JSON -> exportAsJson(task, filePath);
            };

            task.setStatus(ExportTask.ExportStatus.COMPLETED);
            task.setExportedRecords(exported);
            task.setFileSize(Files.size(filePath));
            task.setCompletedAt(Instant.now());
            task.setFileUrl(baseUrl + "/" + taskId);

            log.info("Export task completed: {} records={}", taskId, exported);

        } catch (Exception e) {
            log.error("Export task failed: {}", taskId, e);
            task.setStatus(ExportTask.ExportStatus.FAILED);
            task.setErrorMessage(e.getMessage());
            task.setCompletedAt(Instant.now());
        }

        exportTasks.put(taskId, task);
    }

    private long exportAsCsv(ExportTask task, Path filePath) throws Exception {
        LogQueryRequest query = task.getQueryRequest();
        query.setHighlight(false);
        query.setSize(chunkSize);

        AtomicLong exported = new AtomicLong(0);
        long maxRecords = task.getTotalRecords();

        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(new GZIPOutputStream(
                        Files.newOutputStream(filePath)), StandardCharsets.UTF_8));
             CSVPrinter printer = new CSVPrinter(writer, CSVFormat.DEFAULT.builder()
                     .setHeader(CSV_HEADERS)
                     .build())) {

            int page = 0;
            boolean hasMore = true;

            while (hasMore && exported.get() < maxRecords) {
                query.setPage(page);
                int remaining = (int) Math.min(chunkSize, maxRecords - exported.get());
                query.setSize(remaining);

                List<LogEntry> logs = fetchLogs(query);

                if (logs.isEmpty()) {
                    hasMore = false;
                    break;
                }

                for (LogEntry entry : logs) {
                    if (exported.get() >= maxRecords) break;

                    printer.printRecord(
                            entry.getId(),
                            entry.getTimestamp() != null ? entry.getTimestamp().toString() : "",
                            entry.getAppName(),
                            entry.getLevel(),
                            entry.getLogger(),
                            entry.getThread(),
                            entry.getMessage(),
                            entry.getStackTrace(),
                            entry.getHost(),
                            entry.getIp(),
                            entry.getTraceId()
                    );
                    exported.incrementAndGet();
                }

                task.setExportedRecords(exported.get());
                exportTasks.put(task.getTaskId(), task);

                page++;
                if (logs.size() < chunkSize) {
                    hasMore = false;
                }

                Thread.sleep(10);
            }
        }

        return exported.get();
    }

    private long exportAsJson(ExportTask task, Path filePath) throws Exception {
        LogQueryRequest query = task.getQueryRequest();
        query.setHighlight(false);
        query.setSize(chunkSize);

        AtomicLong exported = new AtomicLong(0);
        long maxRecords = task.getTotalRecords();
        com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();

        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(new GZIPOutputStream(
                        Files.newOutputStream(filePath)), StandardCharsets.UTF_8))) {

            writer.write("[");
            boolean first = true;

            int page = 0;
            boolean hasMore = true;

            while (hasMore && exported.get() < maxRecords) {
                query.setPage(page);
                int remaining = (int) Math.min(chunkSize, maxRecords - exported.get());
                query.setSize(remaining);

                List<LogEntry> logs = fetchLogs(query);

                if (logs.isEmpty()) {
                    hasMore = false;
                    break;
                }

                for (LogEntry entry : logs) {
                    if (exported.get() >= maxRecords) break;

                    if (!first) {
                        writer.write(",");
                    }
                    first = false;

                    writer.write(mapper.writeValueAsString(entry));
                    exported.incrementAndGet();
                }

                task.setExportedRecords(exported.get());
                exportTasks.put(task.getTaskId(), task);

                page++;
                if (logs.size() < chunkSize) {
                    hasMore = false;
                }

                Thread.sleep(10);
            }

            writer.write("]");
        }

        return exported.get();
    }

    private List<LogEntry> fetchLogs(LogQueryRequest query) {
        return elasticsearchQueryService.search(query).getLogs();
    }

    private String generateFileName(ExportTask.ExportFormat format) {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String ext = format == ExportTask.ExportFormat.CSV ? "csv" : "json";
        return String.format("logs_export_%s.%s.gz", timestamp, ext);
    }

    public ExportTask getTaskStatus(String taskId) {
        return exportTasks.get(taskId);
    }

    public List<ExportTask> listTasks() {
        return new ArrayList<>(exportTasks.values());
    }

    public Path getExportFilePath(String taskId) {
        ExportTask task = exportTasks.get(taskId);
        if (task == null || task.getStatus() != ExportTask.ExportStatus.COMPLETED) {
            return null;
        }
        return Paths.get(tempDir, task.getFileName());
    }

    public void cleanupOldTasks(long maxAgeMinutes) {
        long cutoff = System.currentTimeMillis() - maxAgeMinutes * 60 * 1000;
        exportTasks.entrySet().removeIf(entry -> {
            ExportTask task = entry.getValue();
            if (task.getCompletedAt() != null
                    && task.getCompletedAt().toEpochMilli() < cutoff) {
                try {
                    Path filePath = Paths.get(tempDir, task.getFileName());
                    Files.deleteIfExists(filePath);
                } catch (IOException e) {
                    log.warn("Failed to delete export file: {}", task.getFileName(), e);
                }
                return true;
            }
            return false;
        });
    }
}
