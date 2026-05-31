package com.datacheck.datasource;

import com.datacheck.model.enums.DataSourceType;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;

@Component
public class DataSourceAdapterFactory {

    private final Map<DataSourceType, DataSourceAdapter> adapterMap;

    @Autowired
    public DataSourceAdapterFactory(List<DataSourceAdapter> adapters) {
        this.adapterMap = new EnumMap<>(DataSourceType.class);
        for (DataSourceAdapter adapter : adapters) {
            adapterMap.put(adapter.getType(), adapter);
        }
    }

    public DataSourceAdapter getAdapter(DataSourceType type) {
        DataSourceAdapter adapter = adapterMap.get(type);
        if (adapter == null) {
            throw new IllegalArgumentException("No adapter found for data source type: " + type);
        }
        return adapter;
    }
}
