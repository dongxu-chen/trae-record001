package com.logplatform.service;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.logplatform.model.LogEntry;
import com.logplatform.model.LogQueryRequest;
import com.logplatform.model.LogQueryResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.zip.GZIPOutputStream;

@Slf4j
@Service
@RequiredArgsConstructor
public class LogQueryService {

    private final ElasticsearchQueryService elasticsearchQueryService;

    @Value("${query.cache-expire-seconds:300}")
    private int cacheExpireSeconds;

    @Value("${query.cache-max-size:1000}")
    private int cacheMaxSize;

    @Value("${export.max-export-size:10000}")
    private int maxExportSize;

    private final Cache<String, LogQueryResult> queryCache = Caffeine.newBuilder()
            .expireAfterWrite(5, TimeUnit.MINUTES)
            .maximumSize(1000)
            .build();

    public LogQueryResult search(LogQueryRequest request) {
        String cacheKey = buildCacheKey(request);
        LogQueryResult cachedResult = queryCache.getIfPresent(cacheKey);

        if (cachedResult != null) {
            log.debug("Cache hit for query: {}", cacheKey);
            return cachedResult;
        }

        LogQueryResult result = elasticsearchQueryService.search(request);

        if (result.getTookMs() < 1000) {
            queryCache.put(cacheKey, result);
        }

        return result;
    }

    public long count(LogQueryRequest request) {
        return elasticsearchQueryService.count(request);
    }

    public byte[] exportAsCsv(LogQueryRequest request) throws Exception {
        request.setSize(Math.min(request.getSize(), maxExportSize));
        request.setHighlight(false);

        LogQueryResult result = elasticsearchQueryService.search(request);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        GZIPOutputStream gzip = new GZIPOutputStream(out);
        Writer writer = new OutputStreamWriter(gzip, StandardCharsets.UTF_8);

        String[] headers = {"id", "timestamp", "appName", "level", "logger", "thread",
                "message", "stackTrace", "host", "ip", "traceId"};

        CSVFormat csvFormat = CSVFormat.DEFAULT.builder()
                .setHeader(headers)
                .build();

        try (CSVPrinter printer = new CSVPrinter(writer, csvFormat)) {
            for (LogEntry entry : result.getLogs()) {
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
            }
        }

        return out.toByteArray();
    }

    public byte[] exportAsJson(LogQueryRequest request) throws Exception {
        request.setSize(Math.min(request.getSize(), maxExportSize));
        request.setHighlight(false);

        LogQueryResult result = elasticsearchQueryService.search(request);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        GZIPOutputStream gzip = new GZIPOutputStream(out);
        Writer writer = new OutputStreamWriter(gzip, StandardCharsets.UTF_8);

        com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
        writer.write(mapper.writeValueAsString(result.getLogs()));
        writer.flush();
        gzip.finish();

        return out.toByteArray();
    }

    private String buildCacheKey(LogQueryRequest request) {
        return String.format("%s_%s_%s_%s_%s_%d_%d_%b",
                request.getQuery(),
                request.getAppName(),
                request.getLevel(),
                request.getStartTime(),
                request.getEndTime(),
                request.getPage(),
                request.getSize(),
                request.isHighlight());
    }

    public void evictCache() {
        queryCache.invalidateAll();
        log.info("Query cache evicted");
    }
}
