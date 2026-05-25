package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.entity.RepairType;
import com.property.repair.service.RepairTypeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/repair-type")
@CrossOrigin
public class RepairTypeController {

    @Autowired
    private RepairTypeService repairTypeService;

    @GetMapping("/list")
    public Result<List<RepairType>> list() {
        return Result.success(repairTypeService.getAllTypes());
    }

    @GetMapping("/{id}")
    public Result<RepairType> getById(@PathVariable Long id) {
        return Result.success(repairTypeService.getById(id));
    }
}
