package com.payment.reconciliation.parser;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class ParserFactory {

    @Autowired
    private List<ReconciliationParser> parsers;

    public ReconciliationParser getParser(String fileType) {
        for (ReconciliationParser parser : parsers) {
            if (parser.support(fileType)) {
                return parser;
            }
        }
        throw new IllegalArgumentException("不支持的文件类型: " + fileType);
    }
}
