package com.logplatform;

import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import com.logplatform.parser.QueryParserService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class QueryParserTest {

    @Autowired
    private QueryParserService queryParserService;

    @Test
    void testSimpleTermQuery() {
        Query query = queryParserService.parseQuery("error");
        assertNotNull(query);
        assertTrue(query.isMultiMatch());
    }

    @Test
    void testAndQuery() {
        Query query = queryParserService.parseQuery("error AND timeout");
        assertNotNull(query);
        assertTrue(query.isBool());
    }

    @Test
    void testOrQuery() {
        Query query = queryParserService.parseQuery("error OR warn");
        assertNotNull(query);
        assertTrue(query.isBool());
    }

    @Test
    void testNotQuery() {
        Query query = queryParserService.parseQuery("error NOT debug");
        assertNotNull(query);
        assertTrue(query.isBool());
    }

    @Test
    void testFieldQuery() {
        Query query = queryParserService.parseQuery("level:ERROR");
        assertNotNull(query);
    }

    @Test
    void testWildcardQuery() {
        Query query = queryParserService.parseQuery("user*");
        assertNotNull(query);
    }

    @Test
    void testPhraseQuery() {
        Query query = queryParserService.parseQuery("\"connection failed\"");
        assertNotNull(query);
    }

    @Test
    void testRangeQuery() {
        Query query = queryParserService.parseQuery("status:[400 TO 500]");
        assertNotNull(query);
    }

    @Test
    void testComplexQuery() {
        Query query = queryParserService.parseQuery("(error OR warn) AND appName:service1 NOT level:DEBUG");
        assertNotNull(query);
    }

    @Test
    void testInvalidQuery() {
        assertThrows(IllegalArgumentException.class, () -> {
            queryParserService.parseQuery("error AND (");
        });
    }
}
