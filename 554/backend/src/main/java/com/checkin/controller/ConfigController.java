package com.checkin.controller;

import com.checkin.common.Result;
import com.checkin.entity.CheckinConfig;
import com.checkin.entity.CheckinTreasure;
import com.checkin.service.CheckinConfigService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/config")
public class ConfigController {

    @Autowired
    private CheckinConfigService checkinConfigService;

    @GetMapping("/checkin/{periodType}")
    public Result<List<CheckinConfig>> getCheckinConfigs(@PathVariable String periodType) {
        try {
            List<CheckinConfig> configs = checkinConfigService.getConfigs(periodType);
            return Result.success(configs);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/checkin")
    public Result<CheckinConfig> saveCheckinConfig(@RequestBody CheckinConfig config) {
        try {
            CheckinConfig saved = checkinConfigService.saveConfig(config);
            return Result.success(saved);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/checkin/{id}")
    public Result<Void> deleteCheckinConfig(@PathVariable Long id) {
        try {
            checkinConfigService.deleteConfig(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/treasure/{periodType}")
    public Result<List<CheckinTreasure>> getTreasures(@PathVariable String periodType) {
        try {
            List<CheckinTreasure> treasures = checkinConfigService.getTreasures(periodType);
            return Result.success(treasures);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/treasure")
    public Result<CheckinTreasure> saveTreasure(@RequestBody CheckinTreasure treasure) {
        try {
            CheckinTreasure saved = checkinConfigService.saveTreasure(treasure);
            return Result.success(saved);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/treasure/{id}")
    public Result<Void> deleteTreasure(@PathVariable Long id) {
        try {
            checkinConfigService.deleteTreasure(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
}
