package com.datasecurity.masking.strategy.impl;

import com.datasecurity.masking.enums.MaskStrategy;
import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.model.MaskPolicy;
import com.datasecurity.masking.strategy.MaskStrategyService;
import org.apache.commons.codec.digest.DigestUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.HashMap;
import java.util.Map;

@Service
public class MaskStrategyServiceImpl implements MaskStrategyService {

    private Map<SensitiveType, MaskPolicy> defaultPolicies;

    @PostConstruct
    public void init() {
        defaultPolicies = new HashMap<>();

        defaultPolicies.put(SensitiveType.ID_CARD, MaskPolicy.builder()
                .sensitiveType(SensitiveType.ID_CARD)
                .strategy(MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(6)
                .keepEnd(4)
                .build());

        defaultPolicies.put(SensitiveType.PHONE, MaskPolicy.builder()
                .sensitiveType(SensitiveType.PHONE)
                .strategy(MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(3)
                .keepEnd(4)
                .build());

        defaultPolicies.put(SensitiveType.BANK_CARD, MaskPolicy.builder()
                .sensitiveType(SensitiveType.BANK_CARD)
                .strategy(MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(4)
                .keepEnd(4)
                .build());

        defaultPolicies.put(SensitiveType.NAME, MaskPolicy.builder()
                .sensitiveType(SensitiveType.NAME)
                .strategy(MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(1)
                .keepEnd(0)
                .build());

        defaultPolicies.put(SensitiveType.EMAIL, MaskPolicy.builder()
                .sensitiveType(SensitiveType.EMAIL)
                .strategy(MaskStrategy.MASK)
                .maskChar("*")
                .keepStart(2)
                .keepEnd(0)
                .build());

        defaultPolicies.put(SensitiveType.ADDRESS, MaskPolicy.builder()
                .sensitiveType(SensitiveType.ADDRESS)
                .strategy(MaskStrategy.TRUNCATE)
                .keepStart(6)
                .replaceValue("***")
                .build());
    }

    @Override
    public String mask(String value, SensitiveType sensitiveType) {
        if (StringUtils.isBlank(value)) {
            return value;
        }
        MaskPolicy policy = defaultPolicies.getOrDefault(sensitiveType,
                MaskPolicy.builder().strategy(MaskStrategy.NONE).build());
        return mask(value, policy);
    }

    @Override
    public String mask(String value, MaskPolicy policy) {
        if (StringUtils.isBlank(value) || policy == null) {
            return value;
        }

        MaskStrategy strategy = policy.getStrategy();
        if (strategy == null) {
            strategy = MaskStrategy.NONE;
        }

        switch (strategy) {
            case MASK:
                return doMask(value, policy);
            case REPLACE:
                return doReplace(value, policy);
            case HASH:
                return doHash(value, policy);
            case TRUNCATE:
                return doTruncate(value, policy);
            case NONE:
            default:
                return value;
        }
    }

    private String doMask(String value, MaskPolicy policy) {
        int keepStart = policy.getKeepStart() != null ? policy.getKeepStart() : 0;
        int keepEnd = policy.getKeepEnd() != null ? policy.getKeepEnd() : 0;
        String maskChar = StringUtils.defaultIfBlank(policy.getMaskChar(), "*");

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

    private String doReplace(String value, MaskPolicy policy) {
        return StringUtils.defaultIfBlank(policy.getReplaceValue(), "***");
    }

    private String doHash(String value, MaskPolicy policy) {
        String algorithm = StringUtils.defaultIfBlank(policy.getHashAlgorithm(), "MD5");
        String salt = policy.getHashSalt();
        String toHash = salt != null ? value + salt : value;

        switch (algorithm.toUpperCase()) {
            case "SHA256":
                return DigestUtils.sha256Hex(toHash);
            case "SHA512":
                return DigestUtils.sha512Hex(toHash);
            case "MD5":
            default:
                return DigestUtils.md5Hex(toHash);
        }
    }

    private String doTruncate(String value, MaskPolicy policy) {
        int keepStart = policy.getKeepStart() != null ? policy.getKeepStart() : 0;
        String replaceValue = StringUtils.defaultIfBlank(policy.getReplaceValue(), "...");

        if (value.length() <= keepStart) {
            return value;
        }
        return value.substring(0, keepStart) + replaceValue;
    }
}
