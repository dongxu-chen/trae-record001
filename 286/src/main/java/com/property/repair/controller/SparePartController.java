package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.dto.OrderPartDTO;
import com.property.repair.entity.OrderPart;
import com.property.repair.entity.SparePart;
import com.property.repair.entity.StockLog;
import com.property.repair.service.OrderPartService;
import com.property.repair.service.SparePartService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/spare-part")
@CrossOrigin
public class SparePartController {

    @Autowired
    private SparePartService sparePartService;

    @Autowired
    private OrderPartService orderPartService;

    @GetMapping("/list")
    public Result<List<SparePart>> list() {
        return Result.success(sparePartService.getAllParts());
    }

    @GetMapping("/{id}")
    public Result<SparePart> getById(@PathVariable Long id) {
        return Result.success(sparePartService.getById(id));
    }

    @GetMapping("/code/{code}")
    public Result<SparePart> getByCode(@PathVariable String code) {
        return Result.success(sparePartService.getByCode(code));
    }

    @GetMapping("/low-stock")
    public Result<List<SparePart>> getLowStockParts() {
        return Result.success(sparePartService.getLowStockParts());
    }

    @PostMapping("/create")
    public Result<SparePart> create(@RequestBody SparePart part,
                                     @RequestParam Long operatorId,
                                     @RequestParam String operatorName) {
        try {
            SparePart created = sparePartService.createPart(part, operatorId, operatorName);
            return Result.success(created);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/stock-in")
    public Result<SparePart> stockIn(@RequestParam Long partId,
                                      @RequestParam Integer quantity,
                                      @RequestParam Long operatorId,
                                      @RequestParam String operatorName,
                                      @RequestParam(required = false) String remark) {
        try {
            SparePart updated = sparePartService.updateStock(
                partId, quantity, "IN", null, operatorId, operatorName, remark);
            return Result.success(updated);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}/logs")
    public Result<List<StockLog>> getPartLogs(@PathVariable Long id) {
        return Result.success(sparePartService.getPartLogs(id));
    }
}
