package com.apiversion.business.v2.repository;

import org.springframework.stereotype.Component;

import java.util.Collection;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class InMemoryRepository<T> {

    private final Map<Long, T> storage = new ConcurrentHashMap<>();

    public void save(Long id, T entity) {
        storage.put(id, entity);
    }

    public T findById(Long id) {
        return storage.get(id);
    }

    public Collection<T> findAll() {
        return storage.values();
    }

    public void delete(Long id) {
        storage.remove(id);
    }

    public boolean exists(Long id) {
        return storage.containsKey(id);
    }
}
