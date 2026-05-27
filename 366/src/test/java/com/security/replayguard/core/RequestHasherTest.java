package com.security.replayguard.core;

import com.security.replayguard.model.RequestFeature;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class RequestHasherTest {

    private RequestHasher requestHasher;

    @BeforeEach
    void setUp() {
        requestHasher = new RequestHasher();
    }

    @Test
    @DisplayName("Compute unique hash - same features produce same hash")
    void testComputeUniqueHash_Consistency() {
        RequestFeature feature1 = createSampleFeature();
        RequestFeature feature2 = createSampleFeature();

        String hash1 = requestHasher.computeUniqueHash(feature1);
        String hash2 = requestHasher.computeUniqueHash(feature2);

        assertEquals(hash1, hash2, "Same features should produce same unique hash");
        assertNotNull(hash1);
        assertFalse(hash1.isEmpty());
    }

    @Test
    @DisplayName("Compute unique hash - different path produces different hash")
    void testComputeUniqueHash_DifferentPath() {
        RequestFeature feature1 = createSampleFeature();
        feature1.setRequestPath("/api/test1");

        RequestFeature feature2 = createSampleFeature();
        feature2.setRequestPath("/api/test2");

        String hash1 = requestHasher.computeUniqueHash(feature1);
        String hash2 = requestHasher.computeUniqueHash(feature2);

        assertNotEquals(hash1, hash2, "Different paths should produce different hash");
    }

    @Test
    @DisplayName("Compute unique hash - different params produce different hash")
    void testComputeUniqueHash_DifferentParams() {
        RequestFeature feature1 = createSampleFeature();
        feature1.getQueryParams().put("key1", "value1");

        RequestFeature feature2 = createSampleFeature();
        feature2.getQueryParams().put("key1", "value2");

        String hash1 = requestHasher.computeUniqueHash(feature1);
        String hash2 = requestHasher.computeUniqueHash(feature2);

        assertNotEquals(hash1, hash2, "Different params should produce different hash");
    }

    @Test
    @DisplayName("Compute unique hash - param order doesn't matter")
    void testComputeUniqueHash_ParamOrder() {
        RequestFeature feature1 = createSampleFeature();
        feature1.getQueryParams().put("a", "1");
        feature1.getQueryParams().put("b", "2");

        RequestFeature feature2 = createSampleFeature();
        feature2.getQueryParams().put("b", "2");
        feature2.getQueryParams().put("a", "1");

        String hash1 = requestHasher.computeUniqueHash(feature1);
        String hash2 = requestHasher.computeUniqueHash(feature2);

        assertEquals(hash1, hash2, "Param order should not affect hash");
    }

    @Test
    @DisplayName("Compute full hash - includes nonce and timestamp")
    void testComputeFullHash_IncludesNonce() {
        RequestFeature feature1 = createSampleFeature();
        feature1.setNonce("nonce1");
        feature1.setTimestamp("1234567890");

        RequestFeature feature2 = createSampleFeature();
        feature2.setNonce("nonce2");
        feature2.setTimestamp("1234567890");

        String hash1 = requestHasher.computeHash(feature1);
        String hash2 = requestHasher.computeHash(feature2);

        assertNotEquals(hash1, hash2, "Different nonce should produce different full hash");
    }

    @Test
    @DisplayName("Compute nonce hash - same inputs produce same hash")
    void testComputeNonceHash_Consistency() {
        String hash1 = requestHasher.computeNonceHash("device1", "nonce1", "1234567890");
        String hash2 = requestHasher.computeNonceHash("device1", "nonce1", "1234567890");

        assertEquals(hash1, hash2);
    }

    @Test
    @DisplayName("Compute nonce hash - different inputs produce different hash")
    void testComputeNonceHash_DifferentInputs() {
        String hash1 = requestHasher.computeNonceHash("device1", "nonce1", "1234567890");
        String hash2 = requestHasher.computeNonceHash("device1", "nonce2", "1234567890");

        assertNotEquals(hash1, hash2);
    }

    @Test
    @DisplayName("Compute request body hash - null handling")
    void testComputeRequestBodyHash_Null() {
        String hash = requestHasher.computeRequestBodyHash(null);
        assertEquals("", hash);
    }

    @Test
    @DisplayName("Compute request body hash - empty handling")
    void testComputeRequestBodyHash_Empty() {
        String hash = requestHasher.computeRequestBodyHash("");
        assertEquals("", hash);
    }

    @Test
    @DisplayName("Compute short hash - returns 16 characters")
    void testComputeShortHash() {
        String hash = requestHasher.computeShortHash("test-input");
        
        assertNotNull(hash);
        assertEquals(16, hash.length());
    }

    @Test
    @DisplayName("Hash length verification")
    void testHashLength() {
        RequestFeature feature = createSampleFeature();
        String hash = requestHasher.computeUniqueHash(feature);
        
        assertEquals(64, hash.length(), "SHA-256 hex hash should be 64 characters");
    }

    @Test
    @DisplayName("Path normalization - trailing slash removed")
    void testPathNormalization_TrailingSlash() {
        RequestFeature feature1 = createSampleFeature();
        feature1.setRequestPath("/api/test/");

        RequestFeature feature2 = createSampleFeature();
        feature2.setRequestPath("/api/test");

        String hash1 = requestHasher.computeUniqueHash(feature1);
        String hash2 = requestHasher.computeUniqueHash(feature2);

        assertEquals(hash1, hash2, "Trailing slash should be normalized");
    }

    @Test
    @DisplayName("Path normalization - case insensitive")
    void testPathNormalization_CaseInsensitive() {
        RequestFeature feature1 = createSampleFeature();
        feature1.setRequestPath("/API/TEST");

        RequestFeature feature2 = createSampleFeature();
        feature2.setRequestPath("/api/test");

        String hash1 = requestHasher.computeUniqueHash(feature1);
        String hash2 = requestHasher.computeUniqueHash(feature2);

        assertEquals(hash1, hash2, "Path should be case insensitive");
    }

    private RequestFeature createSampleFeature() {
        Map<String, String> params = new HashMap<>();
        params.put("key1", "value1");

        return RequestFeature.builder()
                .requestPath("/api/test")
                .method("POST")
                .queryParams(params)
                .bodyHash("abc123")
                .timestamp("1234567890")
                .nonce("test-nonce")
                .deviceFingerprint("device-fp-123")
                .ipAddress("192.168.1.1")
                .userAgent("Mozilla/5.0")
                .build();
    }
}
