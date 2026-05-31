package com.datatransfer.migration.adapter;

import com.datatransfer.migration.engine.DataSourceReader;
import com.datatransfer.migration.engine.DataSourceWriter;

import java.util.List;
import java.util.Map;

public interface DataSourceAdapter {
    boolean testConnection();

    DataSourceReader createReader();

    DataSourceWriter createWriter();

    List<String> listTables();

    Map<String, String> getTableSchema(String tableName);
}
