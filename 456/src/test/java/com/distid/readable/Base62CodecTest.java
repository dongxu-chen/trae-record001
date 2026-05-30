package com.distid.readable;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class Base62CodecTest {

    @Test
    void shouldEncodeAndDecode() {
        long value = 123456789L;
        String encoded = Base62Codec.encode(value);
        long decoded = Base62Codec.decode(encoded);
        assertEquals(value, decoded);
    }

    @Test
    void shouldEncodeZero() {
        assertEquals("0", Base62Codec.encode(0));
        assertEquals(0, Base62Codec.decode("0"));
    }

    @Test
    void shouldEncodeMaxLong() {
        long value = Long.MAX_VALUE;
        String encoded = Base62Codec.encode(value);
        long decoded = Base62Codec.decode(encoded);
        assertEquals(value, decoded);
    }

    @Test
    void shouldPadToMinLength() {
        String encoded = Base62Codec.encodeWithPadding(1, 8);
        assertTrue(encoded.length() >= 8);
        assertEquals(1, Base62Codec.decode(encoded.trim()));
    }

    @Test
    void shouldRejectNegativeValues() {
        assertThrows(IllegalArgumentException.class, () -> Base62Codec.encode(-1));
    }

    @Test
    void shouldRejectInvalidCharacters() {
        assertThrows(IllegalArgumentException.class, () -> Base62Codec.decode("!@#$"));
    }
}
