package com.datasecurity.masking.sql;

import com.datasecurity.masking.enums.MaskStrategy;
import com.datasecurity.masking.model.MaskPolicy;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.service.MetadataService;
import lombok.extern.slf4j.Slf4j;
import net.sf.jsqlparser.expression.*;
import net.sf.jsqlparser.expression.operators.conditional.AndExpression;
import net.sf.jsqlparser.expression.operators.relational.EqualsTo;
import net.sf.jsqlparser.expression.operators.relational.ExpressionList;
import net.sf.jsqlparser.expression.operators.relational.InExpression;
import net.sf.jsqlparser.parser.CCJSqlParserUtil;
import net.sf.jsqlparser.schema.Column;
import net.sf.jsqlparser.schema.Table;
import net.sf.jsqlparser.statement.Statement;
import net.sf.jsqlparser.statement.select.*;
import org.apache.commons.codec.digest.DigestUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class SQLRewriteEngine {

    @Autowired
    private MetadataService metadataService;

    @Autowired
    private SQLParserService sqlParserService;

    private static final String MASK_PREFIX = "MASKED_";

    public String rewriteSQL(String originalSQL, String databaseId, boolean needMasking) throws Exception {
        if (!needMasking) {
            log.debug("No masking needed, returning original SQL");
            return originalSQL;
        }

        log.debug("Rewriting SQL for database: {}", databaseId);
        log.debug("Original SQL: {}", originalSQL);

        List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields(databaseId);
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            log.debug("No sensitive fields found, returning original SQL");
            return originalSQL;
        }

        Statement statement = CCJSqlParserUtil.parse(originalSQL);
        if (statement instanceof Select) {
            Select select = (Select) statement;
            return rewriteSelect(select, sensitiveFields);
        }

        return originalSQL;
    }

    private String rewriteSelect(Select select, List<SensitiveField> sensitiveFields) throws Exception {
        SelectBody selectBody = select.getSelectBody();

        if (selectBody instanceof PlainSelect) {
            PlainSelect plainSelect = (PlainSelect) selectBody;
            rewritePlainSelect(plainSelect, sensitiveFields);
        } else if (selectBody instanceof SetOperationList) {
            SetOperationList setOpList = (SetOperationList) selectBody;
            rewriteSetOperationList(setOpList, sensitiveFields);
        }

        return select.toString();
    }

    private void rewritePlainSelect(PlainSelect plainSelect, List<SensitiveField> sensitiveFields) throws Exception {
        Map<String, String> tableAliases = extractTableAliases(plainSelect);
        Set<String> sensitiveColumnNames = sensitiveFields.stream()
                .map(SensitiveField::getColumnName)
                .collect(Collectors.toSet());

        List<SelectItem> selectItems = plainSelect.getSelectItems();
        if (selectItems != null) {
            List<SelectItem> newSelectItems = new ArrayList<>();
            for (SelectItem item : selectItems) {
                if (item instanceof SelectExpressionItem) {
                    SelectExpressionItem exprItem = (SelectExpressionItem) item;
                    Expression expr = exprItem.getExpression();

                    if (expr instanceof Column) {
                        Column column = (Column) expr;
                        String columnName = column.getColumnName();

                        if (sensitiveColumnNames.contains(columnName)) {
                            SensitiveField sensitiveField = findSensitiveField(sensitiveFields, columnName);
                            Expression maskedExpression = createMaskedExpression(column, sensitiveField);

                            SelectExpressionItem newItem = new SelectExpressionItem();
                            newItem.setExpression(maskedExpression);
                            newItem.setAlias(exprItem.getAlias() != null ? exprItem.getAlias() :
                                    new Alias(MASK_PREFIX + columnName, false));
                            newSelectItems.add(newItem);
                            log.debug("Rewrote sensitive column: {}", columnName);
                        } else {
                            newSelectItems.add(item);
                        }
                    } else {
                        newSelectItems.add(item);
                    }
                } else if (item instanceof AllColumns || item instanceof AllTableColumns) {
                    newSelectItems.addAll(expandAllColumns(item, tableAliases, sensitiveFields));
                } else {
                    newSelectItems.add(item);
                }
            }
            plainSelect.setSelectItems(newSelectItems);
        }

        rewriteSubSelects(plainSelect, sensitiveFields);
    }

    private void rewriteSetOperationList(SetOperationList setOpList, List<SensitiveField> sensitiveFields) throws Exception {
        for (SelectBody selectBody : setOpList.getSelects()) {
            if (selectBody instanceof PlainSelect) {
                rewritePlainSelect((PlainSelect) selectBody, sensitiveFields);
            }
        }
    }

    private void rewriteSubSelects(PlainSelect plainSelect, List<SensitiveField> sensitiveFields) throws Exception {
        FromItem fromItem = plainSelect.getFromItem();
        if (fromItem instanceof SubSelect) {
            SubSelect subSelect = (SubSelect) fromItem;
            if (subSelect.getSelectBody() instanceof PlainSelect) {
                rewritePlainSelect((PlainSelect) subSelect.getSelectBody(), sensitiveFields);
            }
        }

        List<Join> joins = plainSelect.getJoins();
        if (joins != null) {
            for (Join join : joins) {
                if (join.getRightItem() instanceof SubSelect) {
                    SubSelect subSelect = (SubSelect) join.getRightItem();
                    if (subSelect.getSelectBody() instanceof PlainSelect) {
                        rewritePlainSelect((PlainSelect) subSelect.getSelectBody(), sensitiveFields);
                    }
                }
            }
        }

        Expression where = plainSelect.getWhere();
        if (where != null) {
            rewriteExpression(where, sensitiveFields);
        }
    }

    private void rewriteExpression(Expression expr, List<SensitiveField> sensitiveFields) throws Exception {
        if (expr instanceof InExpression) {
            InExpression inExpr = (InExpression) expr;
            if (inExpr.getRightExpression() instanceof SubSelect) {
                SubSelect subSelect = (SubSelect) inExpr.getRightExpression();
                if (subSelect.getSelectBody() instanceof PlainSelect) {
                    rewritePlainSelect((PlainSelect) subSelect.getSelectBody(), sensitiveFields);
                }
            }
        } else if (expr instanceof ExistsExpression) {
            ExistsExpression existsExpr = (ExistsExpression) expr;
            if (existsExpr.getRightExpression() instanceof SubSelect) {
                SubSelect subSelect = (SubSelect) existsExpr.getRightExpression();
                if (subSelect.getSelectBody() instanceof PlainSelect) {
                    rewritePlainSelect((PlainSelect) subSelect.getSelectBody(), sensitiveFields);
                }
            }
        } else if (expr instanceof AndExpression) {
            AndExpression and = (AndExpression) expr;
            rewriteExpression(and.getLeftExpression(), sensitiveFields);
            rewriteExpression(and.getRightExpression(), sensitiveFields);
        }
    }

    private Map<String, String> extractTableAliases(PlainSelect plainSelect) {
        Map<String, String> aliases = new HashMap<>();

        FromItem fromItem = plainSelect.getFromItem();
        if (fromItem instanceof Table) {
            Table table = (Table) fromItem;
            String alias = table.getAlias() != null ? table.getAlias().getName() : table.getName();
            aliases.put(alias, table.getName());
        }

        List<Join> joins = plainSelect.getJoins();
        if (joins != null) {
            for (Join join : joins) {
                if (join.getRightItem() instanceof Table) {
                    Table table = (Table) join.getRightItem();
                    String alias = table.getAlias() != null ? table.getAlias().getName() : table.getName();
                    aliases.put(alias, table.getName());
                }
            }
        }

        return aliases;
    }

    private SensitiveField findSensitiveField(List<SensitiveField> sensitiveFields, String columnName) {
        for (SensitiveField field : sensitiveFields) {
            if (field.getColumnName().equalsIgnoreCase(columnName)) {
                return field;
            }
        }
        return null;
    }

    private Expression createMaskedExpression(Column column, SensitiveField sensitiveField) {
        if (sensitiveField == null || sensitiveField.getSensitiveType() == null) {
            return column;
        }

        MaskPolicy defaultPolicy = createDefaultPolicy(sensitiveField);
        String columnName = column.getColumnName();
        String tableName = column.getTable() != null ? column.getTable().getName() + "." : "";

        switch (defaultPolicy.getStrategy()) {
            case MASK:
                return createMaskFunction(column, tableName + columnName, defaultPolicy);
            case HASH:
                return createHashFunction(column, tableName + columnName, defaultPolicy);
            case REPLACE:
                return createReplaceValue(column, defaultPolicy);
            case TRUNCATE:
                return createTruncateFunction(column, tableName + columnName, defaultPolicy);
            default:
                return column;
        }
    }

    private MaskPolicy createDefaultPolicy(SensitiveField sensitiveField) {
        switch (sensitiveField.getSensitiveType()) {
            case ID_CARD:
                return MaskPolicy.builder()
                        .strategy(MaskStrategy.MASK)
                        .maskChar("*")
                        .keepStart(6)
                        .keepEnd(4)
                        .build();
            case PHONE:
                return MaskPolicy.builder()
                        .strategy(MaskStrategy.MASK)
                        .maskChar("*")
                        .keepStart(3)
                        .keepEnd(4)
                        .build();
            case BANK_CARD:
                return MaskPolicy.builder()
                        .strategy(MaskStrategy.MASK)
                        .maskChar("*")
                        .keepStart(4)
                        .keepEnd(4)
                        .build();
            case NAME:
                return MaskPolicy.builder()
                        .strategy(MaskStrategy.MASK)
                        .maskChar("*")
                        .keepStart(1)
                        .keepEnd(0)
                        .build();
            case EMAIL:
                return MaskPolicy.builder()
                        .strategy(MaskStrategy.MASK)
                        .maskChar("*")
                        .keepStart(2)
                        .keepEnd(0)
                        .build();
            default:
                return MaskPolicy.builder()
                        .strategy(MaskStrategy.MASK)
                        .maskChar("*")
                        .keepStart(3)
                        .keepEnd(4)
                        .build();
        }
    }

    private Expression createMaskFunction(Column column, String fullColumnName, MaskPolicy policy) {
        Function function = new Function();
        function.setName("CASE");

        ExpressionList params = new ExpressionList();
        List<Expression> expressions = new ArrayList<>();

        int keepStart = policy.getKeepStart() != null ? policy.getKeepStart() : 0;
        int keepEnd = policy.getKeepEnd() != null ? policy.getKeepEnd() : 0;
        String maskChar = policy.getMaskChar() != null ? policy.getMaskChar() : "*";

        WhenClause whenClause = new WhenClause();
        whenClause.setWhenExpression(new GreaterThanEquals(
                new Function.Builder().withName("LENGTH").withParameters(new ExpressionList(column)).build(),
                new LongValue(String.valueOf(keepStart + keepEnd + 1))
        ));

        Function concatFunc = new Function();
        concatFunc.setName("CONCAT");
        List<Expression> concatParams = new ArrayList<>();

        if (keepStart > 0) {
            Function leftFunc = new Function();
            leftFunc.setName("LEFT");
            leftFunc.setParameters(new ExpressionList(column, new LongValue(String.valueOf(keepStart))));
            concatParams.add(leftFunc);
        }

        Function repeatFunc = new Function();
        repeatFunc.setName("REPEAT");
        repeatFunc.setParameters(new ExpressionList(
                new StringValue("'" + maskChar + "'"),
                new Function.Builder().withName("GREATEST")
                        .withParameters(new ExpressionList(
                                new Function.Builder().withName("LENGTH").withParameters(new ExpressionList(column)).build(),
                                new LongValue(String.valueOf(keepStart + keepEnd))
                        )).build()
        ));
        concatParams.add(repeatFunc);

        if (keepEnd > 0) {
            Function rightFunc = new Function();
            rightFunc.setName("RIGHT");
            rightFunc.setParameters(new ExpressionList(column, new LongValue(String.valueOf(keepEnd))));
            concatParams.add(rightFunc);
        }

        concatFunc.setParameters(new ExpressionList(concatParams));
        whenClause.setThenExpression(concatFunc);

        return column;
    }

    private Expression createHashFunction(Column column, String fullColumnName, MaskPolicy policy) {
        String algorithm = policy.getHashAlgorithm() != null ? policy.getHashAlgorithm() : "MD5";

        if ("MD5".equalsIgnoreCase(algorithm)) {
            Function function = new Function();
            function.setName("MD5");
            function.setParameters(new ExpressionList(column));
            return function;
        } else if ("SHA256".equalsIgnoreCase(algorithm)) {
            Function function = new Function();
            function.setName("SHA2");
            function.setParameters(new ExpressionList(column, new LongValue("256")));
            return function;
        }

        return column;
    }

    private Expression createReplaceValue(Column column, MaskPolicy policy) {
        String replaceValue = policy.getReplaceValue() != null ? policy.getReplaceValue() : "***";
        return new StringValue("'" + replaceValue + "'");
    }

    private Expression createTruncateFunction(Column column, String fullColumnName, MaskPolicy policy) {
        int keepStart = policy.getKeepStart() != null ? policy.getKeepStart() : 6;
        String replaceValue = policy.getReplaceValue() != null ? policy.getReplaceValue() : "...";

        Function function = new Function();
        function.setName("CONCAT");

        Function leftFunc = new Function();
        leftFunc.setName("LEFT");
        leftFunc.setParameters(new ExpressionList(column, new LongValue(String.valueOf(keepStart))));

        function.setParameters(new ExpressionList(leftFunc, new StringValue("'" + replaceValue + "'")));
        return function;
    }

    private List<SelectItem> expandAllColumns(SelectItem item, Map<String, String> tableAliases,
                                              List<SensitiveField> sensitiveFields) {
        List<SelectItem> result = new ArrayList<>();
        Set<String> sensitiveColumnNames = sensitiveFields.stream()
                .map(SensitiveField::getColumnName)
                .collect(Collectors.toSet());

        for (String tableName : tableAliases.values()) {
            for (SensitiveField field : sensitiveFields) {
                if (field.getTableName().equalsIgnoreCase(tableName) ||
                        sensitiveColumnNames.contains(field.getColumnName())) {
                    Column column = new Column();
                    column.setColumnName(field.getColumnName());

                    SelectExpressionItem selectItem = new SelectExpressionItem();
                    selectItem.setExpression(column);
                    selectItem.setAlias(new Alias(MASK_PREFIX + field.getColumnName(), false));
                    result.add(selectItem);
                }
            }
        }

        return result;
    }

    public Object maskValue(Object value, MaskPolicy policy) {
        if (value == null || !(value instanceof String)) {
            return value;
        }

        String strValue = (String) value;
        MaskStrategy strategy = policy.getStrategy();
        if (strategy == null) {
            strategy = MaskStrategy.MASK;
        }

        switch (strategy) {
            case MASK:
                return doMask(strValue, policy);
            case REPLACE:
                return policy.getReplaceValue() != null ? policy.getReplaceValue() : "***";
            case HASH:
                String algorithm = policy.getHashAlgorithm() != null ? policy.getHashAlgorithm() : "MD5";
                String salt = policy.getHashSalt() != null ? policy.getHashSalt() : "";
                if ("MD5".equalsIgnoreCase(algorithm)) {
                    return DigestUtils.md5Hex(strValue + salt);
                } else if ("SHA256".equalsIgnoreCase(algorithm)) {
                    return DigestUtils.sha256Hex(strValue + salt);
                } else if ("SHA512".equalsIgnoreCase(algorithm)) {
                    return DigestUtils.sha512Hex(strValue + salt);
                }
                return DigestUtils.md5Hex(strValue + salt);
            case TRUNCATE:
                int keepStart = policy.getKeepStart() != null ? policy.getKeepStart() : 6;
                String replaceValue = policy.getReplaceValue() != null ? policy.getReplaceValue() : "...";
                if (strValue.length() <= keepStart) {
                    return strValue;
                }
                return strValue.substring(0, keepStart) + replaceValue;
            default:
                return strValue;
        }
    }

    private String doMask(String value, MaskPolicy policy) {
        int keepStart = policy.getKeepStart() != null ? policy.getKeepStart() : 0;
        int keepEnd = policy.getKeepEnd() != null ? policy.getKeepEnd() : 0;
        String maskChar = policy.getMaskChar() != null ? policy.getMaskChar() : "*";

        int length = value.length();
        if (keepStart + keepEnd >= length) {
            return value;
        }

        StringBuilder sb = new StringBuilder();
        sb.append(value, 0, keepStart);
        int maskLength = length - keepStart - keepEnd;
        for (int i = 0; i < maskLength; i++) {
            sb.append(maskChar);
        }
        if (keepEnd > 0) {
            sb.append(value, length - keepEnd, length);
        }
        return sb.toString();
    }
}
