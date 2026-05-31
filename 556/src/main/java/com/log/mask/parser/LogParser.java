package com.log.mask.parser;

public interface LogParser {
    String parseAndMask(String logContent, com.log.mask.core.RegexMaskEngine maskEngine);
    boolean supportFormat(String format);
}
