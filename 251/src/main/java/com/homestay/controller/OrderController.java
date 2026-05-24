package com.homestay.controller;

import com.homestay.common.Result;
import com.homestay.dto.OrderCreateDTO;
import com.homestay.entity.OrderInfo;
import com.homestay.service.OrderService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/order")
public class OrderController {

    @Autowired
    private OrderService orderService;

    @PostMapping("/create")
    public Result<OrderInfo> createOrder(@Valid @RequestBody OrderCreateDTO dto) {
        return Result.success(orderService.createOrder(dto));
    }

    @PostMapping("/pay/{id}")
    public Result<Void> payOrder(@PathVariable Long id, @RequestParam String payMethod) {
        orderService.payOrder(id, payMethod);
        return Result.success();
    }

    @PostMapping("/cancel/{id}")
    public Result<Void> cancelOrder(@PathVariable Long id) {
        orderService.cancelOrder(id);
        return Result.success();
    }

    @PostMapping("/checkin/{id}")
    public Result<Void> checkIn(@PathVariable Long id) {
        orderService.checkIn(id);
        return Result.success();
    }

    @PostMapping("/checkout/{id}")
    public Result<Void> checkOut(@PathVariable Long id) {
        orderService.checkOut(id);
        return Result.success();
    }

    @GetMapping("/list")
    public Result<List<OrderInfo>> getUserOrders(@RequestParam(required = false) Integer status) {
        return Result.success(orderService.getUserOrders(status));
    }

    @GetMapping("/host/list")
    public Result<List<OrderInfo>> getHostOrders(@RequestParam(required = false) Integer status) {
        return Result.success(orderService.getHostOrders(status));
    }
}
