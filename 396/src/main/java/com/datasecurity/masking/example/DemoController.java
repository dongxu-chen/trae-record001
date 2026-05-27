package com.datasecurity.masking.example;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/demo")
public class DemoController {

    @Autowired
    private UserService userService;

    @GetMapping("/users")
    public ResponseEntity<List<Map<String, Object>>> getUsers() {
        return ResponseEntity.ok(userService.findAllUsers());
    }

    @GetMapping("/users/{id}")
    public ResponseEntity<Map<String, Object>> getUserById(@PathVariable Long id) {
        return ResponseEntity.ok(userService.findUserById(id));
    }

    @PostMapping("/user/role/admin")
    public ResponseEntity<String> setAdminRole() {
        userService.setCurrentUserAsAdmin();
        return ResponseEntity.ok("User role set to ADMIN");
    }

    @PostMapping("/user/role/viewer")
    public ResponseEntity<String> setViewerRole() {
        userService.setCurrentUserAsViewer();
        return ResponseEntity.ok("User role set to VIEWER");
    }

    @PostMapping("/user/role/operator")
    public ResponseEntity<String> setOperatorRole() {
        userService.setCurrentUserAsOperator();
        return ResponseEntity.ok("User role set to OPERATOR");
    }

    @PostMapping("/user/clear")
    public ResponseEntity<String> clearUser() {
        userService.clearUserContext();
        return ResponseEntity.ok("User context cleared");
    }
}
