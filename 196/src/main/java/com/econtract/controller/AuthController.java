package com.econtract.controller;

import com.econtract.common.Result;
import com.econtract.dto.LoginDTO;
import com.econtract.dto.RegisterDTO;
import com.econtract.security.UserContext;
import com.econtract.service.UserService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.Map;

@RestController
@RequestMapping("/auth")
public class AuthController {

    @Resource
    private UserService userService;

    @PostMapping("/login")
    public Result<Map<String, Object>> login(@Validated @RequestBody LoginDTO loginDTO) {
        return Result.success(userService.login(loginDTO));
    }

    @PostMapping("/register")
    public Result<Void> register(@Validated @RequestBody RegisterDTO registerDTO) {
        userService.register(registerDTO);
        return Result.success();
    }

    @GetMapping("/info")
    public Result<?> getUserInfo() {
        Long userId = UserContext.getCurrentUserId();
        return Result.success(userService.getUserInfo(userId));
    }
}
