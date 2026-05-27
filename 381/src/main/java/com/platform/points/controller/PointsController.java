package com.platform.points.controller;

import com.platform.points.dto.PointsDeductDTO;
import com.platform.points.dto.PointsGrantDTO;
import com.platform.points.dto.PointsRecordQueryDTO;
import com.platform.points.service.PointsService;
import com.platform.points.utils.Result;
import com.platform.points.vo.PointsRecordVO;
import com.platform.points.vo.UserPointsVO;
import com.baomidou.mybatisplus.core.metadata.IPage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/points")
public class PointsController {

    @Autowired
    private PointsService pointsService;

    @GetMapping("/{userId}")
    public Result<UserPointsVO> getUserPoints(@PathVariable Long userId) {
        return Result.success(pointsService.getUserPoints(userId));
    }

    @PostMapping("/grant")
    public Result<Void> grantPoints(@RequestBody @Validated PointsGrantDTO dto) {
        pointsService.grantPoints(dto);
        return Result.success();
    }

    @PostMapping("/deduct")
    public Result<Void> deductPoints(@RequestBody @Validated PointsDeductDTO dto) {
        pointsService.deductPoints(dto);
        return Result.success();
    }

    @PostMapping("/records")
    public Result<IPage<PointsRecordVO>> queryRecords(@RequestBody @Validated PointsRecordQueryDTO dto) {
        return Result.success(pointsService.queryRecords(dto));
    }
}
