package com.datasync.canal;

import com.datasync.model.DDLEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class DDLParser {

    private static final Pattern TABLE_NAME_PATTERN = Pattern.compile(
            "(?:CREATE|ALTER|DROP|TRUNCATE|RENAME)\\s+(?:TABLE|INDEX)\\s+`?(\\w+)`?\\.`?(\\w+)`?",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern ALTER_TABLE_PATTERN = Pattern.compile(
            "ALTER\\s+TABLE\\s+`?(\\w+)`?\\.`?(\\w+)`?\\s+(.*)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern ADD_COLUMN_PATTERN = Pattern.compile(
            "ADD\\s+(?:COLUMN\\s+)?`?(\\w+)`?\\s+(\\w+(?:\\(\\d+(?:,\\s*\\d+)?\\))?)\\s*(.*?)(?:,|$)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern DROP_COLUMN_PATTERN = Pattern.compile(
            "DROP\\s+(?:COLUMN\\s+)?`?(\\w+)`?",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern MODIFY_COLUMN_PATTERN = Pattern.compile(
            "MODIFY\\s+(?:COLUMN\\s+)?`?(\\w+)`?\\s+(\\w+(?:\\(\\d+(?:,\\s*\\d+)?\\))?)\\s*(.*?)(?:,|$)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern CHANGE_COLUMN_PATTERN = Pattern.compile(
            "CHANGE\\s+(?:COLUMN\\s+)?`?(\\w+)`?\\s+`?(\\w+)`?\\s+(\\w+(?:\\(\\d+(?:,\\s*\\d+)?\\))?)\\s*(.*?)(?:,|$)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern DATA_TYPE_PATTERN = Pattern.compile(
            "(\\w+)(?:\\((\\d+)(?:,\\s*(\\d+))?\\))?");

    private static final Pattern NULLABLE_PATTERN = Pattern.compile("\\bNOT\\s+NULL\\b", Pattern.CASE_INSENSITIVE);

    private static final Pattern DEFAULT_PATTERN = Pattern.compile("DEFAULT\\s+['\"]?([^'\"\\s,]+)['\"]?", Pattern.CASE_INSENSITIVE);

    private static final Pattern COMMENT_PATTERN = Pattern.compile("COMMENT\\s+['\"]([^'\"]+)['\"]", Pattern.CASE_INSENSITIVE);

    private static final Pattern AFTER_PATTERN = Pattern.compile("AFTER\\s+`?(\\w+)`?", Pattern.CASE_INSENSITIVE);

    public DDLEvent parse(String database, String table, String sql) {
        DDLEvent.DDLEventBuilder builder = DDLEvent.builder()
                .database(database)
                .table(table)
                .sql(sql);

        String sqlUpper = sql.toUpperCase().trim();

        if (sqlUpper.startsWith("CREATE TABLE")) {
            builder.ddlType(DDLEvent.DDLType.CREATE_TABLE);
            builder.columnChanges(parseCreateTableColumns(sql));
        } else if (sqlUpper.startsWith("ALTER TABLE")) {
            builder.ddlType(DDLEvent.DDLType.ALTER_TABLE);
            builder.columnChanges(parseAlterTable(sql));
        } else if (sqlUpper.startsWith("DROP TABLE")) {
            builder.ddlType(DDLEvent.DDLType.DROP_TABLE);
        } else if (sqlUpper.startsWith("TRUNCATE")) {
            builder.ddlType(DDLEvent.DDLType.TRUNCATE_TABLE);
        } else if (sqlUpper.startsWith("RENAME TABLE")) {
            builder.ddlType(DDLEvent.DDLType.RENAME_TABLE);
        } else if (sqlUpper.startsWith("CREATE INDEX")) {
            builder.ddlType(DDLEvent.DDLType.CREATE_INDEX);
        } else if (sqlUpper.startsWith("DROP INDEX")) {
            builder.ddlType(DDLEvent.DDLType.DROP_INDEX);
        } else {
            builder.ddlType(DDLEvent.DDLType.UNKNOWN);
        }

        return builder.build();
    }

    private List<DDLEvent.ColumnChange> parseCreateTableColumns(String sql) {
        List<DDLEvent.ColumnChange> changes = new ArrayList<>();

        try {
            int startParen = sql.indexOf('(');
            int endParen = findMatchingParen(sql, startParen);

            if (startParen > 0 && endParen > startParen) {
                String columnsPart = sql.substring(startParen + 1, endParen);
                String[] columnDefs = splitTopLevelCommas(columnsPart);

                for (String columnDef : columnDefs) {
                    String trimmed = columnDef.trim();
                    if (isColumnDefinition(trimmed)) {
                        DDLEvent.ColumnChange change = parseColumnDefinition(trimmed);
                        if (change != null) {
                            change.setChangeType(DDLEvent.ColumnChange.ChangeType.ADD);
                            changes.add(change);
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.warn("Failed to parse CREATE TABLE columns: {}", e.getMessage());
        }

        return changes;
    }

    private List<DDLEvent.ColumnChange> parseAlterTable(String sql) {
        List<DDLEvent.ColumnChange> changes = new ArrayList<>();

        try {
            Matcher alterMatcher = ALTER_TABLE_PATTERN.matcher(sql);
            if (alterMatcher.find()) {
                String alterBody = alterMatcher.group(3);
                String[] actions = splitTopLevelCommas(alterBody);

                for (String action : actions) {
                    String trimmed = action.trim();
                    String actionUpper = trimmed.toUpperCase();

                    if (actionUpper.startsWith("ADD")) {
                        Matcher addMatcher = ADD_COLUMN_PATTERN.matcher(trimmed);
                        if (addMatcher.find()) {
                            DDLEvent.ColumnChange change = parseColumnDefinition(trimmed);
                            change.setChangeType(DDLEvent.ColumnChange.ChangeType.ADD);
                            changes.add(change);
                        }
                    } else if (actionUpper.startsWith("DROP")) {
                        Matcher dropMatcher = DROP_COLUMN_PATTERN.matcher(trimmed);
                        if (dropMatcher.find()) {
                            DDLEvent.ColumnChange change = new DDLEvent.ColumnChange();
                            change.setChangeType(DDLEvent.ColumnChange.ChangeType.DROP);
                            change.setColumnName(dropMatcher.group(1));
                            changes.add(change);
                        }
                    } else if (actionUpper.startsWith("MODIFY")) {
                        Matcher modifyMatcher = MODIFY_COLUMN_PATTERN.matcher(trimmed);
                        if (modifyMatcher.find()) {
                            DDLEvent.ColumnChange change = parseColumnDefinition(trimmed);
                            change.setChangeType(DDLEvent.ColumnChange.ChangeType.MODIFY);
                            changes.add(change);
                        }
                    } else if (actionUpper.startsWith("CHANGE")) {
                        Matcher changeMatcher = CHANGE_COLUMN_PATTERN.matcher(trimmed);
                        if (changeMatcher.find()) {
                            DDLEvent.ColumnChange change = new DDLEvent.ColumnChange();
                            change.setChangeType(DDLEvent.ColumnChange.ChangeType.CHANGE);
                            change.setOldColumnName(changeMatcher.group(1));
                            change.setColumnName(changeMatcher.group(2));
                            change.setDataType(changeMatcher.group(3));
                            parseColumnAttributes(change, changeMatcher.group(4));
                            changes.add(change);
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.warn("Failed to parse ALTER TABLE: {}", e.getMessage());
        }

        return changes;
    }

    private DDLEvent.ColumnChange parseColumnDefinition(String columnDef) {
        DDLEvent.ColumnChange change = new DDLEvent.ColumnChange();

        try {
            String[] parts = columnDef.trim().split("\\s+", 3);
            if (parts.length < 2) {
                return null;
            }

            String columnName = parts[0].replace("`", "").replace("`", "");
            change.setColumnName(columnName);

            Matcher typeMatcher = DATA_TYPE_PATTERN.matcher(parts[1]);
            if (typeMatcher.find()) {
                change.setDataType(typeMatcher.group(1));
                if (typeMatcher.group(2) != null) {
                    change.setLength(Integer.parseInt(typeMatcher.group(2)));
                }
                if (typeMatcher.group(3) != null) {
                    change.setScale(Integer.parseInt(typeMatcher.group(3)));
                }
            }

            parseColumnAttributes(change, parts.length > 2 ? parts[2] : "");

        } catch (Exception e) {
            log.warn("Failed to parse column definition: {}", columnDef);
        }

        return change;
    }

    private void parseColumnAttributes(DDLEvent.ColumnChange change, String attrs) {
        if (attrs == null || attrs.isEmpty()) {
            return;
        }

        Matcher nullableMatcher = NULLABLE_PATTERN.matcher(attrs);
        change.setNullable(!nullableMatcher.find());

        Matcher defaultMatcher = DEFAULT_PATTERN.matcher(attrs);
        if (defaultMatcher.find()) {
            change.setDefaultValue(defaultMatcher.group(1));
        }

        Matcher commentMatcher = COMMENT_PATTERN.matcher(attrs);
        if (commentMatcher.find()) {
            change.setComment(commentMatcher.group(1));
        }

        Matcher afterMatcher = AFTER_PATTERN.matcher(attrs);
        if (afterMatcher.find()) {
            change.setAfterColumn(afterMatcher.group(1));
        }
    }

    private int findMatchingParen(String sql, int start) {
        int depth = 0;
        for (int i = start; i < sql.length(); i++) {
            char c = sql.charAt(i);
            if (c == '(') depth++;
            else if (c == ')') {
                depth--;
                if (depth == 0) return i;
            }
        }
        return -1;
    }

    private String[] splitTopLevelCommas(String str) {
        List<String> parts = new ArrayList<>();
        int depth = 0;
        StringBuilder current = new StringBuilder();

        for (int i = 0; i < str.length(); i++) {
            char c = str.charAt(i);
            if (c == '(') depth++;
            else if (c == ')') depth--;
            else if (c == ',' && depth == 0) {
                parts.add(current.toString().trim());
                current.setLength(0);
                continue;
            }
            current.append(c);
        }
        if (current.length() > 0) {
            parts.add(current.toString().trim());
        }
        return parts.toArray(new String[0]);
    }

    private boolean isColumnDefinition(String def) {
        String upper = def.toUpperCase().trim();
        return !upper.startsWith("PRIMARY") && !upper.startsWith("UNIQUE")
                && !upper.startsWith("INDEX") && !upper.startsWith("KEY")
                && !upper.startsWith("CONSTRAINT") && !upper.startsWith("FOREIGN");
    }

    public boolean isDDL(String sql) {
        if (sql == null || sql.isEmpty()) {
            return false;
        }
        String trimmed = sql.toUpperCase().trim();
        return trimmed.startsWith("CREATE") || trimmed.startsWith("ALTER") ||
                trimmed.startsWith("DROP") || trimmed.startsWith("TRUNCATE") ||
                trimmed.startsWith("RENAME");
    }

    public String extractDatabase(String sql) {
        Matcher matcher = TABLE_NAME_PATTERN.matcher(sql);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return null;
    }

    public String extractTable(String sql) {
        Matcher matcher = TABLE_NAME_PATTERN.matcher(sql);
        if (matcher.find()) {
            return matcher.group(2);
        }
        return null;
    }
}
