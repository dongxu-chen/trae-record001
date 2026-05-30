package com.loganalytics.parser;

import com.loganalytics.model.NginxLogEvent;
import org.junit.Test;
import static org.junit.Assert.*;

public class NginxLogParserTest {

    @Test
    public void testParseStandardLog() {
        String logLine = "192.168.1.100 - - [28/May/2024:10:00:01 +0800] \"GET /api/v1/users HTTP/1.1\" 200 1234 \"https://example.com\" \"Mozilla/5.0\"";

        NginxLogEvent event = NginxLogParser.parse(logLine);

        assertNotNull(event);
        assertEquals("192.168.1.100", event.getRemoteAddr());
        assertEquals("GET", event.getMethod());
        assertEquals("/api/v1/users", event.getPath());
        assertEquals(200, event.getStatus());
        assertEquals(1234, event.getBodyBytesSent());
    }

    @Test
    public void testParseExtendedLog() {
        String logLine = "192.168.1.100 - - [28/May/2024:10:00:01 +0800] \"GET /api/v1/users HTTP/1.1\" 200 1234 \"https://example.com\" \"Mozilla/5.0\" 0.123 0.100 \"200\" \"api.example.com\"";

        NginxLogEvent event = NginxLogParser.parse(logLine);

        assertNotNull(event);
        assertEquals("192.168.1.100", event.getRemoteAddr());
        assertEquals("GET", event.getMethod());
        assertEquals("/api/v1/users", event.getPath());
        assertEquals(200, event.getStatus());
        assertEquals(0.123, event.getRequestTime(), 0.001);
        assertEquals(0.100, event.getUpstreamResponseTime(), 0.001);
        assertEquals("200", event.getUpstreamStatus());
        assertEquals("api.example.com", event.getHost());
    }

    @Test
    public void testParseInvalidLog() {
        String logLine = "invalid log line";

        NginxLogEvent event = NginxLogParser.parse(logLine);

        assertNull(event);
    }

    @Test
    public void testExtractPathWithQueryString() {
        String logLine = "192.168.1.100 - - [28/May/2024:10:00:01 +0800] \"GET /api/v1/users?page=1&limit=10 HTTP/1.1\" 200 1234 \"-\" \"Mozilla/5.0\"";

        NginxLogEvent event = NginxLogParser.parse(logLine);

        assertNotNull(event);
        assertEquals("/api/v1/users", event.getPath());
        assertEquals("/api/v1/users?page=1&limit=10", event.getUri());
    }
}
