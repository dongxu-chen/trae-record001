package com.riskengine.engine.groovy;

import com.riskengine.model.RuleDefinition;
import groovy.lang.GroovyClassLoader;
import groovy.lang.GroovyObject;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.lang.ref.WeakReference;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

@Slf4j
@Component
public class GroovyScriptEngine {

    @Value("${risk.engine.groovy.classloader.unused-timeout-minutes:60}")
    private long unusedTimeoutMinutes;

    @Value("${risk.engine.groovy.classloader.cleanup-interval-ms:300000}")
    private long cleanupIntervalMs;

    private final Map<String, ScriptClassLoaderHolder> classLoaderCache = new ConcurrentHashMap<>();
    private final ReentrantLock cleanupLock = new ReentrantLock();

    @Data
    private static class ScriptClassLoaderHolder {
        private final GroovyClassLoader classLoader;
        private final WeakReference<Class<?>> scriptClassRef;
        private long lastAccessTime;
        private long loadTime;
        private long useCount;

        public ScriptClassLoaderHolder(GroovyClassLoader classLoader, Class<?> scriptClass) {
            this.classLoader = classLoader;
            this.scriptClassRef = new WeakReference<>(scriptClass);
            this.lastAccessTime = System.currentTimeMillis();
            this.loadTime = System.currentTimeMillis();
            this.useCount = 0;
        }

        public void access() {
            this.lastAccessTime = System.currentTimeMillis();
            this.useCount++;
        }
    }

    public synchronized Object execute(RuleDefinition rule, Map<String, Object> context) {
        String ruleCode = rule.getRuleCode();
        String script = rule.getGroovyScript();

        if (script == null || script.trim().isEmpty()) {
            return null;
        }

        try {
            Class<?> scriptClass = getOrCreateScriptClass(ruleCode, script);

            GroovyObject groovyObject = (GroovyObject) scriptClass.getDeclaredConstructor().newInstance();

            if (groovyObject instanceof groovy.lang.Script) {
                groovy.lang.Script scriptObj = (groovy.lang.Script) groovyObject;
                context.forEach(scriptObj.getBinding()::setVariable);
                return scriptObj.run();
            } else {
                for (Map.Entry<String, Object> entry : context.entrySet()) {
                    try {
                        groovyObject.setProperty(entry.getKey(), entry.getValue());
                    } catch (Exception ignored) {
                    }
                }
                try {
                    return groovyObject.invokeMethod("evaluate", new Object[]{context});
                } catch (Exception e) {
                    return groovyObject.invokeMethod("run", new Object[]{});
                }
            }
        } catch (Exception e) {
            log.error("Groovy script execution failed for rule: {}", ruleCode, e);
            throw new RuntimeException("Groovy script execution failed: " + e.getMessage(), e);
        }
    }

    private Class<?> getOrCreateScriptClass(String ruleCode, String script) throws Exception {
        ScriptClassLoaderHolder holder = classLoaderCache.get(ruleCode);

        if (holder != null) {
            Class<?> cachedClass = holder.getScriptClassRef().get();
            if (cachedClass != null) {
                holder.access();
                log.trace("Using cached class for rule: {}, useCount: {}", ruleCode, holder.getUseCount());
                return cachedClass;
            } else {
                log.info("Cached class for rule {} was GC'd, reloading", ruleCode);
                classLoaderCache.remove(ruleCode);
                holder = null;
            }
        }

        GroovyClassLoader isolatedClassLoader = new GroovyClassLoader(
                Thread.currentThread().getContextClassLoader()
        );

        try {
            Class<?> scriptClass = isolatedClassLoader.parseClass(script);

            ScriptClassLoaderHolder newHolder = new ScriptClassLoaderHolder(isolatedClassLoader, scriptClass);
            newHolder.access();
            classLoaderCache.put(ruleCode, newHolder);

            log.info("Groovy script parsed with isolated ClassLoader: {}, loaded in {}ms",
                    ruleCode, System.currentTimeMillis() - newHolder.getLoadTime());

            return scriptClass;
        } catch (Exception e) {
            try {
                isolatedClassLoader.close();
            } catch (Exception ignored) {
            }
            throw e;
        }
    }

    public synchronized void reloadScript(String ruleCode, String script) {
        try {
            unloadScript(ruleCode, true);

            if (script != null && !script.trim().isEmpty()) {
                getOrCreateScriptClass(ruleCode, script);
                log.info("Groovy script reloaded with new isolated ClassLoader: {}", ruleCode);
            }
        } catch (Exception e) {
            log.error("Failed to reload Groovy script: {}", ruleCode, e);
            throw new RuntimeException("Groovy script reload failed: " + e.getMessage(), e);
        }
    }

