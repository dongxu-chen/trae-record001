package com.tracing.staining.context;

import java.util.HashMap;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.concurrent.atomic.AtomicInteger;

public class TransmittableThreadLocal<T> extends ThreadLocal<T> {

    private static final AtomicInteger HOLDER_ID_GENERATOR = new AtomicInteger(0);

    private static final ThreadLocal<WeakHashMap<TransmittableThreadLocal<Object>, ?>> HOLDER =
            ThreadLocal.withInitial(WeakHashMap::new);

    private final int id = HOLDER_ID_GENERATOR.getAndIncrement();

    @Override
    public final void set(T value) {
        if (value == null) {
            remove();
            return;
        }
        super.set(value);
        addThisToHolder();
    }

    @Override
    public final void remove() {
        removeThisFromHolder();
        super.remove();
    }

    private void addThisToHolder() {
        WeakHashMap<TransmittableThreadLocal<Object>, ?> holder = HOLDER.get();
        if (!holder.containsKey((TransmittableThreadLocal<Object>) this)) {
            holder.put((TransmittableThreadLocal<Object>) this, null);
        }
    }

    private void removeThisFromHolder() {
        WeakHashMap<TransmittableThreadLocal<Object>, ?> holder = HOLDER.get();
        holder.remove((TransmittableThreadLocal<Object>) this);
    }

    public static Map<TransmittableThreadLocal<Object>, Object> capture() {
        Map<TransmittableThreadLocal<Object>, Object> ttlValues = new HashMap<>();
        WeakHashMap<TransmittableThreadLocal<Object>, ?> holder = HOLDER.get();
        for (TransmittableThreadLocal<Object> ttl : holder.keySet()) {
            ttlValues.put(ttl, ttl.get());
        }
        return ttlValues;
    }

    public static Runnable wrap(Runnable runnable) {
        final Map<TransmittableThreadLocal<Object>, Object> captured = capture();
        return () -> {
            Map<TransmittableThreadLocal<Object>, Object> backup = backupAndSet(captured);
            try {
                runnable.run();
            } finally {
                restore(backup);
            }
        };
    }

    public static <V> Map<TransmittableThreadLocal<Object>, Object> backupAndSet(
            Map<TransmittableThreadLocal<Object>, Object> captured) {
        Map<TransmittableThreadLocal<Object>, Object> backup = new HashMap<>();
        for (Map.Entry<TransmittableThreadLocal<Object>, Object> entry : captured.entrySet()) {
            TransmittableThreadLocal<Object> ttl = entry.getKey();
            backup.put(ttl, ttl.get());
            ttl.set(entry.getValue());
        }
        return backup;
    }

    public static void restore(Map<TransmittableThreadLocal<Object>, Object> backup) {
        for (Map.Entry<TransmittableThreadLocal<Object>, Object> entry : backup.entrySet()) {
            TransmittableThreadLocal<Object> ttl = entry.getKey();
            Object value = entry.getValue();
            if (value == null) {
                ttl.remove();
            } else {
                ttl.set(value);
            }
        }
    }

    @Override
    public final boolean equals(Object o) {
        return this == o;
    }

    @Override
    public final int hashCode() {
        return id;
    }
}
