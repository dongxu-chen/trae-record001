package com.apigateway.mock.grpc;

import com.apigateway.grpc.order.*;
import com.apigateway.mock.common.MockService;
import com.apigateway.mock.entity.Order;
import com.apigateway.mock.entity.OrderItem;
import com.apigateway.mock.store.OrderStore;
import io.grpc.stub.StreamObserver;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class OrderServiceImpl extends OrderServiceGrpc.OrderServiceImplBase {

    private final OrderStore orderStore;
    private final MockService mockService;
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Override
    public void getOrder(GetOrderRequest request, StreamObserver<OrderResponse> responseObserver) {
        log.info("gRPC查询订单: orderId={}", request.getOrderId());
        mockService.simulate();

        Order order = orderStore.findById(request.getOrderId());
        if (order == null) {
            responseObserver.onError(new RuntimeException("订单不存在"));
            return;
        }

        OrderResponse response = convertToOrderResponse(order);
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void listOrders(ListOrdersRequest request, StreamObserver<ListOrdersResponse> responseObserver) {
        log.info("gRPC查询订单列表: userId={}, page={}, size={}",
                request.getUserId(), request.getPage(), request.getSize());
        mockService.simulate();

        List<Order> orders;
        if (request.getUserId() > 0) {
            orders = new ArrayList<>(orderStore.findByUserId(request.getUserId()));
        } else {
            orders = new ArrayList<>(orderStore.findAll());
        }

        orders.sort(Comparator.comparing(Order::getCreatedAt).reversed());

        int page = request.getPage();
        int size = request.getSize();
        int start = (page - 1) * size;
        int end = Math.min(start + size, orders.size());
        List<Order> pageOrders;
        if (start >= orders.size()) {
            pageOrders = new ArrayList<>();
        } else {
            pageOrders = orders.subList(start, end);
        }

        List<OrderResponse> orderResponses = pageOrders.stream()
                .map(this::convertToOrderResponse)
                .toList();

        ListOrdersResponse response = ListOrdersResponse.newBuilder()
                .addAllOrders(orderResponses)
                .setTotal(orders.size())
                .setPage(page)
                .setSize(size)
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void createOrder(CreateOrderRequest request, StreamObserver<OrderResponse> responseObserver) {
        log.info("gRPC创建订单: userId={}", request.getUserId());
        mockService.simulate();

        List<OrderItem> items = request.getItemsList().stream()
                .map(protoItem -> OrderItem.builder()
                        .productId(protoItem.getProductId())
                        .productName(protoItem.getProductName())
                        .quantity(protoItem.getQuantity())
                        .price(protoItem.getPrice())
                        .build())
                .toList();

        Order order = Order.builder()
                .userId(request.getUserId())
                .items(items)
                .address(request.getAddress())
                .status("待支付")
                .build();

        Order saved = orderStore.save(order);
        OrderResponse response = convertToOrderResponse(saved);
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void updateOrderStatus(UpdateOrderStatusRequest request, StreamObserver<OrderResponse> responseObserver) {
        log.info("gRPC更新订单状态: orderId={}, status={}", request.getOrderId(), request.getStatus());
        mockService.simulate();

        Order order = orderStore.findById(request.getOrderId());
        if (order == null) {
            responseObserver.onError(new RuntimeException("订单不存在"));
            return;
        }

        order.setStatus(request.getStatus());
        Order saved = orderStore.save(order);
        OrderResponse response = convertToOrderResponse(saved);
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    private OrderResponse convertToOrderResponse(Order order) {
        List<com.apigateway.grpc.order.OrderItem> protoItems = new ArrayList<>();
        if (order.getItems() != null) {
            protoItems = order.getItems().stream()
                    .map(item -> com.apigateway.grpc.order.OrderItem.newBuilder()
                            .setProductId(item.getProductId())
                            .setProductName(item.getProductName())
                            .setQuantity(item.getQuantity())
                            .setPrice(item.getPrice())
                            .build())
                    .toList();
        }

        return OrderResponse.newBuilder()
                .setOrderId(order.getOrderId())
                .setUserId(order.getUserId())
                .addAllItems(protoItems)
                .setTotalAmount(order.getTotalAmount() != null ? order.getTotalAmount() : 0.0)
                .setStatus(order.getStatus() != null ? order.getStatus() : "")
                .setAddress(order.getAddress() != null ? order.getAddress() : "")
                .setCreatedAt(order.getCreatedAt() != null ? order.getCreatedAt().format(FORMATTER) : "")
                .setUpdatedAt(order.getUpdatedAt() != null ? order.getUpdatedAt().format(FORMATTER) : "")
                .build();
    }
}
