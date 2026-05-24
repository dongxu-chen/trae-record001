package com.homestay.task;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.entity.Coupon;
import com.homestay.entity.OrderInfo;
import com.homestay.entity.UserCoupon;
import com.homestay.mapper.CouponMapper;
import com.homestay.mapper.HouseCalendarMapper;
import com.homestay.mapper.OrderInfoMapper;
import com.homestay.mapper.UserCouponMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;

@Slf4j
@Component
public class OrderTimeoutTask {

    @Autowired
    private OrderInfoMapper orderInfoMapper;

    @Autowired
    private HouseCalendarMapper houseCalendarMapper;

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Autowired
    private CouponMapper couponMapper;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Scheduled(cron = "0 0/5 * * * ?")
    @Transactional(rollbackFor = Exception.class)
    public void processTimeoutOrders() {
        Set<String> keys = redisTemplate.keys("order:timeout:*");
        if (keys == null || keys.isEmpty()) {
            return;
        }
        for (String key : keys) {
            Long orderId = (Long) redisTemplate.opsForValue().get(key);
            if (orderId == null) {
                redisTemplate.delete(key);
                continue;
            }
            OrderInfo order = orderInfoMapper.selectById(orderId);
            if (order == null) {
                redisTemplate.delete(key);
                continue;
            }
            if (order.getStatus() == 0 && order.getCreateTime().plusMinutes(30).isBefore(LocalDateTime.now())) {
                log.info("订单超时自动取消: {}", orderId);
                order.setStatus(4);
                order.setCancelTime(LocalDateTime.now());
                orderInfoMapper.updateById(order);
                houseCalendarMapper.batchUpdateStock(order.getHouseId(), order.getCheckInDate(), order.getCheckOutDate().minusDays(1), 1);
                redisTemplate.delete(key);
            }
        }
    }

    @Scheduled(cron = "0 0 2 * * ?")
    @Transactional(rollbackFor = Exception.class)
    public void autoCheckIn() {
        List<OrderInfo> orders = orderInfoMapper.selectList(new LambdaQueryWrapper<OrderInfo>()
                .eq(OrderInfo::getStatus, 1)
                .apply("check_in_date = CURDATE()"));
        for (OrderInfo order : orders) {
            order.setStatus(2);
            orderInfoMapper.updateById(order);
            log.info("自动入住: {}", order.getId());
        }
    }

    @Scheduled(cron = "0 0 12 * * ?")
    @Transactional(rollbackFor = Exception.class)
    public void autoCheckOut() {
        List<OrderInfo> orders = orderInfoMapper.selectList(new LambdaQueryWrapper<OrderInfo>()
                .eq(OrderInfo::getStatus, 2)
                .apply("check_out_date = CURDATE()"));
        for (OrderInfo order : orders) {
            order.setStatus(3);
            orderInfoMapper.updateById(order);
            log.info("自动退房: {}", order.getId());
        }
    }
}
