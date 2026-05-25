package com.apigateway.mock.store;

import com.apigateway.mock.entity.User;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Collection;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Component
public class UserStore {

    private final ConcurrentHashMap<Long, User> userMap = new ConcurrentHashMap<>();
    private final AtomicLong idGenerator = new AtomicLong(1);

    public UserStore() {
        initMockData();
    }

    private void initMockData() {
        LocalDateTime now = LocalDateTime.now();
        for (int i = 1; i <= 10; i++) {
            User user = User.builder()
                    .id(idGenerator.getAndIncrement())
                    .name("用户" + i)
                    .email("user" + i + "@example.com")
                    .age(20 + i)
                    .createdAt(now)
                    .updatedAt(now)
                    .build();
            userMap.put(user.getId(), user);
        }
        log.info("用户模拟数据初始化完成，共{}条", userMap.size());
    }

    public User save(User user) {
        if (user.getId() == null) {
            user.setId(idGenerator.getAndIncrement());
        }
        LocalDateTime now = LocalDateTime.now();
        if (user.getCreatedAt() == null) {
            user.setCreatedAt(now);
        }
        user.setUpdatedAt(now);
        userMap.put(user.getId(), user);
        return user;
    }

    public User findById(Long id) {
        return userMap.get(id);
    }

    public Collection<User> findAll() {
        return userMap.values();
    }

    public boolean deleteById(Long id) {
        return userMap.remove(id) != null;
    }

    public boolean existsById(Long id) {
        return userMap.containsKey(id);
    }

    public long count() {
        return userMap.size();
    }
}
