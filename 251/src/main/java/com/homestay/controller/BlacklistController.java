package com.homestay.controller;

import com.homestay.common.Result;
import com.homestay.entity.Blacklist;
import com.homestay.service.BlacklistService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/blacklist")
public class BlacklistController {

    @Autowired
    private BlacklistService blacklistService;

    @GetMapping("/check")
    public Result<Boolean> checkBlacklist() {
        Long userId = com.homestay.common.UserContext.getUserId();
        return Result.success(blacklistService.isUserBlacklisted(userId));
    }

    @GetMapping("/my")
    public Result<Blacklist> getMyBlacklist() {
        Long userId = com.homestay.common.UserContext.getUserId();
        return Result.success(blacklistService.getActiveBlacklist(userId));
    }

    @PostMapping("/add")
    public Result<Void> addToBlacklist(@RequestParam Long userId,
                                        @RequestParam Integer reason,
                                        @RequestParam(required = false) String remark,
                                        @RequestParam(required = false) Integer days) {
        blacklistService.addToBlacklist(userId, reason, remark, days);
        return Result.success();
    }

    @PostMapping("/remove/{id}")
    public Result<Void> removeFromBlacklist(@PathVariable Long id) {
        blacklistService.removeFromBlacklist(id);
        return Result.success();
    }

    @GetMapping("/list")
    public Result<List<Blacklist>> getBlacklist(@RequestParam(required = false) Integer status,
                                                 @RequestParam(defaultValue = "1") int pageNum,
                                                 @RequestParam(defaultValue = "10") int pageSize) {
        return Result.success(blacklistService.getBlacklist(status, pageNum, pageSize));
    }
}
