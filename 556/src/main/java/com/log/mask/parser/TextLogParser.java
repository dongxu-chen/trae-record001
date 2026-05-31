package com.log.mask.parser;

import com.log.mask.core.RegexMaskEngine;

public class TextLogParser implements LogParser {

    @Override
    public String parseAndMask(String logContent, RegexMaskEngine maskEngine) {
        if (logContent == null || logContent.isEmpty()) {
            return logContent;
        }
        return maskEngine.mask(logContent);
    }

    @Override
    public boolean supportFormat(String format) {
        return "text".equalsIgnoreCase(format) || "plain".equalsIgnoreCase(format);
    }
}
