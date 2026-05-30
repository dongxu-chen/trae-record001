package com.apiversion.business.v2.controller;

import com.apiversion.business.v2.entity.Order;
import com.apiversion.business.v2.repository.InMemoryRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping("/orders")
@RequiredArgsConstructor
@Tag(name = "订单管理V2", description = "订单CRUD操作V2版本")
public class OrderController {

    private final InMemoryRepository<Order> orderRepository;

    @PostMapping
    @Operation(summary = "创建订单V2", description = "创建新订单，包含payTime、deliveryTime字段")
    public Order createOrder(@RequestBody Order order) {
        order.setId(System.currentTimeMillis());
        order.setCreateTime(LocalDateTime.now());
        order.setUpdateTime(LocalDateTime.now());
        orderRepository.save(order.getId(), order);
        return order;
    }

    @GetMapping("/{id}")
    @Operation(summary = "根据ID查询订单V2", description = "根据订单ID查询订单信息")
    public Order getOrderById(@PathVariable @Parameter(description = "订单ID") Long id) {
        return orderRepository.findById(id);
    }

    @GetMapping("/orderNo/{orderNo}")
    @Operation(summary = "根据订单编号查询订单V2", description = "根据订单编号查询订单信息（V2新增接口）")
    public Order getOrderByOrderNo(@PathVariable @Parameter(description = "订单编号") String orderNo) {
        return orderRepository.findAll().stream()
                .filter(order -> orderNo.equals(order.getOrderNo()))
                .findFirst()
                .orElse(null);
    }

    @GetMapping
    @Operation(summary = "查询所有订单V2", description = "查询所有订单列表")
    public List<Order> getAllOrders() {
        return new ArrayList<>(orderRepository.findAll());
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新订单V2", description = "更新订单信息，包含payTime、deliveryTime字段")
    public Order updateOrder(@PathVariable Long id, @RequestBody Order order) {
        Order existOrder = orderRepository.findById(id);
        if (existOrder != null) {
            existOrder.setOrderNo(order.getOrderNo());
            existOrder.setUserId(order.getUserId());
            existOrder.setAmount(order.getAmount());
            existOrder.setStatus(order.getStatus());
            existOrder.setPayTime(order.getPayTime());
            existOrder.setDeliveryTime(order.getDeliveryTime());
            existOrder.setUpdateTime(LocalDateTime.now());
            orderRepository.save(id, existOrder);
            return existOrder;
        }
        return null;
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除订单V2", description = "根据ID删除订单")
    public boolean deleteOrder(@PathVariable Long id) {
        orderRepository.delete(id);
        return true;
    }
}
