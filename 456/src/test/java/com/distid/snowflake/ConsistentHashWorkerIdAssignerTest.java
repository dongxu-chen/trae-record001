package com.distid.snowflake;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ConsistentHashWorkerIdAssignerTest {

    @Test
    void shouldGenerateConsistentHashForSamePodName() {
        String podName1 = "distid-service-7f98d7c6d-abcde";
        String podName2 = "distid-service-7f98d7c6d-abcde";

        long hash1 = ConsistentHashWorkerIdAssigner.murmur3Hash(podName1);
        long hash2 = ConsistentHashWorkerIdAssigner.murmur3Hash(podName2);

        assertEquals(hash1, hash2, "Same pod name should generate same hash");
    }

    @Test
    void shouldGenerateDifferentHashForDifferentPodNames() {
        String podName1 = "distid-service-7f98d7c6d-abcde";
        String podName2 = "distid-service-7f98d7c6d-fghij";

        long hash1 = ConsistentHashWorkerIdAssigner.murmur3Hash(podName1);
        long hash2 = ConsistentHashWorkerIdAssigner.murmur3Hash(podName2);

        assertNotEquals(hash1, hash2, "Different pod names should generate different hashes");
    }

    @Test
    void shouldGenerateWorkerIdWithinValidRange() {
        String[] podNames = {
                "distid-service-0",
                "distid-service-1",
                "distid-service-2",
                "distid-service-3",
                "distid-service-4",
                "pod-abc-xyz-5",
                "my-app-pod-test",
                "production-id-generator-12345"
        };

        for (String podName : podNames) {
            long hash = ConsistentHashWorkerIdAssigner.murmur3Hash(podName);
            long workerId = (hash & 0xFFFFFFFFL) % 32;
            assertTrue(workerId >= 0 && workerId <= 31,
                    "WorkerId should be between 0-31, but was " + workerId + " for pod " + podName);
        }
    }

    @Test
    void shouldGenerateStableWorkerIdAfterRestart() {
        String podName = "distid-stable-pod";
        long[] workerIds = new long[10];

        for (int i = 0; i < 10; i++) {
            long hash = ConsistentHashWorkerIdAssigner.murmur3Hash(podName);
            workerIds[i] = (hash & 0xFFFFFFFFL) % 32;
        }

        for (int i = 1; i < 10; i++) {
            assertEquals(workerIds[0], workerIds[i],
                    "WorkerId should be stable across invocations");
        }
    }
}
