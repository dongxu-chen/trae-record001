package com.dbpool.optimizer.parser;

import com.dbpool.optimizer.model.PoolType;
import org.springframework.stereotype.Component;
import java.util.EnumMap;
import java.util.Map;

@Component
public class PoolConfigParserFactory {

    private final Map<PoolType, PoolConfigParser> parsers = new EnumMap<>(PoolType.class);

    public PoolConfigParserFactory(HikariCPConfigParser hikariParser,
                                   DruidConfigParser druidParser,
                                   TomcatJDBCConfigParser tomcatParser) {
        parsers.put(PoolType.HIKARICP, hikariParser);
        parsers.put(PoolType.DRUID, druidParser);
        parsers.put(PoolType.TOMCAT_JDBC, tomcatParser);
    }

    public PoolConfigParser getParser(PoolType poolType) {
        PoolConfigParser parser = parsers.get(poolType);
        if (parser == null) {
            throw new IllegalArgumentException("Unsupported pool type: " + poolType);
        }
        return parser;
    }

    public PoolConfigParser getParserByName(String poolTypeName) {
        for (Map.Entry<PoolType, PoolConfigParser> entry : parsers.entrySet()) {
            if (entry.getValue().getPoolTypeName().equalsIgnoreCase(poolTypeName)
                    || entry.getKey().name().equalsIgnoreCase(poolTypeName)) {
                return entry.getValue();
            }
        }
        throw new IllegalArgumentException("Unsupported pool type: " + poolTypeName);
    }
}
