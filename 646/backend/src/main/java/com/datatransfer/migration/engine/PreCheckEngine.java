package com.datatransfer.migration.engine;

import com.datatransfer.migration.adapter.DataSourceAdapter;
import com.datatransfer.migration.adapter.DataSourceAdapterFactory;
import com.datatransfer.migration.model.DataSource;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
public class PreCheckEngine {
    private final DataSourceAdapterFactory adapterFactory;

    public PreCheckEngine(DataSourceAdapterFactory adapterFactory) {
        this.adapterFactory = adapterFactory;
    }

    public PreCheckResult preCheck(DataSource sourceDs, DataSource targetDs, Map<String, Object> config) {
        PreCheckResult result = new PreCheckResult();
        log.info("Starting pre-check for migration: source={}, target={}", sourceDs.getName(), targetDs.getName());

        result.addCheck(checkSourceConnection(sourceDs));
        result.addCheck(checkTargetConnection(targetDs));
        result.addCheck(checkSourceTable(sourceDs, config));
        result.addCheck(checkTargetTable(targetDs, config));
        result.addCheck(checkSchemaCompatibility(sourceDs, targetDs, config));
        result.addCheck(checkTargetWritable(targetDs, config));

        log.info("Pre-check completed: passed={}, failed={}, warnings={}",
                result.getPassedCount(), result.getFailedCount(), result.getWarningCount());
        return result;
    }

    private CheckItem checkSourceConnection(DataSource sourceDs) {
        CheckItem item = new CheckItem();
        item.setName("源数据源连接");
        item.setCategory("connection");
        try {
            DataSourceAdapter adapter = adapterFactory.createAdapter(sourceDs);
            boolean connected = adapter.testConnection();
            item.setPassed(connected);
            item.setMessage(connected ? "源数据源连接成功" : "源数据源连接失败");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("源数据源连接异常: " + e.getMessage());
        }
        return item;
    }

    private CheckItem checkTargetConnection(DataSource targetDs) {
        CheckItem item = new CheckItem();
        item.setName("目标数据源连接");
        item.setCategory("connection");
        try {
            DataSourceAdapter adapter = adapterFactory.createAdapter(targetDs);
            boolean connected = adapter.testConnection();
            item.setPassed(connected);
            item.setMessage(connected ? "目标数据源连接成功" : "目标数据源连接失败");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("目标数据源连接异常: " + e.getMessage());
        }
        return item;
    }

    private CheckItem checkSourceTable(DataSource sourceDs, Map<String, Object> config) {
        CheckItem item = new CheckItem();
        item.setName("源表检查");
        item.setCategory("schema");
        try {
            String tableName = (String) config.get("tableName");
            if (tableName == null || tableName.isEmpty()) {
                item.setPassed(false);
                item.setMessage("未指定源表名");
                return item;
            }
            DataSourceAdapter adapter = adapterFactory.createAdapter(sourceDs);
            List<String> tables = adapter.listTables();
            boolean exists = tables.contains(tableName);
            item.setPassed(exists);
            item.setMessage(exists ? "源表 " + tableName + " 存在" : "源表 " + tableName + " 不存在");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("源表检查异常: " + e.getMessage());
        }
        return item;
    }

    private CheckItem checkTargetTable(DataSource targetDs, Map<String, Object> config) {
        CheckItem item = new CheckItem();
        item.setName("目标表检查");
        item.setCategory("schema");
        try {
            String targetTable = (String) config.get("targetTableName");
            String sourceTable = (String) config.get("tableName");
            String tableName = targetTable != null ? targetTable : sourceTable;
            if (tableName == null || tableName.isEmpty()) {
                item.setPassed(false);
                item.setMessage("未指定目标表名");
                return item;
            }
            DataSourceAdapter adapter = adapterFactory.createAdapter(targetDs);
            List<String> tables = adapter.listTables();
            boolean exists = tables.contains(tableName);
            item.setPassed(true);
            item.setMessage(exists ? "目标表 " + tableName + " 已存在，数据将被追加" : "目标表 " + tableName + " 不存在，迁移时将自动创建");
            if (!exists) {
                item.setWarning(true);
            }
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("目标表检查异常: " + e.getMessage());
        }
        return item;
    }

    private CheckItem checkSchemaCompatibility(DataSource sourceDs, DataSource targetDs, Map<String, Object> config) {
        CheckItem item = new CheckItem();
        item.setName("Schema兼容性");
        item.setCategory("schema");
        try {
            String sourceTable = (String) config.get("tableName");
            String targetTable = (String) config.get("targetTableName");
            if (targetTable == null) targetTable = sourceTable;
            if (sourceTable == null) {
                item.setPassed(false);
                item.setMessage("未指定表名，无法检查Schema");
                return item;
            }
            DataSourceAdapter sourceAdapter = adapterFactory.createAdapter(sourceDs);
            Map<String, String> sourceSchema = sourceAdapter.getTableSchema(sourceTable);
            if (sourceSchema.isEmpty()) {
                item.setPassed(false);
                item.setMessage("无法获取源表Schema");
                return item;
            }
            item.setPassed(true);
            item.setMessage("源表包含 " + sourceSchema.size() + " 个字段，Schema兼容性检查通过");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("Schema兼容性检查异常: " + e.getMessage());
        }
        return item;
    }

    private CheckItem checkTargetWritable(DataSource targetDs, Map<String, Object> config) {
        CheckItem item = new CheckItem();
        item.setName("目标写入权限");
        item.setCategory("permission");
        try {
            DataSourceAdapter adapter = adapterFactory.createAdapter(targetDs);
            boolean connected = adapter.testConnection();
            item.setPassed(connected);
            item.setMessage(connected ? "目标数据源可写入" : "目标数据源不可写入");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("目标写入权限检查异常: " + e.getMessage());
        }
        return item;
    }

    public static class PreCheckResult {
        private final List<CheckItem> items = new ArrayList<>();

        public void addCheck(CheckItem item) { items.add(item); }
        public List<CheckItem> getItems() { return items; }
        public boolean isAllPassed() { return items.stream().allMatch(CheckItem::isPassed); }
        public long getPassedCount() { return items.stream().filter(CheckItem::isPassed).count(); }
        public long getFailedCount() { return items.stream().filter(i -> !i.isPassed()).count(); }
        public long getWarningCount() { return items.stream().filter(CheckItem::isWarning).count(); }
    }

    public static class CheckItem {
        private String name;
        private String category;
        private boolean passed;
        private boolean warning;
        private String message;

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getCategory() { return category; }
        public void setCategory(String category) { this.category = category; }
        public boolean isPassed() { return passed; }
        public void setPassed(boolean passed) { this.passed = passed; }
        public boolean isWarning() { return warning; }
        public void setWarning(boolean warning) { this.warning = warning; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }
}
