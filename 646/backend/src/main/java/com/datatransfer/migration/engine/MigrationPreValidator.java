package com.datatransfer.migration.engine;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class MigrationPreValidator {

    public ValidationResult validate(ValidationContext ctx) {
        ValidationResult result = new ValidationResult();
        List<ValidationItem> items = new ArrayList<>();

        items.add(checkSourceConnection(ctx));
        items.add(checkTargetConnection(ctx));
        items.add(checkSourceTableExists(ctx));
        items.add(checkTargetTableExists(ctx));
        items.add(checkSourceTablePermissions(ctx));
        items.add(checkTargetTablePermissions(ctx));
        items.add(checkTableSchemaCompatibility(ctx));

        result.setItems(items);
        result.setValid(items.stream().allMatch(ValidationItem::isPassed));
        result.setValidatedAt(LocalDateTime.now());

        long passed = items.stream().filter(ValidationItem::isPassed).count();
        long failed = items.size() - passed;
        result.setSummary(String.format("检查项 %d 项，通过 %d 项，失败 %d 项", items.size(), passed, failed));

        return result;
    }

    private ValidationItem checkSourceConnection(ValidationContext ctx) {
        ValidationItem item = new ValidationItem("source_connection", "源数据源连接检查");
        try {
            boolean ok = ctx.getSourceAdapter() != null && ctx.getSourceAdapter().testConnection();
            item.setPassed(ok);
            item.setMessage(ok ? "源数据源连接成功" : "源数据源连接失败");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("源数据源连接异常: " + e.getMessage());
        }
        return item;
    }

    private ValidationItem checkTargetConnection(ValidationContext ctx) {
        ValidationItem item = new ValidationItem("target_connection", "目标数据源连接检查");
        try {
            boolean ok = ctx.getTargetAdapter() != null && ctx.getTargetAdapter().testConnection();
            item.setPassed(ok);
            item.setMessage(ok ? "目标数据源连接成功" : "目标数据源连接失败");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("目标数据源连接异常: " + e.getMessage());
        }
        return item;
    }

    private ValidationItem checkSourceTableExists(ValidationContext ctx) {
        ValidationItem item = new ValidationItem("source_table_exists", "源表存在性检查");
        try {
            if (ctx.getSourceTableName() == null || ctx.getSourceTableName().isEmpty()) {
                item.setPassed(false);
                item.setMessage("源表名未配置");
                return item;
            }
            List<String> tables = ctx.getSourceAdapter().listTables();
            boolean exists = tables.contains(ctx.getSourceTableName());
            item.setPassed(exists);
            item.setMessage(exists ? "源表存在" : "源表不存在: " + ctx.getSourceTableName());
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("源表检查异常: " + e.getMessage());
        }
        return item;
    }

    private ValidationItem checkTargetTableExists(ValidationContext ctx) {
        ValidationItem item = new ValidationItem("target_table_exists", "目标表存在性检查");
        try {
            if (ctx.getTargetTableName() == null || ctx.getTargetTableName().isEmpty()) {
                item.setPassed(false);
                item.setMessage("目标表名未配置");
                return item;
            }
            List<String> tables = ctx.getTargetAdapter().listTables();
            boolean exists = tables.contains(ctx.getTargetTableName());
            item.setPassed(exists);
            item.setMessage(exists ? "目标表存在" : "目标表不存在: " + ctx.getTargetTableName());
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("目标表检查异常: " + e.getMessage());
        }
        return item;
    }

    private ValidationItem checkSourceTablePermissions(ValidationContext ctx) {
        ValidationItem item = new ValidationItem("source_permissions", "源表权限检查");
        try {
            Map<String, String> schema = ctx.getSourceAdapter().getTableSchema(ctx.getSourceTableName());
            boolean ok = schema != null && !schema.isEmpty();
            item.setPassed(ok);
            item.setMessage(ok ? "源表可读，字段数: " + schema.size() : "源表不可读或无权限");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("源表权限检查异常: " + e.getMessage());
        }
        return item;
    }

    private ValidationItem checkTargetTablePermissions(ValidationContext ctx) {
        ValidationItem item = new ValidationItem("target_permissions", "目标表权限检查");
        try {
            Map<String, String> schema = ctx.getTargetAdapter().getTableSchema(ctx.getTargetTableName());
            boolean ok = schema != null && !schema.isEmpty();
            item.setPassed(ok);
            item.setMessage(ok ? "目标表可写，字段数: " + schema.size() : "目标表不可写或无权限");
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("目标表权限检查异常: " + e.getMessage());
        }
        return item;
    }

    private ValidationItem checkTableSchemaCompatibility(ValidationContext ctx) {
        ValidationItem item = new ValidationItem("schema_compatibility", "表结构兼容性检查");
        try {
            Map<String, String> sourceSchema = ctx.getSourceAdapter().getTableSchema(ctx.getSourceTableName());
            Map<String, String> targetSchema = ctx.getTargetAdapter().getTableSchema(ctx.getTargetTableName());

            if (sourceSchema == null || targetSchema == null) {
                item.setPassed(false);
                item.setMessage("无法获取表结构");
                return item;
            }

            List<String> missingFields = new ArrayList<>();
            for (String field : sourceSchema.keySet()) {
                if (!targetSchema.containsKey(field)) {
                    missingFields.add(field);
                }
            }

            if (missingFields.isEmpty()) {
                item.setPassed(true);
                item.setMessage("表结构兼容，源字段 " + sourceSchema.size() + " 个全部匹配目标表");
            } else {
                item.setPassed(false);
                item.setMessage("目标表缺少字段: " + String.join(", ", missingFields));
            }
        } catch (Exception e) {
            item.setPassed(false);
            item.setMessage("表结构兼容性检查异常: " + e.getMessage());
        }
        return item;
    }

    @Data
    public static class ValidationContext {
        private com.datatransfer.migration.adapter.DataSourceAdapter sourceAdapter;
        private com.datatransfer.migration.adapter.DataSourceAdapter targetAdapter;
        private String sourceTableName;
        private String targetTableName;
    }

    @Data
    public static class ValidationResult {
        private boolean valid;
        private String summary;
        private LocalDateTime validatedAt;
        private List<ValidationItem> items;
    }

    @Data
    public static class ValidationItem {
        private String key;
        private String name;
        private boolean passed;
        private String message;

        public ValidationItem() {}
        public ValidationItem(String key, String name) {
            this.key = key;
            this.name = name;
        }
    }
}
