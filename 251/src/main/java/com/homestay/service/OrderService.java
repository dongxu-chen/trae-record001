package com.homestay.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.common.BusinessException;
import com.homestay.common.UserContext;
import com.homestay.dto.OrderCreateDTO;
import com.homestay.entity.*;
import com.homestay.mapper.*;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class OrderService {

    @Autowired
    private OrderInfoMapper orderInfoMapper;

    @Autowired
    private HouseMapper houseMapper;

    @Autowired
    private HouseCalendarMapper houseCalendarMapper;

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Autowired
    private CouponMapper couponMapper;

    @Autowired
    private RedissonClient redissonClient;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private HouseService houseService;

    @Autowired
    private BlacklistService blacklistService;

    @Transactional(rollbackFor = Exception.class)
    public OrderInfo createOrder(OrderCreateDTO dto) {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BusinessException("请先登录");
        }
        blacklistService.checkBlacklist(userId);
        if (dto.getCheckInDate().isAfter(dto.getCheckOutDate()) || dto.getCheckInDate().isEqual(dto.getCheckOutDate())) {
            throw new BusinessException("入住日期必须早于退房日期");
        }
        if (dto.getCheckInDate().isBefore(LocalDate.now())) {
            throw new BusinessException("入住日期不能早于今天");
        }
        House house = houseMapper.selectById(dto.getHouseId());
        if (house == null || house.getStatus() != 1) {
            throw new BusinessException("房源不存在或未上架");
        }
        if (dto.getGuestCount() > house.getMaxGuests()) {
            throw new BusinessException("入住人数超过最大限制");
        }
        String lockKey = "house:stock:" + dto.getHouseId();
        RLock lock = redissonClient.getFairLock(lockKey);
        try {
            if (!lock.tryLock(5, 10, TimeUnit.SECONDS)) {
                throw new BusinessException("系统繁忙，请稍后重试");
            }
            List<HouseCalendar> calendars = houseCalendarMapper.selectByHouseIdAndDateRange(
                    dto.getHouseId(), dto.getCheckInDate(), dto.getCheckOutDate().minusDays(1));
            long nightCount = ChronoUnit.DAYS.between(dto.getCheckInDate(), dto.getCheckOutDate());
            if (calendars.size() != nightCount) {
                throw new BusinessException("所选日期部分不可预订");
            }
            for (HouseCalendar calendar : calendars) {
                if (calendar.getStock() <= 0 || calendar.getStatus() != 1) {
                    throw new BusinessException("所选日期已被预订");
                }
            }
            BigDecimal totalPrice = calendars.stream()
                    .map(HouseCalendar::getPrice)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            List<Long> userCouponIds = new ArrayList<>();
            if (dto.getCouponId() != null) {
                userCouponIds.add(dto.getCouponId());
            }
            if (dto.getCouponIds() != null && !dto.getCouponIds().isEmpty()) {
                userCouponIds.addAll(dto.getCouponIds());
            }
            userCouponIds = userCouponIds.stream().distinct().collect(Collectors.toList());

            BigDecimal couponDiscount = BigDecimal.ZERO;
            List<Long> validCouponIds = new ArrayList<>();
            Set<String> usedGroups = new HashSet<>();

            if (!userCouponIds.isEmpty()) {
                for (Long userCouponId : userCouponIds) {
                    UserCoupon userCoupon = userCouponMapper.selectOne(new LambdaQueryWrapper<UserCoupon>()
                            .eq(UserCoupon::getUserId, userId)
                            .eq(UserCoupon::getId, userCouponId)
                            .eq(UserCoupon::getStatus, 0));
                    if (userCoupon == null) {
                        throw new BusinessException("优惠券不存在或不可用");
                    }
                    Coupon coupon = couponMapper.selectById(userCoupon.getCouponId());
                    if (coupon == null || coupon.getStatus() != 1) {
                        throw new BusinessException("优惠券已失效");
                    }
                    if (coupon.getValidEndTime().isBefore(LocalDateTime.now())) {
                        throw new BusinessException("优惠券已过期");
                    }
                    if (totalPrice.compareTo(coupon.getMinAmount()) < 0) {
                        throw new BusinessException("优惠券未达到使用门槛: " + coupon.getName());
                    }

                    String groupCode = coupon.getGroupCode();
                    if (groupCode != null && !groupCode.isEmpty()) {
                        if (usedGroups.contains(groupCode)) {
                            throw new BusinessException("同组优惠券只能使用一张: " + coupon.getName());
                        }
                        usedGroups.add(groupCode);
                    }

                    BigDecimal discount;
                    if (coupon.getType() == 1) {
                        discount = coupon.getDiscountAmount();
                    } else {
                        discount = totalPrice.multiply(BigDecimal.ONE.subtract(coupon.getDiscountPercent().divide(new BigDecimal(100))));
                    }
                    couponDiscount = couponDiscount.add(discount);
                    validCouponIds.add(userCoupon.getId());
                }
            }

            Long firstCouponId = validCouponIds.isEmpty() ? null : validCouponIds.get(0);
            String couponIdsStr = validCouponIds.isEmpty() ? null : String.join(",", validCouponIds.stream().map(String::valueOf).collect(Collectors.toList()));

            BigDecimal payAmount = totalPrice.add(house.getCleaningFee() != null ? house.getCleaningFee() : BigDecimal.ZERO)
                    .subtract(couponDiscount);
            if (payAmount.compareTo(BigDecimal.ZERO) < 0) {
                payAmount = BigDecimal.ZERO;
            }
            String orderNo = "HS" + System.currentTimeMillis() + UUID.randomUUID().toString().substring(0, 6).toUpperCase();
            OrderInfo order = new OrderInfo();
            order.setOrderNo(orderNo);
            order.setUserId(userId);
            order.setHouseId(dto.getHouseId());
            order.setHostId(house.getHostId());
            order.setCheckInDate(dto.getCheckInDate());
            order.setCheckOutDate(dto.getCheckOutDate());
            order.setGuestCount(dto.getGuestCount());
            order.setNightCount((int) nightCount);
            order.setTotalPrice(totalPrice);
            order.setCleaningFee(house.getCleaningFee() != null ? house.getCleaningFee() : BigDecimal.ZERO);
            order.setCouponDiscount(couponDiscount);
            order.setPayAmount(payAmount);
            order.setStatus(0);
            order.setContactName(dto.getContactName());
            order.setContactPhone(dto.getContactPhone());
            order.setRemark(dto.getRemark());
            order.setCouponId(firstCouponId);
            order.setCouponIds(couponIdsStr);
            orderInfoMapper.insert(order);
            houseCalendarMapper.batchUpdateStock(dto.getHouseId(), dto.getCheckInDate(), dto.getCheckOutDate().minusDays(1), -1);
            houseService.updateCalendarVersion(dto.getHouseId());
            redisTemplate.opsForValue().set("order:timeout:" + order.getId(), order.getId(), 30, TimeUnit.MINUTES);
            return order;
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            throw new BusinessException("创建订单失败");
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public void payOrder(Long orderId, String payMethod) {
        Long userId = UserContext.getUserId();
        OrderInfo order = orderInfoMapper.selectById(orderId);
        if (order == null || !order.getUserId().equals(userId)) {
            throw new BusinessException("订单不存在");
        }
        if (order.getStatus() != 0) {
            throw new BusinessException("订单状态异常");
        }
        order.setStatus(1);
        order.setPayMethod(payMethod);
        order.setPayTime(LocalDateTime.now());
        orderInfoMapper.updateById(order);

        List<Long> couponIdList = new ArrayList<>();
        if (order.getCouponIds() != null && !order.getCouponIds().isEmpty()) {
            String[] ids = order.getCouponIds().split(",");
            for (String idStr : ids) {
                couponIdList.add(Long.parseLong(idStr));
            }
        } else if (order.getCouponId() != null) {
            couponIdList.add(order.getCouponId());
        }

        for (Long userCouponId : couponIdList) {
            UserCoupon userCoupon = userCouponMapper.selectById(userCouponId);
            if (userCoupon != null) {
                userCoupon.setStatus(1);
                userCoupon.setUsedTime(LocalDateTime.now());
                userCoupon.setOrderId(orderId);
                userCouponMapper.updateById(userCoupon);
                Coupon coupon = couponMapper.selectById(userCoupon.getCouponId());
                if (coupon != null) {
                    coupon.setUsedCount(coupon.getUsedCount() + 1);
                    couponMapper.updateById(coupon);
                }
            }
        }
        redisTemplate.delete("order:timeout:" + orderId);
    }

    @Transactional(rollbackFor = Exception.class)
    public void cancelOrder(Long orderId) {
        Long userId = UserContext.getUserId();
        OrderInfo order = orderInfoMapper.selectById(orderId);
        if (order == null || !order.getUserId().equals(userId)) {
            throw new BusinessException("订单不存在");
        }
        if (order.getStatus() != 0 && order.getStatus() != 1) {
            throw new BusinessException("订单状态不允许取消");
        }
        if (order.getStatus() == 1 && order.getCheckInDate().isBefore(LocalDate.now().plusDays(1))) {
            throw new BusinessException("入住前24小时内无法取消");
        }
        order.setStatus(4);
        order.setCancelTime(LocalDateTime.now());
        orderInfoMapper.updateById(order);
        houseCalendarMapper.batchUpdateStock(order.getHouseId(), order.getCheckInDate(), order.getCheckOutDate().minusDays(1), 1);
        houseService.updateCalendarVersion(order.getHouseId());
        blacklistService.recordCancelOrder(userId, orderId);

        if (order.getStatus() == 1) {
            List<Long> couponIdList = new ArrayList<>();
            if (order.getCouponIds() != null && !order.getCouponIds().isEmpty()) {
                String[] ids = order.getCouponIds().split(",");
                for (String idStr : ids) {
                    couponIdList.add(Long.parseLong(idStr));
                }
            } else if (order.getCouponId() != null) {
                couponIdList.add(order.getCouponId());
            }

            for (Long userCouponId : couponIdList) {
                UserCoupon userCoupon = userCouponMapper.selectById(userCouponId);
                if (userCoupon != null) {
                    userCoupon.setStatus(0);
                    userCoupon.setUsedTime(null);
                    userCoupon.setOrderId(null);
                    userCouponMapper.updateById(userCoupon);
                    Coupon coupon = couponMapper.selectById(userCoupon.getCouponId());
                    if (coupon != null) {
                        coupon.setUsedCount(coupon.getUsedCount() - 1);
                        couponMapper.updateById(coupon);
                    }
                }
            }
        }
        redisTemplate.delete("order:timeout:" + orderId);
    }

    public List<OrderInfo> getUserOrders(Integer status) {
        Long userId = UserContext.getUserId();
        LambdaQueryWrapper<OrderInfo> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(OrderInfo::getUserId, userId);
        if (status != null) {
            wrapper.eq(OrderInfo::getStatus, status);
        }
        wrapper.orderByDesc(OrderInfo::getCreateTime);
        return orderInfoMapper.selectList(wrapper);
    }

    public List<OrderInfo> getHostOrders(Integer status) {
        Long userId = UserContext.getUserId();
        LambdaQueryWrapper<OrderInfo> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(OrderInfo::getHostId, userId);
        if (status != null) {
            wrapper.eq(OrderInfo::getStatus, status);
        }
        wrapper.orderByDesc(OrderInfo::getCreateTime);
        return orderInfoMapper.selectList(wrapper);
    }

    public void checkIn(Long orderId) {
        Long userId = UserContext.getUserId();
        OrderInfo order = orderInfoMapper.selectById(orderId);
        if (order == null || !order.getHostId().equals(userId)) {
            throw new BusinessException("无权限操作");
        }
        if (order.getStatus() != 1) {
            throw new BusinessException("订单状态异常");
        }
        order.setStatus(2);
        orderInfoMapper.updateById(order);
    }

    public void checkOut(Long orderId) {
        Long userId = UserContext.getUserId();
        OrderInfo order = orderInfoMapper.selectById(orderId);
        if (order == null || !order.getHostId().equals(userId)) {
            throw new BusinessException("无权限操作");
        }
        if (order.getStatus() != 2) {
            throw new BusinessException("订单状态异常");
        }
        order.setStatus(3);
        orderInfoMapper.updateById(order);
    }
}
