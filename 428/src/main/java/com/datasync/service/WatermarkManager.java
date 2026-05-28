package com.datasync.service;

import com.datasync.model.Watermark;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.atomic.AtomicBoolean;

@Slf4j
@Service
public class WatermarkManager {

    private final ObjectMapper objectMapper;

    private Watermark watermark;
    private final AtomicBoolean dirty = new AtomicBoolean(false);
    private static final String WATERMARK_FILE = "watermark.json";

    public WatermarkManager(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void init() {
        loadWatermark();
    }

    @PreDestroy
    public void destroy() {
        saveWatermark();
    }

    private void loadWatermark() {
        try {
            Path watermarkPath = getWatermarkPath();
            if (!Files.exists(watermarkPath)) {
                log.info("No watermark file found, starting fresh");
                watermark = new Watermark();
                return;
            }

            String content = new String(Files.readAllBytes(watermarkPath));
            watermark = objectMapper.readValue(content, Watermark.class);
            log.info("Loaded watermark from: {}", watermarkPath);
        } catch (Exception e) {
            log.error("Failed to load watermark, starting fresh", e);
            watermark = new Watermark();
        }
    }

    private void saveWatermark() {
        if (watermark == null) {
            return;
        }

        try {
            Path watermarkPath = getWatermarkPath();
            Files.createDirectories(watermarkPath.getParent());

            String content = objectMapper.writerWithDefaultPrettyPrinter()
                    .writeValueAsString(watermark);
            Files.write(watermarkPath, content.getBytes());

            log.debug("Watermark saved to: {}", watermarkPath);
        } catch (Exception e) {
            log.error("Failed to save watermark", e);
        }
    }

    private Path getWatermarkPath() {
        return Paths.get("./checkpoint", WATERMARK_FILE);
    }

    public void recordFullSyncStart(String database, String table,
                                    String binlogFileName, long binlogPosition) {
        Watermark.TableWatermark tableWatermark = Watermark.TableWatermark.builder()
                .database(database)
                .table(table)
                .binlogFileName(binlogFileName)
                .binlogPosition(binlogPosition)
                .timestamp(System.currentTimeMillis())
                .type(Watermark.TableWatermark.WatermarkType.FULL_SYNC_START)
                .status(Watermark.TableWatermark.Status.RUNNING.name())
                .fullSyncStartTime(System.currentTimeMillis())
                .build();

        watermark.setTableWatermark(database, table, tableWatermark);
        dirty.set(true);
        saveWatermark();

        log.info("Recorded full sync start watermark for {}.{}: {}@{}",
                database, table, binlogFileName, binlogPosition);
    }

    public void recordFullSyncEnd(String database, String table) {
        Watermark.TableWatermark existing = watermark.getTableWatermark(database, table);
        if (existing == null) {
            log.warn("No existing watermark found for {}.{} when recording full sync end",
                    database, table);
            return;
        }

        existing.setType(Watermark.TableWatermark.WatermarkType.FULL_SYNC_END);
        existing.setStatus(Watermark.TableWatermark.Status.COMPLETED.name());
        existing.setFullSyncEndTime(System.currentTimeMillis());

        dirty.set(true);
        saveWatermark();

        log.info("Recorded full sync end watermark for {}.{}", database, table);
    }

    public void recordFullSyncFailed(String database, String table, String error) {
        Watermark.TableWatermark existing = watermark.getTableWatermark(database, table);
        if (existing == null) {
            return;
        }

        existing.setStatus(Watermark.TableWatermark.Status.FAILED.name());
        existing.setFullSyncEndTime(System.currentTimeMillis());

        dirty.set(true);
        saveWatermark();

        log.error("Recorded full sync failed for {}.{}: {}", database, table, error);
    }

    public void recordIncrementalStart(String database, String table,
                                       String binlogFileName, long binlogPosition) {
        Watermark.TableWatermark tableWatermark = Watermark.TableWatermark.builder()
                .database(database)
                .table(table)
                .binlogFileName(binlogFileName)
                .binlogPosition(binlogPosition)
                .timestamp(System.currentTimeMillis())
                .type(Watermark.TableWatermark.WatermarkType.INCREMENTAL_START)
                .status(Watermark.TableWatermark.Status.RUNNING.name())
                .build();

        watermark.setTableWatermark(database, table, tableWatermark);
        dirty.set(true);
        saveWatermark();

        log.info("Recorded incremental start watermark for {}.{}: {}@{}",
                database, table, binlogFileName, binlogPosition);
    }

    public Watermark.TableWatermark getWatermark(String database, String table) {
        return watermark.getTableWatermark(database, table);
    }

    public boolean shouldSkipIncrementalEvent(String database, String table,
                                               String binlogFileName, long binlogPosition) {
        Watermark.TableWatermark watermark = this.watermark.getTableWatermark(database, table);

        if (watermark == null) {
            return false;
        }

        if (!Watermark.TableWatermark.Status.COMPLETED.name().equals(watermark.getStatus())) {
            return true;
        }

        return isBeforeWatermark(binlogFileName, binlogPosition,
                watermark.getBinlogFileName(), watermark.getBinlogPosition());
    }

    private boolean isBeforeWatermark(String currentFile, long currentPos,
                                      String watermarkFile, long watermarkPos) {
        if (currentFile == null || watermarkFile == null) {
            return false;
        }

        int fileCompare = currentFile.compareTo(watermarkFile);
        if (fileCompare < 0) {
            return true;
        } else if (fileCompare > 0) {
            return false;
        } else {
            return currentPos < watermarkPos;
        }
    }

    public boolean isFullSyncCompleted(String database, String table) {
        return watermark.isFullSyncCompleted(database, table);
    }

    public boolean canStartIncremental(String database, String table) {
        return watermark.canStartIncremental(database, table);
    }

    public Watermark getWatermark() {
        return watermark;
    }

    public void forceSave() {
        saveWatermark();
    }

    public void resetWatermark(String database, String table) {
        watermark.getTableWatermarks().remove(database + "." + table);
        dirty.set(true);
        saveWatermark();
        log.info("Reset watermark for {}.{}", database, table);
    }

    public void resetAll() {
        watermark = new Watermark();
        dirty.set(true);
        saveWatermark();
        log.info("Reset all watermarks");
    }
}
