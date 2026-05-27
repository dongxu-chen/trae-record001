package com.datasecurity.masking.rule;

import com.datasecurity.masking.enums.MaskStrategy;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.regex.Pattern;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CustomMaskRule {

    private String id;

    private String name;

    private String description;

    private List<String> columnKeywords;

    private List<String> commentKeywords;

    private String valueRegex;

    private Pattern valuePattern;

    private MaskStrategy defaultStrategy;

    private String maskChar;

    private Integer keepStart;

    private Integer keepEnd;

    private String replaceValue;

    private String hashAlgorithm;

    private String hashSalt;

    private boolean enabled;

    private Integer priority;
}
