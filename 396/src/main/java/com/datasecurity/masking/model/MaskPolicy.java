package com.datasecurity.masking.model;

import com.datasecurity.masking.enums.MaskStrategy;
import com.datasecurity.masking.enums.SensitiveType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MaskPolicy {

    private SensitiveType sensitiveType;

    private MaskStrategy strategy;

    private String maskChar;

    private Integer keepStart;

    private Integer keepEnd;

    private String replaceValue;

    private String hashAlgorithm;

    private String hashSalt;
}
