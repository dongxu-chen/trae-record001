package com.homestay.controller;

import com.homestay.common.Result;
import com.homestay.dto.LoginDTO;
import com.homestay.dto.RegisterDTO;
import com.homestay.dto.HostApplyDTO;
import com.homestay.entity.User;
import com.homestay.service.UserService;
import com.homestay.vo.LoginVO;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/user")
public class UserController {

    @Autowired
    private UserService userService;

    @PostMapping("/login")
    public Result<LoginVO> login(@Valid @RequestBody LoginDTO dto) {
        return Result.success(userService.login(dto));
    }

    @PostMapping("/register")
    public Result<Void> register(@Valid @RequestBody RegisterDTO dto) {
        userService.register(dto);
        return Result.success();
    }

    @PostMapping("/host/apply")
    public Result<Void> applyHost(@Valid @RequestBody HostApplyDTO dto) {
        userService.applyHost(dto);
        return Result.success();
    }

    @PostMapping("/host/audit")
    public Result<Void> auditHost(@RequestParam Long userId, @RequestParam Integer status, @RequestParam(required = false) String rejectReason) {
        userService.auditHost(userId, status, rejectReason);
        return Result.success();
    }

    @GetMapping("/info")
    public Result<User> getUserInfo() {
        return Result.success(userService.getUserInfo());
    }

    @PostMapping("/logout")
    public Result<Void> logout() {
        userService.logout();
        return Result.success();
    }
}
