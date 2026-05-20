package com.configcenter.common.repository;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

public abstract class InMemoryRepository<T, ID> {

    protected final Map<ID, T> storage = new ConcurrentHashMap<>();

    public T save(ID id, T entity) {
        storage.put(id, entity);
        return entity;
    }

    public Optional<T> findById(ID id) {
        return Optional.ofNullable(storage.get(id));
    }

    public List<T> findAll() {
        return new ArrayList<>(storage.values());
    }

    public void deleteById(ID id) {
        storage.remove(id);
    }

    public boolean existsById(ID id) {
        return storage.containsKey(id);
    }

    public int count() {
        return storage.size();
    }

    public void clear() {
        storage.clear();
    }
}
