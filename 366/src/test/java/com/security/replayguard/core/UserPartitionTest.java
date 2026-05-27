package com.security.replayguard.core;

import com.security.replayguard.model.RequestFeature;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class UserPartitionTest {

    private RequestHasher requestHasher;

    @BeforeEach
    void setUp() {
        requestHasher = new RequestHasher();
    }

    @Test
    @DisplayName("Compute partition key - with userId")
    void testComputePartitionKey_WithUserId() {
        RequestFeature feature = createFeatureWithUser("user-123", "/api/test");

        String partitionKey = requestHasher.computePartitionKey(feature);

        assertNotNull(partitionKey);
        assertTrue(partitionKey.startsWith("user:"));
        assertEquals(13, partitionKey.length());
    }

    @Test
    @DisplayName("Compute partition key - with device fingerprint")
    void testComputePartitionKey_WithDeviceFingerprint() {
        RequestFeature feature = createFeatureWithDevice("device-fp-456", "/api/test");

        String partitionKey = requestHasher.computePartitionKey(feature);

        assertNotNull(partitionKey);
        assertTrue(partitionKey.startsWith("device:"));
    }

    @Test
    @DisplayName("Compute partition key - with IP address")
    void testComputePartitionKey_WithIpAddress() {
        RequestFeature feature = createFeatureWithIp("192.168.1.100", "/api/test");

        String partitionKey = requestHasher.computePartitionKey(feature);

        assertNotNull(partitionKey);
        assertTrue(partitionKey.startsWith("ip:"));
    }

    @Test
    @DisplayName("Compute partition key - no identifier returns unknown")
    void testComputePartitionKey_NoIdentifier() {
        RequestFeature feature = RequestFeature.builder()
                .requestPath("/api/test")
                .build();

        String partitionKey = requestHasher.computePartitionKey(feature);

        assertEquals("unknown", partitionKey);
    }

    @Test
    @DisplayName("Compute partition key - userId takes priority")
    void testComputePartitionKey_UserIdPriority() {
        RequestFeature feature = createFeatureWithUser("user-123", "/api/test");
        feature.setDeviceFingerprint("device-fp");
        feature.setIpAddress("192.168.1.1");

        String partitionKey = requestHasher.computePartitionKey(feature);

        assertTrue(partitionKey.startsWith("user:"));
    }

    @Test
    @DisplayName("Compute unique hash with user - different users get different hashes")
    void testComputeUniqueHashWithUser_DifferentUsers() {
        RequestFeature feature1 = createFeatureWithUser("user-1", "/api/test");
        RequestFeature feature2 = createFeatureWithUser("user-2", "/api/test");

        String hash1 = requestHasher.computeUniqueHashWithUser(feature1);
        String hash2 = requestHasher.computeUniqueHashWithUser(feature2);

        assertNotEquals(hash1, hash2, "Different users should get different hashes");
    }

    @Test
    @DisplayName("Compute unique hash with user - same user same path gets same hash")
    void testComputeUniqueHashWithUser_SameUserSamePath() {
        RequestFeature feature1 = createFeatureWithUser("user-1", "/api/test");
        RequestFeature feature2 = createFeatureWithUser("user-1", "/api/test");

        String hash1 = requestHasher.computeUniqueHashWithUser(feature1);
        String hash2 = requestHasher.computeUniqueHashWithUser(feature2);

        assertEquals(hash1, hash2, "Same user same path should get same hash");
    }

    @Test
    @DisplayName("Compute unique hash with user - different paths get different hashes")
    void testComputeUniqueHashWithUser_DifferentPaths() {
        RequestFeature feature1 = createFeatureWithUser("user-1", "/api/test1");
        RequestFeature feature2 = createFeatureWithUser("user-1", "/api/test2");

        String hash1 = requestHasher.computeUniqueHashWithUser(feature1);
        String hash2 = requestHasher.computeUniqueHashWithUser(feature2);

        assertNotEquals(hash1, hash2, "Different paths should get different hashes");
    }

    @Test
    @DisplayName("Compute user ID partition - consistent for same user")
    void testComputeUserIdPartition_Consistent() {
        String partition1 = requestHasher.computeUserIdPartition("user-123");
        String partition2 = requestHasher.computeUserIdPartition("user-123");

        assertEquals(partition1, partition2);
        assertTrue(partition1.startsWith("user:"));
    }

    @Test
    @DisplayName("Compute user ID partition - different users get different partitions")
    void testComputeUserIdPartition_DifferentUsers() {
        String partition1 = requestHasher.computeUserIdPartition("user-1");
        String partition2 = requestHasher.computeUserIdPartition("user-2");

        assertNotEquals(partition1, partition2);
    }

    @Test
    @DisplayName("Compute user ID partition - null handling")
    void testComputeUserIdPartition_Null() {
        String partition = requestHasher.computeUserIdPartition(null);

        assertNotNull(partition);
        assertTrue(partition.startsWith("user:"));
    }

    @Test
    @DisplayName("UserId normalization - case insensitive")
    void testUserIdNormalization_CaseInsensitive() {
        RequestFeature feature1 = createFeatureWithUser("User-123", "/api/test");
        RequestFeature feature2 = createFeatureWithUser("user-123", "/api/test");

        String hash1 = requestHasher.computeUniqueHashWithUser(feature1);
        String hash2 = requestHasher.computeUniqueHashWithUser(feature2);

        assertEquals(hash1, hash2, "User ID should be case insensitive");
    }

    @Test
    @DisplayName("UserId normalization - trimmed")
    void testUserIdNormalization_Trimmed() {
        RequestFeature feature1 = createFeatureWithUser("  user-123  ", "/api/test");
        RequestFeature feature2 = createFeatureWithUser("user-123", "/api/test");

        String hash1 = requestHasher.computeUniqueHashWithUser(feature1);
        String hash2 = requestHasher.computeUniqueHashWithUser(feature2);

        assertEquals(hash1, hash2, "User ID should be trimmed");
    }

    private RequestFeature createFeatureWithUser(String userId, String path) {
        Map<String, String> params = new HashMap<>();
        params.put("key", "value");

        return RequestFeature.builder()
                .requestPath(path)
                .method("POST")
                .queryParams(params)
                .bodyHash("abc123")
                .userId(userId)
                .build();
    }

    private RequestFeature createFeatureWithDevice(String deviceFp, String path) {
        Map<String, String> params = new HashMap<>();
        params.put("key", "value");

        return RequestFeature.builder()
                .requestPath(path)
                .method("POST")
                .queryParams(params)
                .bodyHash("abc123")
                .deviceFingerprint(deviceFp)
                .build();
    }

    private RequestFeature createFeatureWithIp(String ip, String path) {
        Map<String, String> params = new HashMap<>();
        params.put("key", "value");

        return RequestFeature.builder()
                .requestPath(path)
                .method("POST")
                .queryParams(params)
                .bodyHash("abc123")
                .ipAddress(ip)
                .build();
    }
}
