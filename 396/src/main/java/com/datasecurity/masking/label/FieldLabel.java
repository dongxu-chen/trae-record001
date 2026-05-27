package com.datasecurity.masking.label;

import com.datasecurity.masking.enums.SensitiveType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FieldLabel extends DataLabel {

    private String tableName;

    private String columnName;

    private SensitiveType sensitiveType;

    private List<String> downstreamFields;

    public FieldLabel(String tableName, String columnName, SensitiveType sensitiveType, SensitivityLevel level) {
        super(tableName + "." + columnName, columnName, level);
        this.tableName = tableName;
        this.columnName = columnName;
        this.sensitiveType = sensitiveType;
        this.downstreamFields = new ArrayList<>();
        this.setDataType("FIELD");
    }

    public void addDownstreamField(String fieldFullName) {
        if (downstreamFields == null) {
            downstreamFields = new ArrayList<>();
        }
        if (!downstreamFields.contains(fieldFullName)) {
            downstreamFields.add(fieldFullName);
        }
    }
}
