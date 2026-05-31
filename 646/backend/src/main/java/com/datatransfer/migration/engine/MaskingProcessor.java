package com.datatransfer.migration.engine;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MaskingProcessor implements DataProcessor {
    private final Map<String, MaskingStrategy> strategies = new HashMap<>();
    private final List<Map<String, String>> maskingRules;

    public MaskingProcessor(List<Map<String, String>> maskingRules) {
        this.maskingRules = maskingRules;
        strategies.put("phone", new PhoneMaskingStrategy());
        strategies.put("email", new EmailMaskingStrategy());
        strategies.put("idcard", new IdCardMaskingStrategy());
        strategies.put("full", new FullMaskingStrategy());
    }

    @Override
    public void process(Record record) throws Exception {
        if (maskingRules == null || maskingRules.isEmpty()) return;
        applyMasking(record);
    }

    @Override
    public void processBatch(List<Record> records) throws Exception {
        if (maskingRules == null || maskingRules.isEmpty()) return;
        for (Record record : records) {
            applyMasking(record);
        }
    }

    private void applyMasking(Record record) {
        for (Map<String, String> rule : maskingRules) {
            String fieldName = rule.get("fieldName");
            String strategyType = rule.get("strategyType");
            if (record.containsKey(fieldName)) {
                Object value = record.get(fieldName);
                if (value instanceof String) {
                    MaskingStrategy strategy = strategies.get(strategyType);
                    if (strategy != null) {
                        record.set(fieldName, strategy.mask((String) value));
                    }
                }
            }
        }
    }
}
