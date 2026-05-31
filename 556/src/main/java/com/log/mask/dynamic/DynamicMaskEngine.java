package com.log.mask.dynamic;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class DynamicMaskEngine {
    private final Map<String, DataTypeMaskConfig> dataTypeConfigs = new HashMap<>();

    public DynamicMaskEngine() {
        loadDefaultConfigs();
    }

    private void loadDefaultConfigs() {
        addConfig(new DataTypeMaskConfig("phone", "1[3-9]\\d{9",
            "****",        // COMPLETE: 全部遮盖
            "$1****$3",    // PARTIAL: 保留前3后4
            "$0"           // FULL: 不脱敏
        ));

        addConfig(new DataTypeMaskConfig("idCard", "\\d{6}(19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]",
            "****************",
            "$1************",
            "$0"
        ));

        addConfig(new DataTypeMaskConfig("password", "(?i)(password|pwd|passwd)[=:]['\"]?([^'\"\\s,;]+)['\"]?",
            "******",
            "******",
            "$0"
        ));

        addConfig(new DataTypeMaskConfig("email", "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
            "****@****.***",
            "***@$2",
            "$0"
        ).withGroupPattern("([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})"));

        addConfig(new DataTypeMaskConfig("bankCard", "\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}",
            "**** **** **** ****",
            "$1********$2",
            "$0"
        ).withGroupPattern("\\b(\\d{4})\\d{8,12}(\\d{4})\\b"));
    }

    public void addConfig(DataTypeMaskConfig config) {
        dataTypeConfigs.put(config.getDataType(), config);
    }

    public String mask(String input, AccessContext context) {
        if (input == null || input.isEmpty()) {
            return input;
        }
        if (context == null) {
            context = AccessContext.anonymous();
        }

        String result = input;
        for (Map.Entry<String, DataTypeMaskConfig> entry : dataTypeConfigs.entrySet()) {
            String dataType = entry.getKey();
            DataTypeMaskConfig config = entry.getValue();
            MaskPolicy policy = context.resolvePolicy(dataType);

            if (policy == MaskPolicy.FULL) {
                continue;
            }

            String replacement = config.getReplacement(policy);
            String regex = config.getGroupPattern() != null ? config.getGroupPattern() : config.getRegex();

            try {
                Pattern pattern = Pattern.compile(regex, Pattern.CASE_INSENSITIVE);
                Matcher matcher = pattern.matcher(result);
                StringBuffer sb = new StringBuffer();

                while (matcher.find()) {
                    String resolved;
                    if (policy == MaskPolicy.COMPLETE) {
                        resolved = config.getCompleteReplacement();
                    } else if (policy == MaskPolicy.PARTIAL) {
                        resolved = resolveGroupReplacement(matcher, config.getPartialReplacement());
                    } else {
                        continue;
                    }
                    matcher.appendReplacement(sb, Matcher.quoteReplacement(resolved));
                }
                matcher.appendTail(sb);
                result = sb.toString();
            } catch (Exception e) {
                // skip on error
            }
        }
        return result;
    }

    private String resolveGroupReplacement(Matcher matcher, String replacement) {
        String result = replacement;
        for (int i = 0; i <= matcher.groupCount(); i++) {
            String groupValue = matcher.group(i);
            if (groupValue != null && result.contains("$" + i)) {
                result = result.replace("$" + i, groupValue);
            }
        }
        if (result.contains("$0")) {
            result = result.replace("$0", matcher.group());
        }
        return result;
    }

    public DataTypeMaskConfig getConfig(String dataType) {
        return dataTypeConfigs.get(dataType);
    }

    public Collection<DataTypeMaskConfig> getAllConfigs() {
        return dataTypeConfigs.values();
    }
}