    public synchronized void removeScript(String ruleCode) {
        unloadScript(ruleCode, true);
        log.info("Groovy script removed and ClassLoader cleaned: {}", ruleCode);
    }

    private void unloadScript(String ruleCode, boolean removeFromCache) {
        ScriptClassLoaderHolder holder = removeFromCache
                ? classLoaderCache.remove(ruleCode)
                : classLoaderCache.get(ruleCode);

        if (holder != null) {
            try {
                Class<?> clazz = holder.getScriptClassRef().get();
                if (clazz != null) {
                    holder.getClassLoader().removeClass(clazz);
                }
            } catch (Exception e) {
                log.warn("Failed to remove class from ClassLoader for rule: {}", ruleCode, e);
            }

            try {
                holder.getClassLoader().close();
                log.debug("GroovyClassLoader closed for rule: {}, useCount: {}, alive: {}s",
                        ruleCode, holder.getUseCount(),
                        (System.currentTimeMillis() - holder.getLoadTime()) / 1000);
            } catch (Exception e) {
                log.warn("Failed to close ClassLoader for rule: {}", ruleCode, e);
            }
        }
    }

    public boolean validateScript(String script) {
        GroovyClassLoader tempClassLoader = new GroovyClassLoader(
                Thread.currentThread().getContextClassLoader()
        );
        try {
            Class<?> parsed = tempClassLoader.parseClass(script);
            tempClassLoader.removeClass(parsed);
            return true;
        } catch (Exception e) {
            log.warn("Groovy script validation failed: {}", e.getMessage());
            return false;
        } finally {
            try {
                tempClassLoader.close();
            } catch (Exception ignored) {
            }
        }
    }

    public boolean isScriptCached(String ruleCode) {
        ScriptClassLoaderHolder holder = classLoaderCache.get(ruleCode);
        return holder != null && holder.getScriptClassRef().get() != null;
    }

    @Scheduled(fixedRateString = "${risk.engine.groovy.classloader.cleanup-interval-ms:300000}")
    public void scheduledCleanup() {
        if (!cleanupLock.tryLock()) {
            log.debug("Previous ClassLoader cleanup still in progress, skipping");
            return;
        }
        try {
            cleanupUnusedClassLoaders();
        } finally {
            cleanupLock.unlock();
        }
    }

    public void cleanupUnusedClassLoaders() {
        long now = System.currentTimeMillis();
        long timeoutMs = TimeUnit.MINUTES.toMillis(unusedTimeoutMinutes);
        int cleanedCount = 0;

        log.info("Starting Groovy ClassLoader cleanup, current loaded: {}", classLoaderCache.size());

        for (Map.Entry<String, ScriptClassLoaderHolder> entry : classLoaderCache.entrySet()) {
            String ruleCode = entry.getKey();
            ScriptClassLoaderHolder holder = entry.getValue();

            long idleTime = now - holder.getLastAccessTime();

            if (idleTime > timeoutMs) {
                log.info("Unloading idle script ClassLoader: rule={}, idle={}min, useCount={}",
                        ruleCode, (idleTime / 60000), holder.getUseCount());
                unloadScript(ruleCode, true);
                cleanedCount++;
            }
        }

        if (cleanedCount > 0) {
            log.info("ClassLoader cleanup completed: unloaded {} idle scripts, remaining: {}",
                    cleanedCount, classLoaderCache.size());
        } else {
            log.info("ClassLoader cleanup completed: no idle scripts to unload");
        }
    }

    public int getLoadedClassLoaderCount() {
        return (int) classLoaderCache.entrySet().stream()
                .filter(e -> e.getValue().getScriptClassRef().get() != null)
                .count();
    }

    public Map<String, Object> getClassLoaderStats() {
        return Map.of(
                "totalRules", classLoaderCache.size(),
                "activeRules", getLoadedClassLoaderCount(),
                "unusedTimeoutMinutes", unusedTimeoutMinutes,
                "cleanupIntervalMs", cleanupIntervalMs,
                "rules", classLoaderCache.entrySet().stream().map(e -> Map.of(
                        "ruleCode", e.getKey(),
                        "loaded", (e.getValue().getScriptClassRef().get() != null),
                        "useCount", e.getValue().getUseCount(),
                        "lastAccessTimeMs", System.currentTimeMillis() - e.getValue().getLastAccessTime(),
                        "aliveTimeMs", System.currentTimeMillis() - e.getValue().getLoadTime()
                )).toList()
        );
    }
}
