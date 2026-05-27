package com.sample.controller;

import com.sample.dto.UserRequest;
import com.sample.dto.UserResponse;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping
    public List<UserResponse> getAllUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword) {
        return new ArrayList<>();
    }

    @GetMapping("/{id}")
    public UserResponse getUserById(@PathVariable Long id) {
        return new UserResponse();
    }

    @PostMapping
    public UserResponse createUser(@RequestBody UserRequest request) {
        return new UserResponse();
    }

    @PutMapping("/{id}")
    public UserResponse updateUser(@PathVariable Long id, @RequestBody UserRequest request) {
        return new UserResponse();
    }

    @DeleteMapping("/{id}")
    public void deleteUser(@PathVariable Long id) {
    }
}