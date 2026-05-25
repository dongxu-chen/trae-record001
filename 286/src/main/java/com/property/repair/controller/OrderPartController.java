package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.dto.OrderPartDTO;
import com.property.repair.entity.OrderPart;
import com.property.repair.service.OrderPartService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/order-part")
@CrossOrigin
public class OrderPartController {

    @Autowired
    private OrderPartService orderPartService;

    @PostMapping("/add")
    public Result<OrderPart> addPart(@Validated @RequestBody OrderPartDTO dto) {
        try {
            OrderPart orderPart = orderPartService.addPartToOrder(dto);
            return Result.success(orderPart);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/batch/{orderId}")
    public Result<List<OrderPart>> addParts(
            @PathVariable Long orderId,
            @RequestBody List<OrderPartDTO> parts,
            @RequestParam Long operatorId,
            @RequestParam String operatorName) {
        try {
            List<OrderPart> result = orderPartService.addPartsToOrder(
                orderId, parts, operatorId, operatorName);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    public Result<Void> removePart(
            @PathVariable Long id,
            @RequestParam Long operatorId,
            @RequestParam String operatorName) {
        try {
            boolean removed = orderPartService.removePartFromOrder(id, operatorId, operatorName);
            if (removed) {
                return Result.success();
            } else {
                return Result.error("删除失败");
            }
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/confirm/{orderId}")
    public Result<Void> confirmUsage(
            @PathVariable Long orderId,
            @RequestParam Long operatorId,
            @RequestParam String operatorName) {
        try {
            orderPartService.confirmPartsUsage(orderId, operatorId, operatorName);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/order/{orderId}")
    public Result<List<OrderPart>> getOrderParts(@PathVariable Long orderId) {
        return Result.success(orderPartService.getOrderParts(orderId));
    }
}
