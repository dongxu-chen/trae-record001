package com.homestay.controller;

import com.homestay.common.Result;
import com.homestay.service.PricingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/pricing")
public class PricingController {

    @Autowired
    private PricingService pricingService;

    @GetMapping("/suggestion/{houseId}")
    public Result<Map<String, Object>> getPricingSuggestion(@PathVariable Long houseId) {
        return Result.success(pricingService.getPricingSuggestion(houseId));
    }
}
