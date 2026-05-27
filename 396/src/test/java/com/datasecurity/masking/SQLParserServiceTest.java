package com.datasecurity.masking;

import com.datasecurity.masking.sql.SQLParserService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class SQLParserServiceTest {

    @Autowired
    private SQLParserService sqlParserService;

    @Test
    void testParseSimpleSelect() throws Exception {
        String sql = "SELECT id, name, phone FROM users WHERE id = 1";
        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        assertEquals("SELECT", parsed.getSqlType());
        assertEquals(1, parsed.getTables().size());
        assertEquals("users", parsed.getTables().get(0).getName());
        assertEquals(3, parsed.getColumns().size());
        assertFalse(parsed.isHasSubQuery());
        assertFalse(parsed.isHasUnion());
    }

    @Test
    void testParseSelectWithJoin() throws Exception {
        String sql = "SELECT u.id, u.name, o.order_no " +
                "FROM users u " +
                "JOIN orders o ON u.id = o.user_id " +
                "WHERE u.status = 1";
        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        assertEquals(2, parsed.getTables().size());
        List<String> tableNames = sqlParserService.extractAllTableNames(parsed);
        assertTrue(tableNames.contains("users"));
        assertTrue(tableNames.contains("orders"));
    }

    @Test
    void testParseSubSelectInFrom() throws Exception {
        String sql = "SELECT * FROM (SELECT id, name, phone FROM users WHERE status = 1) t " +
                "WHERE t.id > 100";
        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        assertTrue(parsed.isHasSubQuery());
        assertTrue(parsed.getSubSelects().size() > 0);
    }

    @Test
    void testParseSubSelectInWhere() throws Exception {
        String sql = "SELECT id, name FROM users " +
                "WHERE id IN (SELECT user_id FROM orders WHERE status = 'PAID')";
        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        List<String> columns = sqlParserService.extractAllColumnNames(parsed);
        assertTrue(columns.contains("id"));
        assertTrue(columns.contains("name"));
        assertTrue(columns.contains("user_id"));
    }

    @Test
    void testParseUnion() throws Exception {
        String sql = "SELECT id, name FROM customers " +
                "UNION " +
                "SELECT id, name FROM suppliers";
        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        assertTrue(parsed.isHasUnion());
        assertEquals(2, parsed.getUnions().size());
    }

    @Test
    void testParseUnionAll() throws Exception {
        String sql = "SELECT id, name FROM customers " +
                "UNION ALL " +
                "SELECT id, name FROM suppliers";
        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        assertTrue(parsed.isHasUnion());
        assertTrue(parsed.getUnions().get(1).isAll());
    }

    @Test
    void testExtractAllTableNames() throws Exception {
        String sql = "SELECT u.name, o.order_no, p.product_name " +
                "FROM users u " +
                "JOIN orders o ON u.id = o.user_id " +
                "JOIN products p ON o.product_id = p.id";
        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        List<String> tables = sqlParserService.extractAllTableNames(parsed);
        assertEquals(3, tables.size());
        assertTrue(tables.contains("users"));
        assertTrue(tables.contains("orders"));
        assertTrue(tables.contains("products"));
    }

    @Test
    void testExtractAllColumnNames() throws Exception {
        String sql = "SELECT id, name, phone, email FROM users WHERE status = 1";
        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        List<String> columns = sqlParserService.extractAllColumnNames(parsed);
        assertTrue(columns.contains("id"));
        assertTrue(columns.contains("name"));
        assertTrue(columns.contains("phone"));
        assertTrue(columns.contains("email"));
        assertTrue(columns.contains("status"));
    }

    @Test
    void testIsWriteOperation() {
        assertTrue(sqlParserService.isWriteOperation("INSERT INTO users (name) VALUES ('test')"));
        assertTrue(sqlParserService.isWriteOperation("UPDATE users SET name = 'test' WHERE id = 1"));
        assertTrue(sqlParserService.isWriteOperation("DELETE FROM users WHERE id = 1"));
        assertTrue(sqlParserService.isWriteOperation("CREATE TABLE test (id INT)"));
        assertTrue(sqlParserService.isWriteOperation("ALTER TABLE test ADD COLUMN name VARCHAR(100)"));
        assertTrue(sqlParserService.isWriteOperation("DROP TABLE test"));
        assertFalse(sqlParserService.isWriteOperation("SELECT * FROM users"));
    }

    @Test
    void testParseComplexQuery() throws Exception {
        String sql = "SELECT " +
                "    u.id, " +
                "    u.name, " +
                "    (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) as order_count, " +
                "    (SELECT SUM(amount) FROM payments p WHERE p.user_id = u.id) as total_paid " +
                "FROM users u " +
                "WHERE u.id IN (SELECT user_id FROM vip_members WHERE level = 'GOLD') " +
                "AND EXISTS (SELECT 1 FROM orders o2 WHERE o2.user_id = u.id AND o2.status = 'SHIPPED')";

        SQLParserService.ParsedSQL parsed = sqlParserService.parse(sql);

        assertTrue(parsed.isHasSubQuery());
        List<String> tables = sqlParserService.extractAllTableNames(parsed);
        assertTrue(tables.contains("users"));
        assertTrue(tables.contains("orders"));
        assertTrue(tables.contains("payments"));
        assertTrue(tables.contains("vip_members"));
    }
}
