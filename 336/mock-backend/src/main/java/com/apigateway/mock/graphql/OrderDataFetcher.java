package com.apigateway.mock.graphql;

import com.apigateway.mock.common.MockService;
import com.apigateway.mock.entity.Order;
import com.apigateway.mock.entity.OrderItem;
import com.apigateway.mock.store.OrderStore;
import graphql.schema.DataFetcher;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class OrderDataFetcher {

    private final OrderStore orderStore;
    private final MockService mockService;

    public DataFetcher<Order> getOrderById() {
        return env -> {
            String orderId = env.getArgument("orderId");
            log.info("GraphQL查询订单: orderId={}", orderId);
            mockService.simulate();
            return orderStore.findById(orderId);
        };
    }

    public DataFetcher<List<Order>> listOrders() {
        return env -> {
            Long userId = env.getArgumentOrDefault("userId", null);
            int page = env.getArgumentOrDefault("page", 1);
            int size = env.getArgumentOrDefault("size", 10);
            log.info("GraphQL查询订单列表: userId={}, page={}, size={}", userId, page, size);
            mockService.simulate();

            List<Order> orders;
            if (userId != null && userId > 0) {
                orders = new ArrayList<>(orderStore.findByUserId(userId));
            } else {
                orders = new ArrayList<>(orderStore.findAll());
            }

            orders.sort(Comparator.comparing(Order::getCreatedAt).reversed());

            int start = (page - 1) * size;
            int end = Math.min(start + size, orders.size());
            if (start >= orders.size()) {
                return new ArrayList<>();
            }
            return orders.subList(start, end);
        };
    }

    public DataFetcher<Order> createOrder() {
        return env -> {
            Map<String, Object> input = env.getArgument("input");
            log.info("GraphQL创建订单: input={}", input);
            mockService.simulate();

            List<Map<String, Object>> itemsInput = (List<Map<String, Object>>) input.get("items");
            List<OrderItem> items = new ArrayList<>();
            if (itemsInput != null) {
                for (Map<String, Object> itemInput : itemsInput) {
                    OrderItem item = OrderItem.builder()
                            .productId((String) itemInput.get("productId"))
                            .productName((String) itemInput.get("productName"))
                            .quantity(itemInput.get("quantity") != null ? ((Number) itemInput.get("quantity")).intValue() : 1)
                            .price(itemInput.get("price") != null ? ((Number) itemInput.get("price")).doubleValue() : 0.0)
                            .build();
                    items.add(item);
                }
            }

            Order order = Order.builder()
                    .userId(input.get("userId") != null ? ((Number) input.get("userId")).longValue() : null)
                    .items(items)
                    .address((String) input.get("address"))
                    .status("待支付")
                    .build();

            return orderStore.save(order);
        };
    }

    public DataFetcher<Order> updateOrderStatus() {
        return env -> {
            String orderId = env.getArgument("orderId");
            String status = env.getArgument("status");
            log.info("GraphQL更新订单状态: orderId={}, status={}", orderId, status);
            mockService.simulate();

            Order order = orderStore.findById(orderId);
            if (order == null) {
                throw new RuntimeException("订单不存在");
            }

            order.setStatus(status);
            return orderStore.save(order);
        };
    }

    public DataFetcher<Long> orderCount() {
        return env -> {
            Long userId = env.getArgumentOrDefault("userId", null);
            log.info("GraphQL统计订单数量: userId={}", userId);
            mockService.simulate();

            if (userId != null && userId > 0) {
                return (long) orderStore.findByUserId(userId).size();
            }
            return orderStore.count();
        };
    }
}
