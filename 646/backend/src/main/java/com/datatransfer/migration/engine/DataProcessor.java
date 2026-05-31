package com.datatransfer.migration.engine;

import java.util.List;

public interface DataProcessor {
    default void open() throws Exception {
    }

    void process(Record record) throws Exception;

    default void processBatch(List<Record> records) throws Exception {
        for (Record record : records) {
            process(record);
        }
    }

    default void close() throws Exception {
    }

    default DataProcessor andThen(DataProcessor next) {
        DataProcessor self = this;
        return new DataProcessor() {
            @Override
            public void open() throws Exception {
                self.open();
                next.open();
            }

            @Override
            public void process(Record record) throws Exception {
                self.process(record);
                next.process(record);
            }

            @Override
            public void processBatch(List<Record> records) throws Exception {
                self.processBatch(records);
                next.processBatch(records);
            }

            @Override
            public void close() throws Exception {
                self.close();
                next.close();
            }
        };
    }
}
