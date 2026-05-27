package com.datasecurity.masking.sql;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.sf.jsqlparser.expression.*;
import net.sf.jsqlparser.expression.operators.conditional.AndExpression;
import net.sf.jsqlparser.expression.operators.conditional.OrExpression;
import net.sf.jsqlparser.expression.operators.relational.*;
import net.sf.jsqlparser.parser.CCJSqlParserUtil;
import net.sf.jsqlparser.schema.Column;
import net.sf.jsqlparser.schema.Table;
import net.sf.jsqlparser.statement.Statement;
import net.sf.jsqlparser.statement.select.*;
import org.springframework.stereotype.Component;

import java.util.*;

@Slf4j
@Component
public class SQLParserService {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ParsedSQL {
        private String originalSQL;
        private String sqlType;
        private List<TableInfo> tables;
        private List<ColumnInfo> columns;
        private List<SubSelectInfo> subSelects;
        private List<UnionInfo> unions;
        private boolean hasSubQuery;
        private boolean hasUnion;
        private WhereCondition whereCondition;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableInfo {
        private String name;
        private String alias;
        private String schema;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ColumnInfo {
        private String name;
        private String tableAlias;
        private String alias;
        private boolean isAggregate;
        private String expression;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SubSelectInfo {
        private String id;
        private String sql;
        private String location;
        private List<TableInfo> tables;
        private List<ColumnInfo> columns;
        private int startIndex;
        private int endIndex;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UnionInfo {
        private int index;
        private String sql;
        private List<TableInfo> tables;
        private List<ColumnInfo> columns;
        private boolean isAll;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class WhereCondition {
        private String rawCondition;
        private List<String> involvedColumns;
        private List<String> involvedTables;
    }

    private int subQueryCounter = 0;

    public ParsedSQL parse(String sql) throws Exception {
        log.debug("Parsing SQL: {}", sql);
        subQueryCounter = 0;

        Statement statement = CCJSqlParserUtil.parse(sql);

        if (statement instanceof Select) {
            return parseSelect((Select) statement, sql);
        } else {
            throw new IllegalArgumentException("Only SELECT statements are supported for now");
        }
    }

    private ParsedSQL parseSelect(Select select, String originalSQL) {
        ParsedSQL.ParsedSQLBuilder builder = ParsedSQL.builder()
                .originalSQL(originalSQL)
                .sqlType("SELECT")
                .tables(new ArrayList<>())
                .columns(new ArrayList<>())
                .subSelects(new ArrayList<>())
                .unions(new ArrayList<>())
                .hasSubQuery(false)
                .hasUnion(false);

        SelectBody selectBody = select.getSelectBody();

        if (selectBody instanceof PlainSelect) {
            parsePlainSelect((PlainSelect) selectBody, builder, "main");
        } else if (selectBody instanceof SetOperationList) {
            parseSetOperationList((SetOperationList) selectBody, builder);
        }

        return builder.build();
    }

    private void parsePlainSelect(PlainSelect plainSelect, ParsedSQL.ParsedSQLBuilder builder, String context) {
        FromItem fromItem = plainSelect.getFromItem();
        parseFromItem(fromItem, builder, context);

        List<Join> joins = plainSelect.getJoins();
        if (joins != null) {
            for (Join join : joins) {
                parseFromItem(join.getRightItem(), builder, context + "_join");
            }
        }

        List<SelectItem> selectItems = plainSelect.getSelectItems();
        if (selectItems != null) {
            for (SelectItem item : selectItems) {
                parseSelectItem(item, builder, context);
            }
        }

        Expression where = plainSelect.getWhere();
        if (where != null) {
            builder.whereCondition(parseWhereCondition(where));
        }

        if (plainSelect.getGroupBy() != null) {
        }
        if (plainSelect.getHaving() != null) {
        }
        if (plainSelect.getOrderByElements() != null) {
        }
    }

    private void parseSetOperationList(SetOperationList setOpList, ParsedSQL.ParsedSQLBuilder builder) {
        builder.hasUnion(true);

        List<SelectBody> selects = setOpList.getSelects();
        List<SetOperation> operations = setOpList.getOperations();

        for (int i = 0; i < selects.size(); i++) {
            SelectBody selectBody = selects.get(i);
            String context = "union_" + i;

            if (selectBody instanceof PlainSelect) {
                PlainSelect plainSelect = (PlainSelect) selectBody;

                List<TableInfo> tables = new ArrayList<>();
                List<ColumnInfo> columns = new ArrayList<>();

                ParsedSQL.ParsedSQLBuilder tempBuilder = ParsedSQL.builder()
                        .tables(tables)
                        .columns(columns)
                        .subSelects(new ArrayList<>());

                parsePlainSelect(plainSelect, tempBuilder, context);

                boolean isAll = false;
                if (i > 0 && i - 1 < operations.size()) {
                    SetOperation op = operations.get(i - 1);
                    isAll = op instanceof UnionOp && ((UnionOp) op).isAll();
                }

                builder.unions.get().add(UnionInfo.builder()
                        .index(i)
                        .sql(plainSelect.toString())
                        .tables(tables)
                        .columns(columns)
                        .isAll(isAll)
                        .build());
            }
        }
    }

    private void parseFromItem(FromItem fromItem, ParsedSQL.ParsedSQLBuilder builder, String context) {
        if (fromItem instanceof Table) {
            Table table = (Table) fromItem;
            TableInfo tableInfo = TableInfo.builder()
                    .name(table.getName())
                    .alias(table.getAlias() != null ? table.getAlias().getName() : null)
                    .schema(table.getSchemaName())
                    .build();
            builder.tables.get().add(tableInfo);
            log.debug("Found table: {} (alias: {})", tableInfo.getName(), tableInfo.getAlias());

        } else if (fromItem instanceof SubSelect) {
            builder.hasSubQuery(true);
            SubSelect subSelect = (SubSelect) fromItem;

            ParsedSQL.ParsedSQLBuilder subBuilder = ParsedSQL.builder()
                    .tables(new ArrayList<>())
                    .columns(new ArrayList<>())
                    .subSelects(new ArrayList<>());

            if (subSelect.getSelectBody() instanceof PlainSelect) {
                parsePlainSelect((PlainSelect) subSelect.getSelectBody(), subBuilder, context + "_sub");
            }

            String alias = subSelect.getAlias() != null ? subSelect.getAlias().getName() : null;

            SubSelectInfo subSelectInfo = SubSelectInfo.builder()
                    .id("SUB_" + (++subQueryCounter))
                    .sql(subSelect.toString())
                    .location("FROM")
                    .tables(subBuilder.build().getTables())
                    .columns(subBuilder.build().getColumns())
                    .build();
            builder.subSelects.get().add(subSelectInfo);

            if (alias != null) {
                builder.tables.get().add(TableInfo.builder()
                        .name("SUBQUERY_" + subSelectInfo.getId())
                        .alias(alias)
                        .build());
            }

            log.debug("Found subquery in FROM: {}", subSelectInfo.getId());
        }
    }

    private void parseSelectItem(SelectItem item, ParsedSQL.ParsedSQLBuilder builder, String context) {
        if (item instanceof SelectExpressionItem) {
            SelectExpressionItem exprItem = (SelectExpressionItem) item;
            Expression expr = exprItem.getExpression();

            ColumnInfo columnInfo = ColumnInfo.builder()
                    .alias(exprItem.getAlias() != null ? exprItem.getAlias().getName() : null)
                    .expression(expr.toString())
                    .isAggregate(false)
                    .build();

            if (expr instanceof Column) {
                Column column = (Column) expr;
                columnInfo.setName(column.getColumnName());
                if (column.getTable() != null) {
                    columnInfo.setTableAlias(column.getTable().getName());
                }
            } else if (expr instanceof Function) {
                columnInfo.setAggregate(true);
                columnInfo.setName(((Function) expr).getName());
            }

            builder.columns.get().add(columnInfo);
            log.debug("Found column: {} (tableAlias: {}, alias: {})",
                    columnInfo.getName(), columnInfo.getTableAlias(), columnInfo.getAlias());
        }
    }

    private WhereCondition parseWhereCondition(Expression where) {
        WhereCondition condition = WhereCondition.builder()
                .rawCondition(where.toString())
                .involvedColumns(new ArrayList<>())
                .involvedTables(new ArrayList<>())
                .build();

        extractColumnsFromExpression(where, condition);

        return condition;
    }

    private void extractColumnsFromExpression(Expression expr, WhereCondition condition) {
        if (expr == null) {
            return;
        }

        if (expr instanceof Column) {
            Column column = (Column) expr;
            condition.getInvolvedColumns().add(column.getColumnName());
            if (column.getTable() != null) {
                condition.getInvolvedTables().add(column.getTable().getName());
            }
        } else if (expr instanceof AndExpression) {
            AndExpression and = (AndExpression) expr;
            extractColumnsFromExpression(and.getLeftExpression(), condition);
            extractColumnsFromExpression(and.getRightExpression(), condition);
        } else if (expr instanceof OrExpression) {
            OrExpression or = (OrExpression) expr;
            extractColumnsFromExpression(or.getLeftExpression(), condition);
            extractColumnsFromExpression(or.getRightExpression(), condition);
        } else if (expr instanceof ComparisonOperator) {
            ComparisonOperator comp = (ComparisonOperator) expr;
            extractColumnsFromExpression(comp.getLeftExpression(), condition);
            extractColumnsFromExpression(comp.getRightExpression(), condition);
        } else if (expr instanceof InExpression) {
            InExpression in = (InExpression) expr;
            extractColumnsFromExpression(in.getLeftExpression(), condition);
            if (in.getRightExpression() instanceof SubSelect) {
                SubSelect subSelect = (SubSelect) in.getRightExpression();
                log.debug("Found subquery in IN clause");
            }
        } else if (expr instanceof Between) {
            Between between = (Between) expr;
            extractColumnsFromExpression(between.getLeftExpression(), condition);
        } else if (expr instanceof LikeExpression) {
            LikeExpression like = (LikeExpression) expr;
            extractColumnsFromExpression(like.getLeftExpression(), condition);
        } else if (expr instanceof IsNullExpression) {
            IsNullExpression isNull = (IsNullExpression) expr;
            extractColumnsFromExpression(isNull.getLeftExpression(), condition);
        } else if (expr instanceof ExistsExpression) {
            ExistsExpression exists = (ExistsExpression) expr;
            if (exists.getRightExpression() instanceof SubSelect) {
                log.debug("Found subquery in EXISTS clause");
            }
        }
    }

    public List<String> extractAllTableNames(ParsedSQL parsedSQL) {
        Set<String> allTables = new HashSet<>();

        if (parsedSQL.getTables() != null) {
            for (TableInfo table : parsedSQL.getTables()) {
                allTables.add(table.getName());
            }
        }

        if (parsedSQL.getSubSelects() != null) {
            for (SubSelectInfo subSelect : parsedSQL.getSubSelects()) {
                if (subSelect.getTables() != null) {
                    for (TableInfo table : subSelect.getTables()) {
                        allTables.add(table.getName());
                    }
                }
            }
        }

        if (parsedSQL.getUnions() != null) {
            for (UnionInfo union : parsedSQL.getUnions()) {
                if (union.getTables() != null) {
                    for (TableInfo table : union.getTables()) {
                        allTables.add(table.getName());
                    }
                }
            }
        }

        return new ArrayList<>(allTables);
    }

    public List<String> extractAllColumnNames(ParsedSQL parsedSQL) {
        Set<String> allColumns = new HashSet<>();

        if (parsedSQL.getColumns() != null) {
            for (ColumnInfo column : parsedSQL.getColumns()) {
                if (!column.isAggregate()) {
                    allColumns.add(column.getName());
                }
            }
        }

        if (parsedSQL.getSubSelects() != null) {
            for (SubSelectInfo subSelect : parsedSQL.getSubSelects()) {
                if (subSelect.getColumns() != null) {
                    for (ColumnInfo column : subSelect.getColumns()) {
                        if (!column.isAggregate()) {
                            allColumns.add(column.getName());
                        }
                    }
                }
            }
        }

        if (parsedSQL.getUnions() != null) {
            for (UnionInfo union : parsedSQL.getUnions()) {
                if (union.getColumns() != null) {
                    for (ColumnInfo column : union.getColumns()) {
                        if (!column.isAggregate()) {
                            allColumns.add(column.getName());
                        }
                    }
                }
            }
        }

        if (parsedSQL.getWhereCondition() != null && parsedSQL.getWhereCondition().getInvolvedColumns() != null) {
            allColumns.addAll(parsedSQL.getWhereCondition().getInvolvedColumns());
        }

        return new ArrayList<>(allColumns);
    }

    public boolean isWriteOperation(String sql) {
        String trimmed = sql.trim().toUpperCase();
        return trimmed.startsWith("INSERT") ||
                trimmed.startsWith("UPDATE") ||
                trimmed.startsWith("DELETE") ||
                trimmed.startsWith("CREATE") ||
                trimmed.startsWith("ALTER") ||
                trimmed.startsWith("DROP");
    }
}
