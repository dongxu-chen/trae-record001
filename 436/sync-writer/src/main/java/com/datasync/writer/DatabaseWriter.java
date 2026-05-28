package com.datasync.writer;

import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.SyncResult;

import java.util.List;

public interface DatabaseWriter {
    SyncResult write(DataChangeEvent event);

    List<SyncResult> writeBatch(List<DataChangeEvent> events);

    boolean isHealthy();

    void shutdown();
}
