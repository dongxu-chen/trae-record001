package com.distid.readable;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class FormattedIdTest {

    @Test
    void shouldFormatWithBizTagAndDcCode() {
        FormattedId id = FormattedId.of(123456789L, "ORDER", "dc1");
        assertNotNull(id.getReadableId());
        assertTrue(id.getReadableId().contains("ORDER"));
        assertTrue(id.getReadableId().contains("dc1"));
        assertNotNull(id.getBase62Id());
        assertEquals(123456789L, id.getRawId());
    }

    @Test
    void shouldFormatWithoutBizTag() {
        FormattedId id = FormattedId.of(999L, "", "dc1");
        assertFalse(id.getReadableId().contains("null"));
        assertTrue(id.getReadableId().contains("dc1"));
    }

    @Test
    void shouldIncludeTimePrefix() {
        FormattedId id = FormattedId.of(100L, "USER", "dc2");
        assertNotNull(id.getTimePrefix());
        assertTrue(id.getTimePrefix().length() >= 8);
    }
}
