package com.analytics.config;

import org.apache.flink.contrib.streaming.state.ConfigurableOptions;
import org.apache.flink.contrib.streaming.state.EmbeddedRocksDBStateBackend;
import org.apache.flink.contrib.streaming.state.PredefinedOptions;
import org.apache.flink.contrib.streaming.state.RocksDBOptions;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.configuration.MemorySize;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class StateBackendConfig {

    private static final Logger LOG = LoggerFactory.getLogger(StateBackendConfig.class);

    public static EmbeddedRocksDBStateBackend createRocksDBStateBackend() {
        Configuration rocksDBConfig = new Configuration();
        
        rocksDBConfig.set(RocksDBOptions.ENABLE_INCREMENTAL_CHECKPOINTING, true);
        
        rocksDBConfig.set(RocksDBOptions.COMPACT_ON_CHECKPOINT, true);
        
        rocksDBConfig.set(RocksDBOptions.USE_DYNAMIC_LEVEL_SIZE, true);
        
        rocksDBConfig.set(RocksDBOptions.MAX_BACKGROUND_THREADS, 4);
        
        rocksDBConfig.set(RocksDBOptions.MAX_OPEN_FILES, 1000);
        
        rocksDBConfig.set(RocksDBOptions.WRITE_BUFFER_SIZE, new MemorySize(64 * 1024 * 1024));
        
        rocksDBConfig.set(RocksDBOptions.MAX_WRITE_BUFFER_NUMBER, 4);
        
        rocksDBConfig.set(RocksDBOptions.MIN_WRITE_BUFFER_NUMBER_TO_MERGE, 2);
        
        rocksDBConfig.set(RocksDBOptions.LEVEL0_FILE_NUM_COMPACTION_TRIGGER, 4);
        
        rocksDBConfig.set(RocksDBOptions.LEVEL0_SLOWDOWN_WRITES_TRIGGER, 20);
        
        rocksDBConfig.set(RocksDBOptions.LEVEL0_STOP_WRITES_TRIGGER, 36);
        
        rocksDBConfig.set(RocksDBOptions.TARGET_FILE_SIZE_BASE, new MemorySize(64 * 1024 * 1024));
        
        rocksDBConfig.set(RocksDBOptions.MAX_SIZE_LEVEL_BASE, new MemorySize(512 * 1024 * 1024));
        
        rocksDBConfig.set(RocksDBOptions.BLOCK_CACHE_SIZE, new MemorySize(256 * 1024 * 1024));
        
        rocksDBConfig.set(RocksDBOptions.BLOCK_SIZE, new MemorySize(16 * 1024));
        
        rocksDBConfig.set(RocksDBOptions.ENABLE_BLOOM_FILTER, true);
        
        rocksDBConfig.set(RocksDBOptions.BLOOM_FILTER_BITS_PER_KEY, 10);

        EmbeddedRocksDBStateBackend rocksDBStateBackend = new EmbeddedRocksDBStateBackend(true);
        
        rocksDBStateBackend.setPredefinedOptions(PredefinedOptions.SPINNING_DISK_OPTIMIZED_HIGH_MEM);
        
        LOG.info("RocksDB state backend configured with incremental checkpointing enabled");
        
        return rocksDBStateBackend;
    }
}
