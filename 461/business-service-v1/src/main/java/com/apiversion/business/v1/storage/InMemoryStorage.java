package com.apiversion.business.v1.storage;

import com.apiversion.business.v1.entity.Order;
import com.apiversion.business.v1.entity.User;
import org.springframework.stereotype.Component;

import java.util.Collection;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class InMemoryStorage {

    private final Map<Long, User> userMap = new ConcurrentHashMap<>();
    private final Map<Long, Order> orderMap = new ConcurrentHashMap<>();
    private final AtomicLong userIdGenerator = new AtomicLong(1);
    private final AtomicLong orderIdGenerator = new AtomicLong(1);

    public Long generateUserId() {
        return userIdGenerator.getAndIncrement();
    }

    public Long generateOrderId() {
        return orderIdGenerator.getAndIncrement();
    }

    public void saveUser(User user) {
        userMap.put(user.getId(), user);
    }

    public User getUser(Long id) {
        return userMap.get(id);
    }

    public Collection<User> getAllUsers() {
        return userMap.values();
    }

    public void deleteUser(Long id) {
        userMap.remove(id);
    }

    public boolean existsUser(Long id) {
        return userMap.containsKey(id);
    }

    public void saveOrder(Order order) {
        orderMap.put(order.getId(), order);
    }

    public Order getOrder(Long id) {
        return orderMap.get(id);
    }

    public Collection<Order> getAllOrders() {
        return orderMap.values();
    }

    public void deleteOrder(Long id) {
        orderMap.remove(id);
    }

    public boolean existsOrder(Long id) {
        return orderMap.containsKey(id);
    }
}
