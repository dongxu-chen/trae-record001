package com.dbpool.optimizer.parser;

import com.dbpool.optimizer.model.PoolConfig;
import java.util.Map;
import java.util.Properties;

public interface PoolConfigParser {
    PoolConfig parse(Map<String, String> configMap);
    PoolConfig parseProperties(Properties properties);
    Map<String, String> exportConfig(PoolConfig config);
    Properties exportProperties(PoolConfig config);
    String getPoolTypeName();
}
