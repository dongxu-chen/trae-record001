package com.datasecurity.masking.model;

import com.datasecurity.masking.enums.SensitiveType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SensitiveField {

    private String tableName;

    private String columnName;

    private SensitiveType sensitiveType;

    private String comment;

    private Integer dataLength;
}
