package com.logplatform.parser;

import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import lombok.extern.slf4j.Slf4j;
import org.antlr.v4.runtime.CharStreams;
import org.antlr.v4.runtime.CommonTokenStream;
import org.antlr.v4.runtime.tree.ParseTree;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class QueryParserService {

    public Query parseQuery(String queryString) {
        if (queryString == null || queryString.trim().isEmpty()) {
            return null;
        }

        try {
            LogQueryLexer lexer = new LogQueryLexer(CharStreams.fromString(queryString));
            CommonTokenStream tokens = new CommonTokenStream(lexer);
            LogQueryParser parser = new LogQueryParser(tokens);

            parser.removeErrorListeners();
            parser.addErrorListener(new LogQueryErrorListener());

            ParseTree tree = parser.parse();
            IteratorQueryBuilder builder = new IteratorQueryBuilder();

            return builder.build(tree);
        } catch (Exception e) {
            log.error("Failed to parse query: {}", queryString, e);
            throw new IllegalArgumentException("查询语法错误: " + e.getMessage(), e);
        }
    }
}
