package com.logplatform;

import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import com.logplatform.parser.IteratorQueryBuilder;
import com.logplatform.parser.LogQueryLexer;
import com.logplatform.parser.LogQueryParser;
import org.antlr.v4.runtime.CharStreams;
import org.antlr.v4.runtime.CommonTokenStream;
import org.antlr.v4.runtime.tree.ParseTree;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class IteratorQueryBuilderTest {

    private Query parse(String queryString) {
        LogQueryLexer lexer = new LogQueryLexer(CharStreams.fromString(queryString));
        CommonTokenStream tokens = new CommonTokenStream(lexer);
        LogQueryParser parser = new LogQueryParser(tokens);
        parser.removeErrorListeners();
        ParseTree tree = parser.parse();

        IteratorQueryBuilder builder = new IteratorQueryBuilder();
        return builder.build(tree);
    }

    @Test
    void testSimpleTermQuery() {
        Query query = parse("error");
        assertNotNull(query);
        assertTrue(query.isMultiMatch());
    }

    @Test
    void testAndQuery() {
        Query query = parse("error AND timeout");
        assertNotNull(query);
        assertTrue(query.isBool());
        assertEquals(2, query.bool().must().size());
    }

    @Test
    void testOrQuery() {
        Query query = parse("error OR warn");
        assertNotNull(query);
        assertTrue(query.isBool());
        assertEquals(2, query.bool().should().size());
    }

    @Test
    void testNotQuery() {
        Query query = parse("error NOT debug");
        assertNotNull(query);
        assertTrue(query.isBool());
        assertFalse(query.bool().mustNot().isEmpty());
    }

    @Test
    void testNestedQuery() {
        Query query = parse("(error OR warn) AND appName:service1 NOT level:DEBUG");
        assertNotNull(query);
        assertTrue(query.isBool());
    }

    @Test
    void testDeepNestedQuery() {
        StringBuilder sb = new StringBuilder();
        sb.append("error");
        for (int i = 0; i < 50; i++) {
            sb.append(" AND test").append(i);
        }
        Query query = parse(sb.toString());
        assertNotNull(query);
        assertTrue(query.isBool());
    }

    @Test
    void testFieldQuery() {
        Query query = parse("level:ERROR");
        assertNotNull(query);
    }

    @Test
    void testWildcardQuery() {
        Query query = parse("user*");
        assertNotNull(query);
        assertTrue(query.isBool());
    }

    @Test
    void testPhraseQuery() {
        Query query = parse("\"connection failed\"");
        assertNotNull(query);
        assertTrue(query.isMultiMatch());
    }

    @Test
    void testRangeQuery() {
        Query query = parse("status:[400 TO 500]");
        assertNotNull(query);
    }

    @Test
    void testInvalidQuery() {
        assertThrows(Exception.class, () -> parse("error AND ("));
    }
}
