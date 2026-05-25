package com.ticket.controller;

import com.ticket.common.PageResult;
import com.ticket.common.Result;
import com.ticket.entity.User;
import com.ticket.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @PostMapping
    public Result<User> createUser(@Valid @RequestBody User user) {
        User created = userService.createUser(user);
        return Result.success(created);
    }

    @PutMapping("/{id}")
    public Result<User> updateUser(@PathVariable Long id, @Valid @RequestBody User user) {
        User updated = userService.updateUser(id, user);
        return Result.success(updated);
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteUser(@PathVariable Long id) {
        userService.deleteUser(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<User> getUserById(@PathVariable Long id) {
        User user = userService.getUserById(id);
        return Result.success(user);
    }

    @GetMapping("/username/{username}")
    public Result<User> getUserByUsername(@PathVariable String username) {
        User user = userService.getUserByUsername(username);
        return Result.success(user);
    }

    @GetMapping
    public Result<PageResult<User>> getUserList(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Pageable pageable = PageRequest.of(pageNum - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<User> page = userService.getUserList(pageable);
        return Result.success(PageResult.of(page));
    }

    @GetMapping("/available")
    public Result<List<User>> getAvailableUsers() {
        List<User> users = userService.getAvailableUsers();
        return Result.success(users);
    }

    @GetMapping("/department/{department}")
    public Result<List<User>> getAvailableUsersByDepartment(@PathVariable String department) {
        List<User> users = userService.getAvailableUsersByDepartment(department);
        return Result.success(users);
    }

    @PutMapping("/{id}/toggle")
    public Result<User> toggleStatus(@PathVariable Long id) {
        User user = userService.toggleStatus(id);
        return Result.success(user);
    }
}
