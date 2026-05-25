package com.sms.platform.controller;

import com.sms.platform.common.Result;
import com.sms.platform.entity.SmsMobileLocation;
import com.sms.platform.service.MobileLocationService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/sms/mobile/location")
public class SmsMobileLocationController {

    @Resource
    private MobileLocationService mobileLocationService;

    @PostMapping("/analyze")
    public Result<MobileLocationService.MobileLocationInfo> analyzeMobile(@RequestBody Map<String, String> params) {
        String mobile = params.get("mobile");
        if (mobile == null || mobile.isEmpty()) {
            return Result.error("手机号不能为空");
        }
        return Result.success(mobileLocationService.analyzeMobile(mobile));
    }

    @PostMapping
    public Result<String> addLocation(@RequestBody SmsMobileLocation location) {
        mobileLocationService.addLocation(location);
        return Result.success("添加成功");
    }

    @PostMapping("/batch")
    public Result<String> addLocationBatch(@RequestBody List<SmsMobileLocation> locations) {
        mobileLocationService.addLocationBatch(locations);
        return Result.success("批量添加完成");
    }

    @DeleteMapping("/{id}")
    public Result<String> deleteLocation(@PathVariable Long id) {
        mobileLocationService.deleteLocation(id);
        return Result.success("删除成功");
    }

    @GetMapping("/list")
    public Result<List<SmsMobileLocation>> listLocations(
            @RequestParam(required = false) String province,
            @RequestParam(required = false) Integer operator) {
        return Result.success(mobileLocationService.listLocations(province, operator));
    }

    @GetMapping("/statistics/province")
    public Result<List<Map<String, Object>>> getProvinceStatistics(
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        return Result.success(mobileLocationService.getProvinceStatistics(startDate, endDate));
    }

    @GetMapping("/statistics/operator")
    public Result<List<Map<String, Object>>> getOperatorStatistics(
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        return Result.success(mobileLocationService.getOperatorStatistics(startDate, endDate));
    }

    @GetMapping("/statistics/full")
    public Result<Map<String, Object>> getFullStatistics(
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        return Result.success(mobileLocationService.getFullStatistics(startDate, endDate));
    }

    @PostMapping("/refresh")
    public Result<String> refreshCache() {
        mobileLocationService.refreshCache();
        return Result.success("缓存刷新成功");
    }
}
