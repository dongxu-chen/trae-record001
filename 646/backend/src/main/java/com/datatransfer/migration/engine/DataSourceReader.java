package com.datatransfer.migration.engine;

import java.util.List;
import java.util.Map;

public interface DataSourceReader extends AutoCloseable {
    void open(Map<String, Object> config) throws Exception;

    void openFromPosition(Map<String, Object> config, CheckpointInfo checkpoint) throws Exception;

    boolean hasNext();

    Record next();

    List<Record> nextBatch(int batchSize);

    long getTotalCount();

    CheckpointInfo currentCheckpoint();

    void close() throws Exception;
}
