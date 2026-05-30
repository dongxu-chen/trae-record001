package com.apiversion.business.v1.controller;

import com.apiversion.business.v1.entity.User;
import com.apiversion.business.v1.storage.InMemoryStorage;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Collection;

@RestController
@RequestMapping("/users")
@Tag(name = "用户管理V1", description = "用户CRUD接口V1版本")
public class UserController {

    private final InMemoryStorage storage;

    public UserController(InMemoryStorage storage) {
        this.storage = storage;
    }

    @PostMapping
    @Operation(summary = "创建用户V1", description = "创建一个新用户")
    public ResponseEntity<User> createUser(@RequestBody User user) {
        user.setId(storage.generateUserId());
        storage.saveUser(user);
        return ResponseEntity.ok(user);
    }

    @GetMapping("/{id}")
    @Operation(summary = "查询用户V1", description = "根据ID查询用户信息")
    public ResponseEntity<User> getUserById(@Parameter(description = "用户ID") @PathVariable Long id) {
        User user = storage.getUser(id);
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(user);
    }

    @GetMapping
    @Operation(summary = "查询所有用户V1", description = "查询所有用户列表")
    public ResponseEntity<Collection<User>> getAllUsers() {
        return ResponseEntity.ok(storage.getAllUsers());
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新用户V1", description = "根据ID更新用户信息")
    public ResponseEntity<User> updateUser(@Parameter(description = "用户ID") @PathVariable Long id, @RequestBody User user) {
        if (!storage.existsUser(id)) {
            return ResponseEntity.notFound().build();
        }
        user.setId(id);
        storage.saveUser(user);
        return ResponseEntity.ok(user);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除用户V1", description = "根据ID删除用户")
    public ResponseEntity<Void> deleteUser(@Parameter(description = "用户ID") @PathVariable Long id) {
        if (!storage.existsUser(id)) {
            return ResponseEntity.notFound().build();
        }
        storage.deleteUser(id);
        return ResponseEntity.noContent().build();
    }
}
