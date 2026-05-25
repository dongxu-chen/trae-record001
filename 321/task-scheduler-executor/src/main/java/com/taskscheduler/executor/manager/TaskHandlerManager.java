package com.taskscheduler.executor.manager;

import com.taskscheduler.common.handler.ITaskHandler;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class TaskHandlerManager implements ApplicationContextAware {

    private final Map<String, ITaskHandler> handlerMap = new ConcurrentHashMap<>();

    @Override
    public void setApplicationContext(ApplicationContext applicationContext) throws BeansException {
        Map<String, ITaskHandler> beans = applicationContext.getBeansOfType(ITaskHandler.class);
        for (Map.Entry<String, ITaskHandler> entry : beans.entrySet()) {
            String beanName = entry.getKey();
            ITaskHandler handler = entry.getValue();
            handlerMap.put(beanName, handler);
            String className = handler.getClass().getSimpleName();
            if (!beanName.equals(className)) {
                handlerMap.put(className, handler);
            }
            log.info("Registered task handler: {} -> {}", beanName, handler.getClass().getName());
        }
        log.info("Total registered task handlers: {}", handlerMap.size());
    }

    public ITaskHandler getHandler(String handlerName) {
        if (handlerName == null || handlerName.trim().isEmpty()) {
            return null;
        }

        ITaskHandler handler = handlerMap.get(handlerName);
        if (handler != null) {
            return handler;
        }

        try {
            Class<?> clazz = Class.forName(handlerName);
            if (ITaskHandler.class.isAssignableFrom(clazz)) {
                handler = (ITaskHandler) clazz.getDeclaredConstructor().newInstance();
                handlerMap.put(handlerName, handler);
                log.info("Loaded task handler by class: {}", handlerName);
                return handler;
            }
        } catch (Exception e) {
            log.warn("Cannot load task handler by class: {}", handlerName, e);
        }

        return null;
    }

    public void registerHandler(String name, ITaskHandler handler) {
        handlerMap.put(name, handler);
        log.info("Manually registered task handler: {}", name);
    }
}
