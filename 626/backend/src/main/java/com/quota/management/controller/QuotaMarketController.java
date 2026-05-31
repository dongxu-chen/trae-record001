package com.quota.management.controller;

import com.quota.management.common.Result;
import com.quota.management.entity.QuotaMarketOrder;
import com.quota.management.entity.QuotaTrade;
import com.quota.management.service.QuotaMarketService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/market")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class QuotaMarketController {

    private final QuotaMarketService quotaMarketService;

    @PostMapping("/sell")
    public Result<QuotaMarketOrder> placeSellOrder(@RequestBody OrderRequest request) {
        try {
            QuotaMarketOrder order = quotaMarketService.placeSellOrder(
                    request.getTenantId(),
                    request.getGranularity(),
                    request.getAmount(),
                    request.getPricePerUnit(),
                    request.getExpireMinutes() != null ? request.getExpireMinutes() : 1440
            );
            return Result.success(order);
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @PostMapping("/buy")
    public Result<QuotaMarketOrder> placeBuyOrder(@RequestBody OrderRequest request) {
        try {
            QuotaMarketOrder order = quotaMarketService.placeBuyOrder(
                    request.getTenantId(),
                    request.getGranularity(),
                    request.getAmount(),
                    request.getPricePerUnit(),
                    request.getExpireMinutes() != null ? request.getExpireMinutes() : 1440
            );
            return Result.success(order);
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @PostMapping("/cancel/{orderId}")
    public Result<Void> cancelOrder(@PathVariable String orderId) {
        try {
            quotaMarketService.cancelOrder(orderId);
            return Result.success(null);
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @GetMapping("/order/{orderId}")
    public Result<QuotaMarketOrder> getOrder(@PathVariable String orderId) {
        QuotaMarketOrder order = quotaMarketService.getOrder(orderId);
        if (order == null) {
            return Result.error(404, "Order not found");
        }
        return Result.success(order);
    }

    @GetMapping("/orders/{tenantId}")
    public Result<List<QuotaMarketOrder>> getMyOrders(@PathVariable String tenantId) {
        List<QuotaMarketOrder> orders = quotaMarketService.getMyOrders(tenantId);
        return Result.success(orders);
    }

    @GetMapping("/orderbook/{granularity}/sell")
    public Result<List<QuotaMarketOrder>> getSellOrderBook(@PathVariable String granularity) {
        List<QuotaMarketOrder> orders = quotaMarketService.getOrderBook(granularity, QuotaMarketOrder.OrderType.SELL);
        return Result.success(orders);
    }

    @GetMapping("/orderbook/{granularity}/buy")
    public Result<List<QuotaMarketOrder>> getBuyOrderBook(@PathVariable String granularity) {
        List<QuotaMarketOrder> orders = quotaMarketService.getOrderBook(granularity, QuotaMarketOrder.OrderType.BUY);
        return Result.success(orders);
    }

    @GetMapping("/trades/{granularity}")
    public Result<List<QuotaTrade>> getRecentTrades(@PathVariable String granularity,
                                                     @RequestParam(defaultValue = "50") int limit) {
        List<QuotaTrade> trades = quotaMarketService.getRecentTrades(granularity, limit);
        return Result.success(trades);
    }

    @GetMapping("/stats/{granularity}")
    public Result<Map<String, Object>> getMarketStats(@PathVariable String granularity) {
        Map<String, Object> stats = quotaMarketService.getMarketStats(granularity);
        return Result.success(stats);
    }

    @Data
    public static class OrderRequest {
        private String tenantId;
        private String granularity;
        private long amount;
        private double pricePerUnit;
        private Long expireMinutes;
    }
}
