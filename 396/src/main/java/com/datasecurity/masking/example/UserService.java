package com.datasecurity.masking.example;

import com.datasecurity.masking.annotation.DataMasking;
import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.access.UserContextHolder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class UserService {

    @DataMasking(databaseId = "default")
    public List<Map<String, Object>> findAllUsers() {
        List<Map<String, Object>> users = new ArrayList<>();

        users.add(Map.of(
                "id", 1L,
                "name", "张三",
                "id_card", "110101199001011234",
                "phone", "13800138000",
                "bank_card", "6222021234567890123",
                "email", "zhangsan@example.com",
                "address", "北京市朝阳区建国路88号"
        ));

        users.add(Map.of(
                "id", 2L,
                "name", "李四",
                "id_card", "310101199203045678",
                "phone", "13900139000",
                "bank_card", "6228489876543210987",
                "email", "lisi@example.com",
                "address", "上海市浦东新区陆家嘴环路1000号"
        ));

        users.add(Map.of(
                "id", 3L,
                "name", "王五",
                "id_card", "440101198512159012",
                "phone", "13700137000",
                "bank_card", "6217001122334455667",
                "email", "wangwu@example.com",
                "address", "广州市天河区珠江新城华夏路8号"
        ));

        return users;
    }

    @DataMasking(databaseId = "default")
    public Map<String, Object> findUserById(Long id) {
        return Map.of(
                "id", id,
                "name", "张三",
                "id_card", "110101199001011234",
                "phone", "13800138000",
                "bank_card", "6222021234567890123",
                "email", "zhangsan@example.com",
                "address", "北京市朝阳区建国路88号"
        );
    }

    public void setCurrentUserAsAdmin() {
        UserContext admin = UserContext.builder()
                .userId("admin001")
                .username("admin")
                .roles(java.util.Set.of("ADMIN"))
                .permissions(java.util.Set.of("VIEW_SENSITIVE_DATA"))
                .needMasking(false)
                .build();
        UserContextHolder.set(admin);
        log.info("Set current user as ADMIN");
    }

    public void setCurrentUserAsViewer() {
        UserContext viewer = UserContext.builder()
                .userId("viewer001")
                .username("viewer")
                .roles(java.util.Set.of("VIEWER"))
                .permissions(java.util.Set.of())
                .needMasking(true)
                .build();
        UserContextHolder.set(viewer);
        log.info("Set current user as VIEWER");
    }

    public void setCurrentUserAsOperator() {
        UserContext operator = UserContext.builder()
                .userId("operator001")
                .username("operator")
                .roles(java.util.Set.of("OPERATOR"))
                .permissions(java.util.Set.of())
                .needMasking(true)
                .build();
        UserContextHolder.set(operator);
        log.info("Set current user as OPERATOR");
    }

    public void clearUserContext() {
        UserContextHolder.clear();
        log.info("Cleared user context");
    }
}
