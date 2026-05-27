package com.platform.points.controller;

import com.platform.points.dto.PointsExchangeDTO;
import com.platform.points.service.PointsMallService;
import com.platform.points.utils.Result;
import com.platform.points.vo.PointsMallProductVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/mall")
public class PointsMallController {

    @Autowired
    private PointsMallService pointsMallService;

    @GetMapping("/products")
    public Result<List<PointsMallProductVO>> listProducts() {
        return Result.success(pointsMallService.listProducts());
    }

    @GetMapping("/products/{productId}")
    public Result<PointsMallProductVO> getProduct(@PathVariable Long productId) {
        return Result.success(pointsMallService.getProduct(productId));
    }

    @PostMapping("/exchange")
    public Result<String> exchange(@RequestBody @Validated PointsExchangeDTO dto) {
        String orderNo = pointsMallService.exchange(dto);
        return Result.success("兑换成功，订单号: " + orderNo);
    }
}
