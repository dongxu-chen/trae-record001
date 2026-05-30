package com.apiversion.business.v2.controller;

import com.apiversion.business.v2.entity.User;
import com.apiversion.business.v2.repository.InMemoryRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping("/users")
@RequiredArgsConstructor
@Tag(name = "用户管理V2", description = "用户CRUD操作V2版本")
public class UserController {

    private final InMemoryRepository<User> userRepository;

    @PostMapping
    @Operation(summary = "创建用户V2", description = "创建新用户，包含age、address字段")
    public User createUser(@RequestBody User user) {
        user.setId(System.currentTimeMillis());
        user.setCreateTime(LocalDateTime.now());
        user.setUpdateTime(LocalDateTime.now());
        userRepository.save(user.getId(), user);
        return user;
    }

    @GetMapping("/{id}")
    @Operation(summary = "根据ID查询用户V2", description = "根据用户ID查询用户信息")
    public User getUserById(@PathVariable @Parameter(description = "用户ID") Long id) {
        return userRepository.findById(id);
    }

    @GetMapping("/email/{email}")
    @Operation(summary = "根据邮箱查询用户V2", description = "根据用户邮箱查询用户信息（V2新增接口）")
    public User getUserByEmail(@PathVariable @Parameter(description = "用户邮箱") String email) {
        return userRepository.findAll().stream()
                .filter(user -> email.equals(user.getEmail()))
                .findFirst()
                .orElse(null);
    }

    @GetMapping
    @Operation(summary = "查询所有用户V2", description = "查询所有用户列表")
    public List<User> getAllUsers() {
        return new ArrayList<>(userRepository.findAll());
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新用户V2", description = "更新用户信息，包含age、address字段")
    public User updateUser(@PathVariable Long id, @RequestBody User user) {
        User existUser = userRepository.findById(id);
        if (existUser != null) {
            existUser.setUsername(user.getUsername());
            existUser.setEmail(user.getEmail());
            existUser.setPhone(user.getPhone());
            existUser.setAge(user.getAge());
            existUser.setAddress(user.getAddress());
            existUser.setUpdateTime(LocalDateTime.now());
            userRepository.save(id, existUser);
            return existUser;
        }
        return null;
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除用户V2", description = "根据ID删除用户")
    public boolean deleteUser(@PathVariable Long id) {
        userRepository.delete(id);
        return true;
    }
}
