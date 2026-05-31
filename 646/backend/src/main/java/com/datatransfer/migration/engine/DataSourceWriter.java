package com.datatransfer.migration.engine;

import java.util.List;
import java.util.Map;

public interface DataSourceWriter extends AutoCloseable {
    void open(Map<String, Object> config) throws Exception;

    void write(Record record) throws Exception;

    void writeBatch(List<Record> records) throws Exception;

    void flush();

    void close() throws Exception;
}
