package com.apiversion.business.v1.controller;

import com.apiversion.business.v1.entity.Order;
import com.apiversion.business.v1.storage.InMemoryStorage;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Collection;

@RestController
@RequestMapping("/orders")
@Tag(name = "订单管理V1", description = "订单CRUD接口V1版本")
public class OrderController {

    private final InMemoryStorage storage;

    public OrderController(InMemoryStorage storage) {
        this.storage = storage;
    }

    @PostMapping
    @Operation(summary = "创建订单V1", description = "创建一个新订单")
    public ResponseEntity<Order> createOrder(@RequestBody Order order) {
        order.setId(storage.generateOrderId());
        storage.saveOrder(order);
        return ResponseEntity.ok(order);
    }

    @GetMapping("/{id}")
    @Operation(summary = "查询订单V1", description = "根据ID查询订单信息")
    public ResponseEntity<Order> getOrderById(@Parameter(description = "订单ID") @PathVariable Long id) {
        Order order = storage.getOrder(id);
        if (order == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(order);
    }

    @GetMapping
    @Operation(summary = "查询所有订单V1", description = "查询所有订单列表")
    public ResponseEntity<Collection<Order>> getAllOrders() {
        return ResponseEntity.ok(storage.getAllOrders());
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新订单V1", description = "根据ID更新订单信息")
    public ResponseEntity<Order> updateOrder(@Parameter(description = "订单ID") @PathVariable Long id, @RequestBody Order order) {
        if (!storage.existsOrder(id)) {
            return ResponseEntity.notFound().build();
        }
        order.setId(id);
        storage.saveOrder(order);
        return ResponseEntity.ok(order);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除订单V1", description = "根据ID删除订单")
    public ResponseEntity<Void> deleteOrder(@Parameter(description = "订单ID") @PathVariable Long id) {
        if (!storage.existsOrder(id)) {
            return ResponseEntity.notFound().build();
        }
        storage.deleteOrder(id);
        return ResponseEntity.noContent().build();
    }
}
