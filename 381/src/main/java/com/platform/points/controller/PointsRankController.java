package com.platform.points.controller;

import com.platform.points.service.PointsRankService;
import com.platform.points.utils.Result;
import com.platform.points.vo.PointsRankVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/rank")
public class PointsRankController {

    @Autowired
    private PointsRankService pointsRankService;

    @GetMapping("/top")
    public Result<List<PointsRankVO>> getTopRank(@RequestParam(defaultValue = "100") int size) {
        return Result.success(pointsRankService.getTopRank(size));
    }

    @GetMapping("/user/{userId}")
    public Result<PointsRankVO> getUserRank(@PathVariable Long userId) {
        return Result.success(pointsRankService.getUserRank(userId));
    }
}
