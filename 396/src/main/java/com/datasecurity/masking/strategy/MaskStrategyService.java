package com.datasecurity.masking.strategy;

import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.model.MaskPolicy;

public interface MaskStrategyService {

    String mask(String value, SensitiveType sensitiveType);

    String mask(String value, MaskPolicy policy);
}
