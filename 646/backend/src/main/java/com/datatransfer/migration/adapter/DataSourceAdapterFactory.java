package com.datatransfer.migration.adapter;

import com.datatransfer.migration.model.DataSource;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
public class DataSourceAdapterFactory {
    private final Map<String, AdapterCreator> registry = new HashMap<>();

    public DataSourceAdapterFactory() {
        registry.put("mysql", MysqlDataSourceAdapter::new);
        registry.put("postgresql", MysqlDataSourceAdapter::new);
        registry.put("mongodb", MysqlDataSourceAdapter::new);
    }

    public DataSourceAdapter createAdapter(DataSource dataSource) {
        AdapterCreator creator = registry.get(dataSource.getType().toLowerCase());
        if (creator == null) {
            throw new IllegalArgumentException("Unsupported data source type: " + dataSource.getType());
        }
        return creator.create(dataSource);
    }

    public boolean supports(String type) {
        return registry.containsKey(type.toLowerCase());
    }

    @FunctionalInterface
    private interface AdapterCreator {
        DataSourceAdapter create(DataSource dataSource);
    }
}
