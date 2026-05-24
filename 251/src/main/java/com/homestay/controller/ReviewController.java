package com.homestay.controller;

import com.homestay.common.Result;
import com.homestay.dto.ReviewCreateDTO;
import com.homestay.entity.Review;
import com.homestay.service.ReviewService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/review")
public class ReviewController {

    @Autowired
    private ReviewService reviewService;

    @PostMapping("/create")
    public Result<Void> createReview(@Valid @RequestBody ReviewCreateDTO dto) {
        reviewService.createReview(dto);
        return Result.success();
    }

    @GetMapping("/house/{houseId}")
    public Result<List<Review>> getHouseReviews(@PathVariable Long houseId,
                                                 @RequestParam(required = false) Integer pageNum,
                                                 @RequestParam(required = false) Integer pageSize) {
        return Result.success(reviewService.getHouseReviews(houseId, pageNum, pageSize));
    }

    @PostMapping("/reply/{id}")
    public Result<Void> replyReview(@PathVariable Long id, @RequestParam String reply) {
        reviewService.replyReview(id, reply);
        return Result.success();
    }

    @GetMapping("/user/list")
    public Result<List<Review>> getUserReviews() {
        return Result.success(reviewService.getUserReviews());
    }

    @GetMapping("/host/list")
    public Result<List<Review>> getHostReviews() {
        return Result.success(reviewService.getHostReviews());
    }
}
