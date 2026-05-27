package com.datasecurity.masking.proxy;

import java.sql.ResultSet;
import java.util.List;
import java.util.Map;

public interface DataMaskingProxy {

    ResultSet executeQuery(String sql, ResultSet originalResultSet);

    List<Map<String, Object>> maskResult(List<Map<String, Object>> originalResult, String databaseId);

    Map<String, Object> maskRow(Map<String, Object> originalRow, String databaseId);
}
