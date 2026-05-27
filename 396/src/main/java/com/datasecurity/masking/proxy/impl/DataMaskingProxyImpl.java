package com.datasecurity.masking.proxy.impl;

import com.datasecurity.masking.access.PermissionService;
import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.access.UserContextHolder;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.proxy.DataMaskingProxy;
import com.datasecurity.masking.service.MetadataService;
import com.datasecurity.masking.strategy.MaskStrategyService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class DataMaskingProxyImpl implements DataMaskingProxy {

    @Autowired
    private MetadataService metadataService;

    @Autowired
    private MaskStrategyService maskStrategyService;

    @Autowired
    private PermissionService permissionService;

    @Override
    public ResultSet executeQuery(String sql, ResultSet originalResultSet) {
        return originalResultSet;
    }

    @Override
    public List<Map<String, Object>> maskResult(List<Map<String, Object>> originalResult, String databaseId) {
        if (originalResult == null || originalResult.isEmpty()) {
            return originalResult;
        }

        UserContext user = UserContextHolder.get();
        if (!permissionService.needMasking(user)) {
            log.debug("User has permission to view sensitive data, skipping masking");
            return originalResult;
        }

        List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields(databaseId);
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            log.debug("No sensitive fields found for database: {}", databaseId);
            return originalResult;
        }

        List<Map<String, Object>> maskedResult = new ArrayList<>();
        for (Map<String, Object> row : originalResult) {
            maskedResult.add(maskRowInternal(row, sensitiveFields, user));
        }

        return maskedResult;
    }

    @Override
    public Map<String, Object> maskRow(Map<String, Object> originalRow, String databaseId) {
        if (originalRow == null || originalRow.isEmpty()) {
            return originalRow;
        }

        UserContext user = UserContextHolder.get();
        if (!permissionService.needMasking(user)) {
            return originalRow;
        }

        List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields(databaseId);
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            return originalRow;
        }

        return maskRowInternal(originalRow, sensitiveFields, user);
    }

    private Map<String, Object> maskRowInternal(Map<String, Object> row,
                                                List<SensitiveField> sensitiveFields,
                                                UserContext user) {
        Map<String, Object> maskedRow = new HashMap<>(row);

        for (SensitiveField field : sensitiveFields) {
            String columnName = field.getColumnName();
            if (maskedRow.containsKey(columnName)) {
                Object value = maskedRow.get(columnName);
                if (value instanceof String) {
                    if (!permissionService.canViewSensitiveType(user, field.getSensitiveType())) {
                        String maskedValue = maskStrategyService.mask((String) value, field.getSensitiveType());
                        maskedRow.put(columnName, maskedValue);
                        log.debug("Masked field: {}, type: {}, original: {}, masked: {}",
                                columnName, field.getSensitiveType(), value, maskedValue);
                    }
                }
            }
        }

        return maskedRow;
    }
}
