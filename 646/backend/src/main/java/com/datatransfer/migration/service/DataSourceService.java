package com.datatransfer.migration.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.datatransfer.migration.adapter.DataSourceAdapter;
import com.datatransfer.migration.adapter.DataSourceAdapterFactory;
import com.datatransfer.migration.model.DataSource;
import com.datatransfer.migration.repository.DataSourceRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class DataSourceService {
    private final DataSourceRepository dataSourceRepository;
    private final DataSourceAdapterFactory adapterFactory;

    public DataSourceService(DataSourceRepository dataSourceRepository,
                             DataSourceAdapterFactory adapterFactory) {
        this.dataSourceRepository = dataSourceRepository;
        this.adapterFactory = adapterFactory;
    }

    public Page<DataSource> list(int page, int size, String type) {
        LambdaQueryWrapper<DataSource> wrapper = new LambdaQueryWrapper<>();
        if (type != null && !type.isEmpty()) {
            wrapper.eq(DataSource::getType, type);
        }
        wrapper.orderByDesc(DataSource::getCreatedAt);
        return dataSourceRepository.selectPage(new Page<>(page, size), wrapper);
    }

    public DataSource getById(Long id) {
        return dataSourceRepository.selectById(id);
    }

    public DataSource create(DataSource dataSource) {
        dataSource.setCreatedAt(LocalDateTime.now());
        dataSource.setUpdatedAt(LocalDateTime.now());
        dataSource.setStatus("inactive");
        dataSource.setCreatorId(1L);
        dataSourceRepository.insert(dataSource);
        return dataSource;
    }

    public DataSource update(Long id, DataSource dataSource) {
        dataSource.setId(id);
        dataSource.setUpdatedAt(LocalDateTime.now());
        dataSourceRepository.updateById(dataSource);
        return dataSource;
    }

    public boolean delete(Long id) {
        return dataSourceRepository.deleteById(id) > 0;
    }

    public Map<String, Object> testConnection(Long id) {
        Map<String, Object> result = new HashMap<>();
        try {
            DataSource dataSource = dataSourceRepository.selectById(id);
            if (dataSource == null) {
                result.put("success", false);
                result.put("message", "DataSource not found");
                return result;
            }

            DataSourceAdapter adapter = adapterFactory.createAdapter(dataSource);
            boolean success = adapter.testConnection();

            dataSource.setStatus(success ? "active" : "inactive");
            dataSource.setUpdatedAt(LocalDateTime.now());
            dataSourceRepository.updateById(dataSource);

            result.put("success", success);
            result.put("message", success ? "Connection successful" : "Connection failed");
        } catch (Exception e) {
            log.error("Connection test failed", e);
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }

    public List<String> listTables(Long id) {
        DataSource dataSource = dataSourceRepository.selectById(id);
        if (dataSource == null) {
            return List.of();
        }
        DataSourceAdapter adapter = adapterFactory.createAdapter(dataSource);
        return adapter.listTables();
    }

    public Map<String, String> getTableSchema(Long id, String tableName) {
        DataSource dataSource = dataSourceRepository.selectById(id);
        if (dataSource == null) {
            return Map.of();
        }
        DataSourceAdapter adapter = adapterFactory.createAdapter(dataSource);
        return adapter.getTableSchema(tableName);
    }
}
