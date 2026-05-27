package com.platform.points.controller;

import com.platform.points.entity.PointsLevelConfig;
import com.platform.points.service.UserLevelService;
import com.platform.points.utils.Result;
import com.platform.points.vo.UserLevelVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/level")
public class UserLevelController {

    @Autowired
    private UserLevelService userLevelService;

    @GetMapping("/user/{userId}")
    public Result<UserLevelVO> getUserLevel(@PathVariable Long userId) {
        return Result.success(userLevelService.getUserLevel(userId));
    }

    @GetMapping("/configs")
    public Result<List<PointsLevelConfig>> getAllLevelConfigs() {
        return Result.success(userLevelService.getAllLevelConfigs());
    }

    @PostMapping("/init/{userId}")
    public Result<Void> initUserLevel(@PathVariable Long userId) {
        userLevelService.initUserLevel(userId);
        return Result.success();
    }
}
