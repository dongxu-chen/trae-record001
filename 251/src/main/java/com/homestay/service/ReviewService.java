package com.homestay.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.common.BusinessException;
import com.homestay.common.UserContext;
import com.homestay.dto.ReviewCreateDTO;
import com.homestay.entity.House;
import com.homestay.entity.OrderInfo;
import com.homestay.entity.Review;
import com.homestay.mapper.HouseMapper;
import com.homestay.mapper.OrderInfoMapper;
import com.homestay.mapper.ReviewMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class ReviewService {

    @Autowired
    private ReviewMapper reviewMapper;

    @Autowired
    private OrderInfoMapper orderInfoMapper;

    @Autowired
    private HouseMapper houseMapper;

    @Transactional(rollbackFor = Exception.class)
    public void createReview(ReviewCreateDTO dto) {
        Long userId = UserContext.getUserId();
        OrderInfo order = orderInfoMapper.selectById(dto.getOrderId());
        if (order == null || !order.getUserId().equals(userId)) {
            throw new BusinessException("订单不存在");
        }
        if (order.getStatus() != 3) {
            throw new BusinessException("订单未完成，无法评价");
        }
        Review existReview = reviewMapper.selectOne(new LambdaQueryWrapper<Review>()
                .eq(Review::getOrderId, dto.getOrderId()));
        if (existReview != null) {
            throw new BusinessException("已评价过此订单");
        }
        if (dto.getRating() < 1 || dto.getRating() > 5) {
            throw new BusinessException("评分必须在1-5之间");
        }
        Review review = new Review();
        review.setOrderId(dto.getOrderId());
        review.setHouseId(order.getHouseId());
        review.setUserId(userId);
        review.setHostId(order.getHostId());
        review.setRating(dto.getRating());
        review.setContent(dto.getContent());
        review.setImages(dto.getImages());
        review.setCleanliness(dto.getCleanliness() != null ? dto.getCleanliness() : dto.getRating());
        review.setAccuracy(dto.getAccuracy() != null ? dto.getAccuracy() : dto.getRating());
        review.setCommunication(dto.getCommunication() != null ? dto.getCommunication() : dto.getRating());
        review.setLocation(dto.getLocation() != null ? dto.getLocation() : dto.getRating());
        review.setCheckIn(dto.getCheckIn() != null ? dto.getCheckIn() : dto.getRating());
        review.setValue(dto.getValue() != null ? dto.getValue() : dto.getRating());
        reviewMapper.insert(review);
        updateHouseRating(order.getHouseId());
    }

    private void updateHouseRating(Long houseId) {
        List<Review> reviews = reviewMapper.selectList(new LambdaQueryWrapper<Review>()
                .eq(Review::getHouseId, houseId));
        if (reviews.isEmpty()) return;
        BigDecimal avgRating = reviews.stream()
                .map(r -> BigDecimal.valueOf(r.getRating()))
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(reviews.size()), 2, RoundingMode.HALF_UP);
        House house = houseMapper.selectById(houseId);
        if (house != null) {
            house.setRating(avgRating);
            house.setReviewCount(reviews.size());
            houseMapper.updateById(house);
        }
    }

    public List<Review> getHouseReviews(Long houseId, Integer pageNum, Integer pageSize) {
        LambdaQueryWrapper<Review> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Review::getHouseId, houseId)
                .orderByDesc(Review::getCreateTime);
        if (pageNum != null && pageSize != null) {
            wrapper.last("LIMIT " + (pageNum - 1) * pageSize + "," + pageSize);
        }
        return reviewMapper.selectList(wrapper);
    }

    public void replyReview(Long reviewId, String reply) {
        Long userId = UserContext.getUserId();
        Review review = reviewMapper.selectById(reviewId);
        if (review == null) {
            throw new BusinessException("评价不存在");
        }
        if (!review.getHostId().equals(userId)) {
            throw new BusinessException("无权限操作");
        }
        review.setHostReply(reply);
        review.setHostReplyTime(LocalDateTime.now());
        reviewMapper.updateById(review);
    }

    public List<Review> getUserReviews() {
        Long userId = UserContext.getUserId();
        return reviewMapper.selectList(new LambdaQueryWrapper<Review>()
                .eq(Review::getUserId, userId)
                .orderByDesc(Review::getCreateTime));
    }

    public List<Review> getHostReviews() {
        Long userId = UserContext.getUserId();
        return reviewMapper.selectList(new LambdaQueryWrapper<Review>()
                .eq(Review::getHostId, userId)
                .orderByDesc(Review::getCreateTime));
    }
}
