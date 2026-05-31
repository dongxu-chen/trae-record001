package com.log.mask.parser;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

public class LogParserFactory {
    private static final List<LogParser> PARSERS = new ArrayList<>();

    static {
        PARSERS.add(new TextLogParser());
        PARSERS.add(new JsonLogParser());
        PARSERS.add(new XmlLogParser());
    }

    public static LogParser getParser(String format) {
        Optional<LogParser> parser = PARSERS.stream()
                .filter(p -> p.supportFormat(format))
                .findFirst();
        return parser.orElseGet(TextLogParser::new);
    }

    public static void registerParser(LogParser parser) {
        PARSERS.add(parser);
    }

    public static List<LogParser> getParsers() {
        return new ArrayList<>(PARSERS);
    }
}
