package com.hotconfig.core.source;

import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.listener.ConfigChangeListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

public abstract class AbstractConfigSource implements ConfigSource {

    protected final Logger logger = LoggerFactory.getLogger(getClass());

    protected final List<ConfigChangeListener> listeners = new CopyOnWriteArrayList<>();

    protected ExecutorService asyncExecutor;

    protected volatile boolean initialized = false;

    protected volatile boolean destroyed = false;

    @Override
    public void addChangeListener(ConfigChangeListener listener) {
        if (listener != null && !listeners.contains(listener)) {
            listeners.add(listener);
            logger.debug("Added config change listener: {}", listener.getClass().getName());
        }
    }

    @Override
    public void removeChangeListener(ConfigChangeListener listener) {
        if (listener != null) {
            listeners.remove(listener);
            logger.debug("Removed config change listener: {}", listener.getClass().getName());
        }
    }

    @Override
    public void fireChangeEvent(ConfigChangeEvent event) {
        if (event == null || listeners.isEmpty()) {
            return;
        }

        logger.debug("Firing config change event from source: {}, changed keys: {}",
                getSourceName(), event.getChangedKeys());

        for (ConfigChangeListener listener : listeners) {
            try {
                if (listener.support(event)) {
                    if (isAsyncListener(listener)) {
                        asyncExecute(() -> invokeListener(listener, event));
                    } else {
                        invokeListener(listener, event);
                    }
                }
            } catch (Exception e) {
                logger.error("Failed to invoke config change listener: {}",
                        listener.getClass().getName(), e);
            }
        }
    }

    protected void invokeListener(ConfigChangeListener listener, ConfigChangeEvent event) {
        try {
            listener.onChange(event);
        } catch (Exception e) {
            logger.error("Exception in config change listener", e);
        }
    }

    protected boolean isAsyncListener(ConfigChangeListener listener) {
        return false;
    }

    protected void asyncExecute(Runnable task) {
        if (asyncExecutor == null || asyncExecutor.isShutdown()) {
            initAsyncExecutor();
        }
        asyncExecutor.submit(task);
    }

    protected void initAsyncExecutor() {
        this.asyncExecutor = Executors.newFixedThreadPool(2, new ThreadFactory() {
            private final AtomicInteger counter = new AtomicInteger(0);

            @Override
            public Thread newThread(Runnable r) {
                Thread thread = new Thread(r, "hot-config-async-" + counter.incrementAndGet());
                thread.setDaemon(true);
                return thread;
            }
        });
    }

    @Override
    public void init() {
        if (initialized) {
            return;
        }
        synchronized (this) {
            if (initialized) {
                return;
            }
            try {
                initAsyncExecutor();
                doInit();
                initialized = true;
                logger.info("Config source [{}] initialized successfully", getSourceName());
            } catch (Exception e) {
                logger.error("Failed to initialize config source: {}", getSourceName(), e);
                throw new RuntimeException("Failed to initialize config source: " + getSourceName(), e);
            }
        }
    }

    protected abstract void doInit() throws Exception;

    @Override
    public void destroy() {
        if (destroyed) {
            return;
        }
        synchronized (this) {
            if (destroyed) {
                return;
            }
            try {
                doDestroy();
                if (asyncExecutor != null && !asyncExecutor.isShutdown()) {
                    asyncExecutor.shutdown();
                }
                listeners.clear();
                destroyed = true;
                logger.info("Config source [{}] destroyed successfully", getSourceName());
            } catch (Exception e) {
                logger.error("Failed to destroy config source: {}", getSourceName(), e);
            }
        }
    }

    protected abstract void doDestroy() throws Exception;

    @Override
    public boolean isAvailable() {
        return initialized && !destroyed;
    }

    @Override
    public String getName() {
        return getSourceName();
    }

    protected abstract String getSourceName();
}
