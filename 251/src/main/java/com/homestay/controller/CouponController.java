package com.homestay.controller;

import com.homestay.common.Result;
import com.homestay.entity.Coupon;
import com.homestay.entity.UserCoupon;
import com.homestay.service.CouponService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/coupon")
public class CouponController {

    @Autowired
    private CouponService couponService;

    @GetMapping("/list")
    public Result<List<Coupon>> getCouponList() {
        return Result.success(couponService.getCouponList());
    }

    @GetMapping("/user/list")
    public Result<List<UserCoupon>> getUserCoupons(@RequestParam(required = false) Integer status) {
        return Result.success(couponService.getUserCoupons(status));
    }

    @PostMapping("/receive/{id}")
    public Result<Void> receiveCoupon(@PathVariable Long id) {
        couponService.receiveCoupon(id);
        return Result.success();
    }

    @PostMapping("/create")
    public Result<Void> createCoupon(@RequestBody Coupon coupon) {
        couponService.createCoupon(coupon);
        return Result.success();
    }

    @PostMapping("/status/{id}")
    public Result<Void> updateCouponStatus(@PathVariable Long id, @RequestParam Integer status) {
        couponService.updateCouponStatus(id, status);
        return Result.success();
    }
}
