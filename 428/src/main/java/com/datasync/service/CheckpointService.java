package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.Checkpoint;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
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
public class CheckpointService {

    private final SyncConfig syncConfig;
    private final ObjectMapper objectMapper;

    private Checkpoint currentCheckpoint;
    private final AtomicBoolean dirty = new AtomicBoolean(false);

    public CheckpointService(SyncConfig syncConfig, ObjectMapper objectMapper) {
        this.syncConfig = syncConfig;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void init() {
        if (!syncConfig.getCheckpoint().isEnabled()) {
            log.info("Checkpoint is disabled");
            currentCheckpoint = new Checkpoint();
            return;
        }

        loadCheckpoint();
    }

    @PreDestroy
    public void destroy() {
        saveCheckpoint();
    }

    public void updateCheckpoint(String database, String table,
                                 String binlogFileName, long binlogPosition, long timestamp) {
        if (!syncConfig.getCheckpoint().isEnabled()) {
            return;
        }

        currentCheckpoint.updateTableCheckpoint(database, table, binlogFileName, binlogPosition, timestamp);
        currentCheckpoint.setUpdateTime(System.currentTimeMillis());
        dirty.set(true);
    }

    public Checkpoint.TableCheckpoint getTableCheckpoint(String database, String table) {
        if (currentCheckpoint == null) {
            return null;
        }
        return currentCheckpoint.getTableCheckpoint(database, table);
    }

    public Checkpoint getCurrentCheckpoint() {
        return currentCheckpoint;
    }

    @Scheduled(fixedDelayString = "${sync.checkpoint.interval-ms:5000}")
    public void scheduledSave() {
        if (dirty.getAndSet(false)) {
            saveCheckpoint();
        }
    }

    private void loadCheckpoint() {
        try {
            SyncConfig.CheckpointConfig config = syncConfig.getCheckpoint();
            Path checkpointPath = getCheckpointPath();

            if (!Files.exists(checkpointPath)) {
                log.info("No checkpoint file found, starting fresh");
                currentCheckpoint = createNewCheckpoint();
                return;
            }

            String content = new String(Files.readAllBytes(checkpointPath));
            currentCheckpoint = objectMapper.readValue(content, Checkpoint.class);
            log.info("Loaded checkpoint from: {}", checkpointPath);

        } catch (Exception e) {
            log.error("Failed to load checkpoint, starting fresh", e);
            currentCheckpoint = createNewCheckpoint();
        }
    }

    private void saveCheckpoint() {
        if (!syncConfig.getCheckpoint().isEnabled() || currentCheckpoint == null) {
            return;
        }

        try {
            Path checkpointPath = getCheckpointPath();
            Files.createDirectories(checkpointPath.getParent());

            String content = objectMapper.writerWithDefaultPrettyPrinter()
                    .writeValueAsString(currentCheckpoint);
            Files.write(checkpointPath, content.getBytes());

            log.debug("Checkpoint saved to: {}", checkpointPath);
        } catch (Exception e) {
            log.error("Failed to save checkpoint", e);
        }
    }

    private Path getCheckpointPath() {
        SyncConfig.CheckpointConfig config = syncConfig.getCheckpoint();
        String filePath = config.getFilePath();
        if (filePath == null || filePath.isEmpty()) {
            filePath = "./checkpoint";
        }
        return Paths.get(filePath, "checkpoint.json");
    }

    private Checkpoint createNewCheckpoint() {
        Checkpoint checkpoint = new Checkpoint();
        checkpoint.setDestination(syncConfig.getCanal().getDestination());
        checkpoint.setCreateTime(System.currentTimeMillis());
        checkpoint.setUpdateTime(System.currentTimeMillis());
        return checkpoint;
    }

    public void forceSave() {
        saveCheckpoint();
    }

    public void resetCheckpoint() {
        currentCheckpoint = createNewCheckpoint();
        dirty.set(true);
        saveCheckpoint();
        log.info("Checkpoint has been reset");
    }

    public boolean hasCheckpoint(String database, String table) {
        if (currentCheckpoint == null) {
            return false;
        }
        return currentCheckpoint.getTableCheckpoint(database, table) != null;
    }

    public String getBinlogFileName(String database, String table) {
        Checkpoint.TableCheckpoint tc = getTableCheckpoint(database, table);
        return tc != null ? tc.getBinlogFileName() : null;
    }

    public long getBinlogPosition(String database, String table) {
        Checkpoint.TableCheckpoint tc = getTableCheckpoint(database, table);
        return tc != null ? tc.getBinlogPosition() : 0;
    }
}
