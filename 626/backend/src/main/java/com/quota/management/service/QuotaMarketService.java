package com.quota.management.service;

import com.quota.management.entity.QuotaMarketOrder;
import com.quota.management.entity.QuotaTrade;
import com.quota.management.entity.QuotaUsage;
import com.quota.management.entity.TenantQuota;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class QuotaMarketService {

    private static final String ORDER_PREFIX = "quota:market:order:";
    private static final String ORDER_SET_KEY = "quota:market:orders:all";
    private static final String TRADE_PREFIX = "quota:market:trade:";
    private static final String TRADE_SET_KEY = "quota:market:trades:all";
    private static final String SELL_ORDERBOOK_PREFIX = "quota:market:orderbook:sell:";
    private static final String BUY_ORDERBOOK_PREFIX = "quota:market:orderbook:buy:";
    private static final String FROZEN_PREFIX = "quota:market:frozen:";
    private static final String MARKET_LOCK = "quota:market:lock";

    private final RedisTemplate<String, Object> redisTemplate;
    private final QuotaManagementService quotaManagementService;
    private final TccTransferService tccTransferService;

    public QuotaMarketOrder placeSellOrder(String tenantId, String granularity, long amount, double pricePerUnit, long expireMinutes) {
        TenantQuota quota = quotaManagementService.getTenantQuota(tenantId);
        if (quota == null) {
            throw new RuntimeException("Tenant not found");
        }

        long available = getAvailableQuota(tenantId, granularity);
        if (available < amount) {
            throw new RuntimeException("Insufficient quota to sell. Available: " + available);
        }

        String lockValue = UUID.randomUUID().toString();
        if (!tryLock(MARKET_LOCK, lockValue, 10)) {
            throw new RuntimeException("Market busy, please try again later");
        }

        try {
            QuotaMarketOrder order = QuotaMarketOrder.builder()
                    .orderId(UUID.randomUUID().toString().replace("-", ""))
                    .orderType(QuotaMarketOrder.OrderType.SELL)
                    .tenantId(tenantId)
                    .tenantName(quota.getTenantName())
                    .granularity(granularity)
                    .totalAmount(amount)
                    .filledAmount(0)
                    .remainingAmount(amount)
                    .pricePerUnit(pricePerUnit)
                    .totalPrice(amount * pricePerUnit)
                    .filledPrice(0)
                    .status(QuotaMarketOrder.OrderStatus.PENDING)
                    .createdAt(LocalDateTime.now())
                    .expiresAt(LocalDateTime.now().plusMinutes(expireMinutes > 0 ? expireMinutes : 1440))
                    .build();

            freezeQuota(tenantId, granularity, amount);

            saveOrder(order);

            addToOrderBook(order);

            matchOrders(granularity);

            log.info("Placed sell order: {} - {} {} @ {}",
                    order.getOrderId(), tenantId, amount, pricePerUnit);

            return order;
        } finally {
            unlock(MARKET_LOCK, lockValue);
        }
    }

    public QuotaMarketOrder placeBuyOrder(String tenantId, String granularity, long amount, double pricePerUnit, long expireMinutes) {
        TenantQuota quota = quotaManagementService.getTenantQuota(tenantId);
        if (quota == null) {
            throw new RuntimeException("Tenant not found");
        }

        String lockValue = UUID.randomUUID().toString();
        if (!tryLock(MARKET_LOCK, lockValue, 10)) {
            throw new RuntimeException("Market busy, please try again later");
        }

        try {
            QuotaMarketOrder order = QuotaMarketOrder.builder()
                    .orderId(UUID.randomUUID().toString().replace("-", ""))
                    .orderType(QuotaMarketOrder.OrderType.BUY)
                    .tenantId(tenantId)
                    .tenantName(quota.getTenantName())
                    .granularity(granularity)
                    .totalAmount(amount)
                    .filledAmount(0)
                    .remainingAmount(amount)
                    .pricePerUnit(pricePerUnit)
                    .totalPrice(amount * pricePerUnit)
                    .filledPrice(0)
                    .status(QuotaMarketOrder.OrderStatus.PENDING)
                    .createdAt(LocalDateTime.now())
                    .expiresAt(LocalDateTime.now().plusMinutes(expireMinutes > 0 ? expireMinutes : 1440))
                    .build();

            saveOrder(order);

            addToOrderBook(order);

            matchOrders(granularity);

            log.info("Placed buy order: {} - {} {} @ {}",
                    order.getOrderId(), tenantId, amount, pricePerUnit);

            return order;
        } finally {
            unlock(MARKET_LOCK, lockValue);
        }
    }

    private void matchOrders(String granularity) {
        String sellKey = SELL_ORDERBOOK_PREFIX + granularity;
        String buyKey = BUY_ORDERBOOK_PREFIX + granularity;

        while (true) {
            Set<Object> sellPrices = redisTemplate.opsForZSet().range(sellKey, 0, 0);
            Set<Object> buyPrices = redisTemplate.opsForZSet().reverseRange(buyKey, 0, 0);

            if (sellPrices == null || sellPrices.isEmpty() || buyPrices == null || buyPrices.isEmpty()) {
                break;
            }

            double bestSellPrice = Double.parseDouble(sellPrices.iterator().next().toString());
            double bestBuyPrice = Double.parseDouble(buyPrices.iterator().next().toString());

            if (bestBuyPrice < bestSellPrice) {
                break;
            }

            Set<Object> sellOrdersAtPrice = redisTemplate.opsForSet().members(sellKey + ":" + bestSellPrice);
            Set<Object> buyOrdersAtPrice = redisTemplate.opsForSet().members(buyKey + ":" + bestBuyPrice);

            if (sellOrdersAtPrice == null || sellOrdersAtPrice.isEmpty() ||
                    buyOrdersAtPrice == null || buyOrdersAtPrice.isEmpty()) {
                redisTemplate.opsForZSet().remove(sellKey, bestSellPrice);
                redisTemplate.opsForZSet().remove(buyKey, bestBuyPrice);
                continue;
            }

            String sellOrderId = sellOrdersAtPrice.iterator().next().toString();
            String buyOrderId = buyOrdersAtPrice.iterator().next().toString();

            executeTrade(sellOrderId, buyOrderId, bestSellPrice);
        }
    }

    private void executeTrade(String sellOrderId, String buyOrderId, double price) {
        QuotaMarketOrder sellOrder = getOrder(sellOrderId);
        QuotaMarketOrder buyOrder = getOrder(buyOrderId);

        if (sellOrder == null || buyOrder == null) {
            return;
        }

        long tradeAmount = Math.min(sellOrder.getRemainingAmount(), buyOrder.getRemainingAmount());
        if (tradeAmount <= 0) {
            return;
        }

        String txId = null;
        try {
            txId = tccTransferService.tryPhase(
                    sellOrder.getTenantId(),
                    buyOrder.getTenantId(),
                    sellOrder.getGranularity(),
                    tradeAmount
            ).getTransactionId();

            tccTransferService.confirmPhase(txId);

            QuotaTrade trade = QuotaTrade.builder()
                    .tradeId(UUID.randomUUID().toString().replace("-", ""))
                    .sellOrderId(sellOrderId)
                    .buyOrderId(buyOrderId)
                    .sellerTenantId(sellOrder.getTenantId())
                    .buyerTenantId(buyOrder.getTenantId())
                    .granularity(sellOrder.getGranularity())
                    .amount(tradeAmount)
                    .pricePerUnit(price)
                    .totalPrice(tradeAmount * price)
                    .tradedAt(LocalDateTime.now())
                    .build();

            saveTrade(trade);

            updateOrderAfterTrade(sellOrder, tradeAmount, tradeAmount * price);
            updateOrderAfterTrade(buyOrder, tradeAmount, tradeAmount * price);

            unfreezeQuota(sellOrder.getTenantId(), sellOrder.getGranularity(), tradeAmount);

            log.info("Trade executed: {} {} {} from {} to {} @ {}",
                    tradeAmount, sellOrder.getGranularity(),
                    sellOrder.getTenantId(), buyOrder.getTenantId(), price);

        } catch (Exception e) {
            if (txId != null) {
                try {
                    tccTransferService.cancelPhase(txId);
                } catch (Exception ex) {
                    log.error("Failed to cancel TCC transaction after trade failure", ex);
                }
            }
            log.error("Trade execution failed", e);
        }
    }

    private void updateOrderAfterTrade(QuotaMarketOrder order, long amount, double price) {
        order.setFilledAmount(order.getFilledAmount() + amount);
        order.setRemainingAmount(order.getRemainingAmount() - amount);
        order.setFilledPrice(order.getFilledPrice() + price);

        if (order.getRemainingAmount() <= 0) {
            order.setStatus(QuotaMarketOrder.OrderStatus.FILLED);
            order.setFilledAt(LocalDateTime.now());
            removeFromOrderBook(order);
        } else {
            order.setStatus(QuotaMarketOrder.OrderStatus.PARTIAL);
        }

        saveOrder(order);
    }

    public void cancelOrder(String orderId) {
        QuotaMarketOrder order = getOrder(orderId);
        if (order == null) {
            throw new RuntimeException("Order not found");
        }

        if (order.getStatus() != QuotaMarketOrder.OrderStatus.PENDING &&
                order.getStatus() != QuotaMarketOrder.OrderStatus.PARTIAL) {
            throw new RuntimeException("Order cannot be cancelled");
        }

        String lockValue = UUID.randomUUID().toString();
        if (!tryLock(MARKET_LOCK, lockValue, 10)) {
            throw new RuntimeException("Market busy");
        }

        try {
            order.setStatus(QuotaMarketOrder.OrderStatus.CANCELLED);
            saveOrder(order);
            removeFromOrderBook(order);

            if (order.getOrderType() == QuotaMarketOrder.OrderType.SELL && order.getRemainingAmount() > 0) {
                unfreezeQuota(order.getTenantId(), order.getGranularity(), order.getRemainingAmount());
            }

            log.info("Cancelled order: {}", orderId);
        } finally {
            unlock(MARKET_LOCK, lockValue);
        }
    }

    private void freezeQuota(String tenantId, String granularity, long amount) {
        String key = FROZEN_PREFIX + tenantId + ":" + granularity;
        redisTemplate.opsForValue().increment(key, amount);
        redisTemplate.expire(key, 24, TimeUnit.HOURS);
    }

    private void unfreezeQuota(String tenantId, String granularity, long amount) {
        String key = FROZEN_PREFIX + tenantId + ":" + granularity;
        redisTemplate.opsForValue().decrement(key, amount);
    }

    private long getFrozenQuota(String tenantId, String granularity) {
        String key = FROZEN_PREFIX + tenantId + ":" + granularity;
        Object val = redisTemplate.opsForValue().get(key);
        return val != null ? Long.parseLong(val.toString()) : 0;
    }

    private long getAvailableQuota(String tenantId, String granularity) {
        TenantQuota quota = quotaManagementService.getTenantQuota(tenantId);
        if (quota == null) return 0;

        long total;
        switch (granularity.toLowerCase()) {
            case "minute":
                total = quota.getMinuteLimit();
                break;
            case "hour":
                total = quota.getHourLimit();
                break;
            case "day":
                total = quota.getDayLimit();
                break;
            default:
                total = 0;
        }

        QuotaUsage usage = quotaManagementService.getQuotaUsage(tenantId);
        long used;
        switch (granularity.toLowerCase()) {
            case "minute":
                used = usage.getMinuteUsed();
                break;
            case "hour":
                used = usage.getHourUsed();
                break;
            case "day":
                used = usage.getDayUsed();
                break;
            default:
                used = 0;
        }
        long frozen = getFrozenQuota(tenantId, granularity);
        return Math.max(0, total - used - frozen);
    }

    private void saveOrder(QuotaMarketOrder order) {
        String key = ORDER_PREFIX + order.getOrderId();
        redisTemplate.opsForValue().set(key, order, 24, TimeUnit.HOURS);
        redisTemplate.opsForSet().add(ORDER_SET_KEY, order.getOrderId());
    }

    public QuotaMarketOrder getOrder(String orderId) {
        String key = ORDER_PREFIX + orderId;
        Object obj = redisTemplate.opsForValue().get(key);
        return obj instanceof QuotaMarketOrder ? (QuotaMarketOrder) obj : null;
    }

    private void saveTrade(QuotaTrade trade) {
        String key = TRADE_PREFIX + trade.getTradeId();
        redisTemplate.opsForValue().set(key, trade, 7, TimeUnit.DAYS);
        redisTemplate.opsForSet().add(TRADE_SET_KEY, trade.getTradeId());
    }

    private void addToOrderBook(QuotaMarketOrder order) {
        String priceKey;
        String orderKey;
        if (order.getOrderType() == QuotaMarketOrder.OrderType.SELL) {
            priceKey = SELL_ORDERBOOK_PREFIX + order.getGranularity();
            orderKey = SELL_ORDERBOOK_PREFIX + order.getGranularity() + ":" + order.getPricePerUnit();
        } else {
            priceKey = BUY_ORDERBOOK_PREFIX + order.getGranularity();
            orderKey = BUY_ORDERBOOK_PREFIX + order.getGranularity() + ":" + order.getPricePerUnit();
        }
        redisTemplate.opsForZSet().add(priceKey, String.valueOf(order.getPricePerUnit()), order.getPricePerUnit());
        redisTemplate.opsForSet().add(orderKey, order.getOrderId());
    }

    private void removeFromOrderBook(QuotaMarketOrder order) {
        String orderKey;
        if (order.getOrderType() == QuotaMarketOrder.OrderType.SELL) {
            orderKey = SELL_ORDERBOOK_PREFIX + order.getGranularity() + ":" + order.getPricePerUnit();
        } else {
            orderKey = BUY_ORDERBOOK_PREFIX + order.getGranularity() + ":" + order.getPricePerUnit();
        }
        redisTemplate.opsForSet().remove(orderKey, order.getOrderId());
    }

    public List<QuotaMarketOrder> getOrderBook(String granularity, QuotaMarketOrder.OrderType type) {
        Set<Object> orderIds = redisTemplate.opsForSet().members(ORDER_SET_KEY);
        if (orderIds == null) return List.of();

        return orderIds.stream()
                .map(id -> getOrder(String.valueOf(id)))
                .filter(o -> o != null)
                .filter(o -> o.getGranularity().equals(granularity))
                .filter(o -> o.getOrderType() == type)
                .filter(o -> o.getStatus() == QuotaMarketOrder.OrderStatus.PENDING ||
                        o.getStatus() == QuotaMarketOrder.OrderStatus.PARTIAL)
                .sorted((a, b) -> {
                    if (type == QuotaMarketOrder.OrderType.SELL) {
                        return Double.compare(a.getPricePerUnit(), b.getPricePerUnit());
                    } else {
                        return Double.compare(b.getPricePerUnit(), a.getPricePerUnit());
                    }
                })
                .collect(Collectors.toList());
    }

    public List<QuotaMarketOrder> getMyOrders(String tenantId) {
        Set<Object> orderIds = redisTemplate.opsForSet().members(ORDER_SET_KEY);
        if (orderIds == null) return List.of();

        return orderIds.stream()
                .map(id -> getOrder(String.valueOf(id)))
                .filter(o -> o != null)
                .filter(o -> o.getTenantId().equals(tenantId))
                .sorted((a, b) -> b.getCreatedAt().compareTo(a.getCreatedAt()))
                .collect(Collectors.toList());
    }

    public List<QuotaTrade> getRecentTrades(String granularity, int limit) {
        Set<Object> tradeIds = redisTemplate.opsForSet().members(TRADE_SET_KEY);
        if (tradeIds == null) return List.of();

        return tradeIds.stream()
                .map(id -> {
                    Object obj = redisTemplate.opsForValue().get(TRADE_PREFIX + id);
                    return obj instanceof QuotaTrade ? (QuotaTrade) obj : null;
                })
                .filter(t -> t != null)
                .filter(t -> t.getGranularity().equals(granularity))
                .sorted((a, b) -> b.getTradedAt().compareTo(a.getTradedAt()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    public Map<String, Object> getMarketStats(String granularity) {
        List<QuotaMarketOrder> sells = getOrderBook(granularity, QuotaMarketOrder.OrderType.SELL);
        List<QuotaMarketOrder> buys = getOrderBook(granularity, QuotaMarketOrder.OrderType.BUY);
        List<QuotaTrade> trades = getRecentTrades(granularity, 100);

        Map<String, Object> stats = new HashMap<>();
        stats.put("sellCount", sells.size());
        stats.put("buyCount", buys.size());
        stats.put("tradeCount24h", trades.size());

        if (!sells.isEmpty()) {
            stats.put("bestAsk", sells.get(0).getPricePerUnit());
        } else {
            stats.put("bestAsk", 0);
        }

        if (!buys.isEmpty()) {
            stats.put("bestBid", buys.get(0).getPricePerUnit());
        } else {
            stats.put("bestBid", 0);
        }

        if (!trades.isEmpty()) {
            stats.put("lastPrice", trades.get(0).getPricePerUnit());
            stats.put("volume24h", trades.stream().mapToLong(QuotaTrade::getAmount).sum());
        } else {
            stats.put("lastPrice", 0);
            stats.put("volume24h", 0);
        }

        return stats;
    }

    @Scheduled(fixedRate = 60000)
    public void expireOrders() {
        Set<Object> orderIds = redisTemplate.opsForSet().members(ORDER_SET_KEY);
        if (orderIds == null) return;

        LocalDateTime now = LocalDateTime.now();
        for (Object orderIdObj : orderIds) {
            String orderId = String.valueOf(orderIdObj);
            QuotaMarketOrder order = getOrder(orderId);
            if (order != null && order.getExpiresAt().isBefore(now) &&
                    (order.getStatus() == QuotaMarketOrder.OrderStatus.PENDING ||
                            order.getStatus() == QuotaMarketOrder.OrderStatus.PARTIAL)) {
                try {
                    cancelOrder(orderId);
                    order.setStatus(QuotaMarketOrder.OrderStatus.EXPIRED);
                    saveOrder(order);
                    log.info("Expired order: {}", orderId);
                } catch (Exception e) {
                    log.error("Failed to expire order {}", orderId, e);
                }
            }
        }
    }

    private boolean tryLock(String lockKey, String lockValue, long leaseTime) {
        Boolean result = redisTemplate.opsForValue()
                .setIfAbsent(lockKey, lockValue, leaseTime, TimeUnit.SECONDS);
        return Boolean.TRUE.equals(result);
    }

    private void unlock(String lockKey, String lockValue) {
        String luaScript = "if redis.call('get', KEYS[1]) == ARGV[1] then " +
                "return redis.call('del', KEYS[1]) " +
                "else " +
                "return 0 " +
                "end";
        org.springframework.data.redis.core.script.DefaultRedisScript<Long> redisScript =
                new org.springframework.data.redis.core.script.DefaultRedisScript<>(luaScript, Long.class);
        redisTemplate.execute(redisScript, java.util.Collections.singletonList(lockKey), lockValue);
    }
}
