package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.dto.OrderCompleteDTO;
import com.property.repair.dto.RepairSubmitDTO;
import com.property.repair.dto.WorkerAssignDTO;
import com.property.repair.entity.RepairOrder;
import com.property.repair.service.RepairOrderService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/repair-order")
@CrossOrigin
public class RepairOrderController {

    @Autowired
    private RepairOrderService repairOrderService;

    @PostMapping("/submit")
    public Result<RepairOrder> submit(@Validated @RequestBody RepairSubmitDTO dto) {
        try {
            RepairOrder order = repairOrderService.submitRepair(dto);
            return Result.success(order);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/accept/{orderId}/{workerId}")
    public Result<RepairOrder> accept(@PathVariable Long orderId, @PathVariable Long workerId) {
        try {
            RepairOrder order = repairOrderService.acceptOrder(orderId, workerId);
            return Result.success(order);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/complete")
    public Result<RepairOrder> complete(@Validated @RequestBody OrderCompleteDTO dto) {
        try {
            RepairOrder order = repairOrderService.completeOrder(dto);
            return Result.success(order);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/assign/{operatorId}")
    public Result<RepairOrder> assign(@Validated @RequestBody WorkerAssignDTO dto, 
                                       @PathVariable Long operatorId) {
        try {
            RepairOrder order = repairOrderService.manualAssign(dto.getOrderId(), dto.getWorkerId(), operatorId);
            return Result.success(order);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}")
    public Result<RepairOrder> getById(@PathVariable Long id) {
        return Result.success(repairOrderService.getById(id));
    }

    @GetMapping("/no/{orderNo}")
    public Result<RepairOrder> getByOrderNo(@PathVariable String orderNo) {
        return Result.success(repairOrderService.getByOrderNo(orderNo));
    }

    @GetMapping("/owner/{ownerId}")
    public Result<List<RepairOrder>> getOwnerOrders(@PathVariable Long ownerId) {
        return Result.success(repairOrderService.getOwnerOrders(ownerId));
    }

    @GetMapping("/worker/{workerId}")
    public Result<List<RepairOrder>> getWorkerOrders(@PathVariable Long workerId) {
        return Result.success(repairOrderService.getWorkerOrders(workerId));
    }

    @GetMapping("/pending")
    public Result<List<RepairOrder>> getPendingOrders() {
        return Result.success(repairOrderService.getPendingOrders());
    }

    @GetMapping("/list")
    public Result<List<RepairOrder>> list() {
        return Result.success(repairOrderService.getAllOrders());
    }
}
