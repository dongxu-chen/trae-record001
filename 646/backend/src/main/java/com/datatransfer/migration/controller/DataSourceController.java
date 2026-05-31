package com.datatransfer.migration.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.datatransfer.migration.model.DataSource;
import com.datatransfer.migration.service.DataSourceService;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/datasources")
public class DataSourceController {
    private final DataSourceService dataSourceService;

    public DataSourceController(DataSourceService dataSourceService) {
        this.dataSourceService = dataSourceService;
    }

    @GetMapping
    public Map<String, Object> list(@RequestParam(defaultValue = "1") int page,
                                    @RequestParam(defaultValue = "10") int size,
                                    @RequestParam(required = false) String type) {
        Page<DataSource> result = dataSourceService.list(page, size, type);
        Map<String, Object> response = new HashMap<>();
        response.put("list", result.getRecords());
        response.put("total", result.getTotal());
        response.put("page", page);
        response.put("size", size);
        return response;
    }

    @GetMapping("/{id}")
    public DataSource getById(@PathVariable Long id) {
        return dataSourceService.getById(id);
    }

    @PostMapping
    public DataSource create(@RequestBody DataSource dataSource) {
        return dataSourceService.create(dataSource);
    }

    @PutMapping("/{id}")
    public DataSource update(@PathVariable Long id, @RequestBody DataSource dataSource) {
        return dataSourceService.update(id, dataSource);
    }

    @DeleteMapping("/{id}")
    public Map<String, Object> delete(@PathVariable Long id) {
        boolean success = dataSourceService.delete(id);
        Map<String, Object> response = new HashMap<>();
        response.put("success", success);
        return response;
    }

    @PostMapping("/{id}/test")
    public Map<String, Object> testConnection(@PathVariable Long id) {
        return dataSourceService.testConnection(id);
    }

    @GetMapping("/{id}/tables")
    public List<String> listTables(@PathVariable Long id) {
        return dataSourceService.listTables(id);
    }

    @GetMapping("/{id}/tables/{tableName}/schema")
    public Map<String, String> getTableSchema(@PathVariable Long id, @PathVariable String tableName) {
        return dataSourceService.getTableSchema(id, tableName);
    }
}
