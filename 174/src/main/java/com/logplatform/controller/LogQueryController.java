package com.logplatform.controller;

import com.logplatform.model.ExportRequest;
import com.logplatform.model.ExportTask;
import com.logplatform.model.LogEntry;
import com.logplatform.model.LogQueryRequest;
import com.logplatform.model.LogQueryResult;
import com.logplatform.service.AsyncExportService;
import com.logplatform.service.LogIngestionService;
import com.logplatform.service.LogQueryService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.PathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/logs")
@RequiredArgsConstructor
public class LogQueryController {

    private final LogQueryService logQueryService;
    private final LogIngestionService logIngestionService;
    private final AsyncExportService asyncExportService;

    @PostMapping("/search")
    public ResponseEntity<LogQueryResult> search(@Valid @RequestBody LogQueryRequest request) {
        log.debug("Search request: {}", request);
        LogQueryResult result = logQueryService.search(request);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/count")
    public ResponseEntity<Map<String, Long>> count(@RequestBody LogQueryRequest request) {
        long count = logQueryService.count(request);
        return ResponseEntity.ok(Map.of("count", count));
    }

    @PostMapping("/export/async")
    public ResponseEntity<ExportTask> createAsyncExport(@Valid @RequestBody ExportRequest request) {
        ExportTask task = asyncExportService.createExportTask(
                request.getQuery(),
                request.getMaxRecords(),
                request.getFormat()
        );
        return ResponseEntity.accepted().body(task);
    }

    @GetMapping("/export/tasks")
    public ResponseEntity<List<ExportTask>> listExportTasks() {
        return ResponseEntity.ok(asyncExportService.listTasks());
    }

    @GetMapping("/export/tasks/{taskId}")
    public ResponseEntity<ExportTask> getExportTaskStatus(@PathVariable String taskId) {
        ExportTask task = asyncExportService.getTaskStatus(taskId);
        if (task == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(task);
    }

    @GetMapping("/export/download/{taskId}")
    public ResponseEntity<Resource> downloadExport(@PathVariable String taskId) {
        Path filePath = asyncExportService.getExportFilePath(taskId);
        if (filePath == null) {
            return ResponseEntity.notFound().build();
        }

        ExportTask task = asyncExportService.getTaskStatus(taskId);
        Resource resource = new PathResource(filePath);

        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("application/gzip"))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + task.getFileName() + "\"")
                .body(resource);
    }

    @PostMapping("/export/csv")
    @Deprecated
    public ResponseEntity<byte[]> exportCsv(@RequestBody LogQueryRequest request) throws Exception {
        byte[] data = logQueryService.exportAsCsv(request);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("application/gzip"));
        headers.setContentDispositionFormData("attachment", "logs.csv.gz");
        return ResponseEntity.ok().headers(headers).body(data);
    }

    @PostMapping("/export/json")
    @Deprecated
    public ResponseEntity<byte[]> exportJson(@RequestBody LogQueryRequest request) throws Exception {
        byte[] data = logQueryService.exportAsJson(request);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("application/gzip"));
        headers.setContentDispositionFormData("attachment", "logs.json.gz");
        return ResponseEntity.ok().headers(headers).body(data);
    }

    @PostMapping("/ingest")
    public ResponseEntity<Map<String, String>> ingest(@RequestBody LogEntry logEntry) {
        logIngestionService.ingest(logEntry);
        return ResponseEntity.ok(Map.of("status", "accepted", "pending", String.valueOf(logIngestionService.getPendingCount())));
    }

    @PostMapping("/ingest/batch")
    public ResponseEntity<Map<String, String>> ingestBatch(@RequestBody List<LogEntry> entries) {
        logIngestionService.ingest(entries);
        return ResponseEntity.ok(Map.of("status", "accepted", "count", String.valueOf(entries.size()),
                "pending", String.valueOf(logIngestionService.getPendingCount())));
    }

    @PostMapping("/cache/evict")
    public ResponseEntity<Map<String, String>> evictCache() {
        logQueryService.evictCache();
        return ResponseEntity.ok(Map.of("status", "success", "message", "Cache evicted"));
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        return ResponseEntity.ok(Map.of(
                "pendingIngestion", logIngestionService.getPendingCount(),
                "status", "running"
        ));
    }
}
