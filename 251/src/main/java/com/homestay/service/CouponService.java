package com.homestay.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.common.BusinessException;
import com.homestay.common.UserContext;
import com.homestay.entity.Coupon;
import com.homestay.entity.User;
import com.homestay.entity.UserCoupon;
import com.homestay.mapper.CouponMapper;
import com.homestay.mapper.UserCouponMapper;
import com.homestay.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class CouponService {

    @Autowired
    private CouponMapper couponMapper;

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Autowired
    private UserMapper userMapper;

    public List<Coupon> getCouponList() {
        return couponMapper.selectList(new LambdaQueryWrapper<Coupon>()
                .eq(Coupon::getStatus, 1)
                .gt(Coupon::getValidEndTime, LocalDateTime.now())
                .apply("used_count < total_count OR total_count = 0")
                .orderByDesc(Coupon::getCreateTime));
    }

    public List<UserCoupon> getUserCoupons(Integer status) {
        Long userId = UserContext.getUserId();
        LambdaQueryWrapper<UserCoupon> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserCoupon::getUserId, userId);
        if (status != null) {
            wrapper.eq(UserCoupon::getStatus, status);
        }
        wrapper.orderByDesc(UserCoupon::getCreateTime);
        return userCouponMapper.selectList(wrapper);
    }

    @Transactional(rollbackFor = Exception.class)
    public void receiveCoupon(Long couponId) {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BusinessException("请先登录");
        }
        Coupon coupon = couponMapper.selectById(couponId);
        if (coupon == null || coupon.getStatus() != 1) {
            throw new BusinessException("优惠券不存在或已失效");
        }
        if (coupon.getValidEndTime().isBefore(LocalDateTime.now())) {
            throw new BusinessException("优惠券已过期");
        }
        if (coupon.getTotalCount() > 0 && coupon.getUsedCount() >= coupon.getTotalCount()) {
            throw new BusinessException("优惠券已领完");
        }
        Long received = userCouponMapper.selectCount(new LambdaQueryWrapper<UserCoupon>()
                .eq(UserCoupon::getUserId, userId)
                .eq(UserCoupon::getCouponId, couponId));
        if (received >= coupon.getPerUserLimit()) {
            throw new BusinessException("已达到领取上限");
        }
        UserCoupon userCoupon = new UserCoupon();
        userCoupon.setUserId(userId);
        userCoupon.setCouponId(couponId);
        userCoupon.setStatus(0);
        userCouponMapper.insert(userCoupon);
    }

    public void createCoupon(Coupon coupon) {
        Long userId = UserContext.getUserId();
        User user = userMapper.selectById(userId);
        if (user == null || user.getRole() != 2) {
            throw new BusinessException("无权限操作");
        }
        coupon.setUsedCount(0);
        coupon.setStatus(1);
        couponMapper.insert(coupon);
    }

    public void updateCouponStatus(Long couponId, Integer status) {
        Long userId = UserContext.getUserId();
        User user = userMapper.selectById(userId);
        if (user == null || user.getRole() != 2) {
            throw new BusinessException("无权限操作");
        }
        Coupon coupon = couponMapper.selectById(couponId);
        if (coupon == null) {
            throw new BusinessException("优惠券不存在");
        }
        coupon.setStatus(status);
        couponMapper.updateById(coupon);
    }
}
