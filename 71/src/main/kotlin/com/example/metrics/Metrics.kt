package com.example.metrics

import kotlinx.serialization.Serializable
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference

@Serializable
data class MetricsSnapshot(
    val totalRequests: Long,
    val cacheHits: Long,
    val cacheMisses: Long,
    val cacheHitRate: Double,
    val providerSuccesses: Map<String, Long>,
    val providerFailures: Map<String, Long>,
    val alertsFired: Long,
    val startedAt: Long,
    val uptimeSeconds: Long
)

class MetricsRecorder {
    private val totalRequests = AtomicLong(0)
    private val cacheHits = AtomicLong(0)
    private val cacheMisses = AtomicLong(0)
    private val providerSuccesses = AtomicReference<MutableMap<String, AtomicLong>>(mutableMapOf())
    private val providerFailures = AtomicReference<MutableMap<String, AtomicLong>>(mutableMapOf())
    private val alertsFired = AtomicLong(0)
    private val startedAt = System.currentTimeMillis()

    fun recordRequest() {
        totalRequests.incrementAndGet()
    }

    fun recordCacheHit() {
        cacheHits.incrementAndGet()
    }

    fun recordCacheMiss() {
        cacheMisses.incrementAndGet()
    }

    fun recordProviderSuccess(providerName: String) {
        val map = providerSuccesses.get()
        map.getOrPut(providerName, { AtomicLong(0) }).incrementAndGet()
    }

    fun recordProviderFailure(providerName: String) {
        val map = providerFailures.get()
        map.getOrPut(providerName, { AtomicLong(0) }).incrementAndGet()
    }

    fun recordAlertFired() {
        alertsFired.incrementAndGet()
    }

    fun snapshot(): MetricsSnapshot {
        val hits = cacheHits.get()
        val misses = cacheMisses.get()
        val total = hits + misses

        val hitRate = if (total > 0) {
            hits.toDouble() / total.toDouble() * 100.0
        } else {
            0.0
        }

        val now = System.currentTimeMillis()
        val uptimeSeconds = (now - startedAt) / 1000

        return MetricsSnapshot(
            totalRequests = totalRequests.get(),
            cacheHits = hits,
            cacheMisses = misses,
            cacheHitRate = hitRate,
            providerSuccesses = providerSuccesses.get().mapValues { it.value.get() },
            providerFailures = providerFailures.get().mapValues { it.value.get() },
            alertsFired = alertsFired.get(),
            startedAt = startedAt,
            uptimeSeconds = uptimeSeconds
        )
    }

    fun reset() {
        totalRequests.set(0)
        cacheHits.set(0)
        cacheMisses.set(0)
        providerSuccesses.set(mutableMapOf())
        providerFailures.set(mutableMapOf())
        alertsFired.set(0)
    }
}
