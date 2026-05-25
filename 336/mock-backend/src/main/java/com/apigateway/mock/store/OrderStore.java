package com.apigateway.mock.store;

import com.apigateway.mock.entity.Order;
import com.apigateway.mock.entity.OrderItem;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
public class OrderStore {

    private final ConcurrentHashMap<String, Order> orderMap = new ConcurrentHashMap<>();
    private final AtomicInteger orderCounter = new AtomicInteger(1);
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    public OrderStore() {
        initMockData();
    }

    private void initMockData() {
        LocalDateTime now = LocalDateTime.now();
        for (int i = 1; i <= 15; i++) {
            List<OrderItem> items = new ArrayList<>();
            items.add(OrderItem.builder()
                    .productId("P" + (i * 2 - 1))
                    .productName("商品" + (i * 2 - 1))
                    .quantity(1 + i % 3)
                    .price(10.0 + i * 5.5)
                    .build());
            items.add(OrderItem.builder()
                    .productId("P" + (i * 2))
                    .productName("商品" + (i * 2))
                    .quantity(1)
                    .price(20.0 + i * 3.0)
                    .build());

            double totalAmount = items.stream()
                    .mapToDouble(item -> item.getPrice() * item.getQuantity())
                    .sum();

            String orderId = generateOrderId();
            Order order = Order.builder()
                    .orderId(orderId)
                    .userId((long) ((i % 10) + 1))
                    .items(items)
                    .totalAmount(totalAmount)
                    .status(i % 3 == 0 ? "已完成" : i % 3 == 1 ? "待支付" : "已发货")
                    .address("北京市朝阳区XXX街道XXX号")
                    .createdAt(now.minusHours(i))
                    .updatedAt(now.minusHours(i / 2))
                    .build();
            orderMap.put(order.getOrderId(), order);
        }
        log.info("订单模拟数据初始化完成，共{}条", orderMap.size());
    }

    private String generateOrderId() {
        String datePart = LocalDateTime.now().format(FORMATTER);
        int seq = orderCounter.getAndIncrement();
        return "ORD" + datePart + String.format("%04d", seq);
    }

    public Order save(Order order) {
        if (order.getOrderId() == null || order.getOrderId().isEmpty()) {
            order.setOrderId(generateOrderId());
        }
        LocalDateTime now = LocalDateTime.now();
        if (order.getCreatedAt() == null) {
            order.setCreatedAt(now);
        }
        order.setUpdatedAt(now);
        if (order.getItems() != null) {
            double totalAmount = order.getItems().stream()
                    .mapToDouble(item -> item.getPrice() * item.getQuantity())
                    .sum();
            order.setTotalAmount(totalAmount);
        }
        orderMap.put(order.getOrderId(), order);
        return order;
    }

    public Order findById(String orderId) {
        return orderMap.get(orderId);
    }

    public Collection<Order> findAll() {
        return orderMap.values();
    }

    public List<Order> findByUserId(Long userId) {
        return orderMap.values().stream()
                .filter(order -> userId.equals(order.getUserId()))
                .toList();
    }

    public boolean existsById(String orderId) {
        return orderMap.containsKey(orderId);
    }

    public long count() {
        return orderMap.size();
    }
}
