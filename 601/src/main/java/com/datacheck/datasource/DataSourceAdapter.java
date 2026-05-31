package com.datacheck.datasource;

import com.datacheck.model.CheckTask;
import com.datacheck.model.DataRecord;
import com.datacheck.model.enums.DataSourceType;

import java.util.Iterator;
import java.util.List;
import java.util.Map;

public interface DataSourceAdapter {

    DataSourceType getType();

    Iterator<DataRecord> iterateSource(CheckTask task);

    Iterator<DataRecord> iterateTarget(CheckTask task);

    DataRecord getSourceRecord(String key, CheckTask task);

    DataRecord getTargetRecord(String key, CheckTask task);

    long getSourceCount(CheckTask task);

    long getTargetCount(CheckTask task);

    boolean insertTarget(DataRecord record, CheckTask task);

    boolean updateTarget(DataRecord record, CheckTask task);

    boolean deleteTarget(String key, CheckTask task);

    List<String> getPrimaryKeys(String tableName);

    List<String> getColumns(String tableName);
}
