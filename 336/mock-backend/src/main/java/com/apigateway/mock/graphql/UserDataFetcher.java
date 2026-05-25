package com.apigateway.mock.graphql;

import com.apigateway.mock.common.MockService;
import com.apigateway.mock.entity.User;
import com.apigateway.mock.store.UserStore;
import graphql.schema.DataFetcher;
import graphql.schema.DataFetchingEnvironment;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class UserDataFetcher {

    private final UserStore userStore;
    private final MockService mockService;

    public DataFetcher<User> getUserById() {
        return env -> {
            Long id = env.getArgument("id");
            log.info("GraphQL查询用户: id={}", id);
            mockService.simulate();
            return userStore.findById(id);
        };
    }

    public DataFetcher<List<User>> listUsers() {
        return env -> {
            int page = env.getArgumentOrDefault("page", 1);
            int size = env.getArgumentOrDefault("size", 10);
            log.info("GraphQL查询用户列表: page={}, size={}", page, size);
            mockService.simulate();

            List<User> users = new ArrayList<>(userStore.findAll());
            users.sort(Comparator.comparing(User::getId));

            int start = (page - 1) * size;
            int end = Math.min(start + size, users.size());
            if (start >= users.size()) {
                return new ArrayList<>();
            }
            return users.subList(start, end);
        };
    }

    public DataFetcher<User> createUser() {
        return env -> {
            Map<String, Object> input = env.getArgument("input");
            log.info("GraphQL创建用户: input={}", input);
            mockService.simulate();

            User user = User.builder()
                    .name((String) input.get("name"))
                    .email((String) input.get("email"))
                    .age(input.get("age") != null ? ((Number) input.get("age")).intValue() : null)
                    .build();

            return userStore.save(user);
        };
    }

    public DataFetcher<User> updateUser() {
        return env -> {
            Long id = env.getArgument("id");
            Map<String, Object> input = env.getArgument("input");
            log.info("GraphQL更新用户: id={}, input={}", id, input);
            mockService.simulate();

            if (!userStore.existsById(id)) {
                throw new RuntimeException("用户不存在");
            }

            User user = User.builder()
                    .id(id)
                    .name((String) input.get("name"))
                    .email((String) input.get("email"))
                    .age(input.get("age") != null ? ((Number) input.get("age")).intValue() : null)
                    .build();

            return userStore.save(user);
        };
    }

    public DataFetcher<Boolean> deleteUser() {
        return env -> {
            Long id = env.getArgument("id");
            log.info("GraphQL删除用户: id={}", id);
            mockService.simulate();
            return userStore.deleteById(id);
        };
    }

    public DataFetcher<Long> userCount() {
        return env -> {
            log.info("GraphQL统计用户数量");
            mockService.simulate();
            return userStore.count();
        };
    }
}
