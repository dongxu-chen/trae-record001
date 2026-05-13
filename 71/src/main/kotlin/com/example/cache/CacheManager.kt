package com.example.cache

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong

class CacheManager(
    private val ttlSeconds: Long = 600,
    private val maxEntries: Int = 1000
) : AutoCloseable {
    private data class CacheEntry(val data: String, val timestamp: AtomicLong = AtomicLong(System.currentTimeMillis()))

    private val cache = ConcurrentHashMap<String, CacheEntry>()
    private val cleanupScheduler: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor()

    init {
        val cleanupInterval = if (ttlSeconds < 60) ttlSeconds / 2 else 30
        cleanupScheduler.scheduleAtFixedRate(
            { cleanupExpiredEntries() },
            cleanupInterval,
            cleanupInterval,
            TimeUnit.SECONDS
        )
    }

    fun get(key: String): String? {
        val entry = cache[key] ?: return null
        if (isExpired(entry)) {
            cache.remove(key)
            return null
        }
        return entry.data
    }

    fun put(key: String, value: String) {
        if (cache.size >= maxEntries) {
            cleanupExpiredEntries()
            if (cache.size >= maxEntries) {
                evictOldest()
            }
        }
        cache[key] = CacheEntry(value)
    }

    fun invalidate(key: String) {
        cache.remove(key)
    }

    fun clear() {
        cache.clear()
    }

    fun cleanupExpiredEntries() {
        val ttlMillis = ttlSeconds * 1000
        val now = System.currentTimeMillis()
        val iterator = cache.entries.iterator()
        while (iterator.hasNext()) {
            val entry = iterator.next()
            if (now - entry.value.timestamp.get() > ttlMillis) {
                iterator.remove()
            }
        }
    }

    private fun isExpired(entry: CacheEntry): Boolean {
        val now = System.currentTimeMillis()
        val ttlMillis = ttlSeconds * 1000
        return now - entry.timestamp.get() > ttlMillis
    }

    private fun evictOldest() {
        var oldestKey: String? = null
        var oldestTime = Long.MAX_VALUE
        for ((key, entry) in cache.entries) {
            if (entry.timestamp.get() < oldestTime) {
                oldestTime = entry.timestamp.get()
                oldestKey = key
            }
        }
        oldestKey?.let { cache.remove(it) }
    }

    fun size(): Int = cache.size

    override fun close() {
        cleanupScheduler.shutdown()
    }
}
