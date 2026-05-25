package com.apigateway.mock.rest;

import com.apigateway.mock.common.ApiResponse;
import com.apigateway.mock.common.MockService;
import com.apigateway.mock.entity.Product;
import com.apigateway.mock.entity.Recommendation;
import com.apigateway.mock.store.ProductStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/api/recommendations")
@RequiredArgsConstructor
public class RecommendationController {

    private final ProductStore productStore;
    private final MockService mockService;
    private final Random random = new Random();

    @GetMapping("/user/{userId}")
    public ApiResponse<List<Recommendation>> getUserRecommendations(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "5") int limit) {
        log.info("获取用户推荐: userId={}, limit={}", userId, userId);
        mockService.simulate();

        List<Product> products = new ArrayList<>(productStore.findAll());
        products.sort(Comparator.comparing(Product::getId));

        List<Recommendation> recommendations = products.stream()
                .limit(limit)
                .map(product -> Recommendation.builder()
                        .productId(product.getId())
                        .productName(product.getName())
                        .score(Math.round((0.5 + random.nextDouble() * 0.5) * 100.0) / 100.0)
                        .reason("基于用户" + userId + "的浏览历史推荐")
                        .build())
                .collect(Collectors.toList());

        return ApiResponse.success(recommendations);
    }

    @GetMapping("/product/{productId}")
    public ApiResponse<List<Recommendation>> getProductRecommendations(
            @PathVariable Long productId,
            @RequestParam(defaultValue = "5") int limit) {
        log.info("获取商品相关推荐: productId={}, limit={}", productId, limit);
        mockService.simulate();

        Product currentProduct = productStore.findById(productId);
        if (currentProduct == null) {
            return ApiResponse.error(404, "商品不存在");
        }

        List<Product> products = new ArrayList<>(productStore.findAll());
        products = products.stream()
                .filter(p -> !p.getId().equals(productId))
                .filter(p -> currentProduct.getCategory().equals(p.getCategory()))
                .limit(limit)
                .collect(Collectors.toList());

        if (products.isEmpty()) {
            products = new ArrayList<>(productStore.findAll()).stream()
                    .filter(p -> !p.getId().equals(productId))
                    .limit(limit)
                    .collect(Collectors.toList());
        }

        List<Recommendation> recommendations = products.stream()
                .map(product -> Recommendation.builder()
                        .productId(product.getId())
                        .productName(product.getName())
                        .score(Math.round((0.6 + random.nextDouble() * 0.4) * 100.0) / 100.0)
                        .reason("与商品" + productId + "相似")
                        .build())
                .collect(Collectors.toList());

        return ApiResponse.success(recommendations);
    }

    @GetMapping("/hot")
    public ApiResponse<List<Recommendation>> getHotRecommendations(
            @RequestParam(defaultValue = "10") int limit) {
        log.info("获取热门推荐: limit={}", limit);
        mockService.simulate();

        List<Product> products = new ArrayList<>(productStore.findAll());
        products.sort((p1, p2) -> Double.compare(p2.getPrice(), p1.getPrice()));

        List<Recommendation> recommendations = products.stream()
                .limit(limit)
                .map(product -> Recommendation.builder()
                        .productId(product.getId())
                        .productName(product.getName())
                        .score(Math.round((0.7 + random.nextDouble() * 0.3) * 100.0) / 100.0)
                        .reason("热门商品推荐")
                        .build())
                .collect(Collectors.toList());

        return ApiResponse.success(recommendations);
    }

    @GetMapping("/new")
    public ApiResponse<List<Recommendation>> getNewRecommendations(
            @RequestParam(defaultValue = "10") int limit) {
        log.info("获取新品推荐: limit={}", limit);
        mockService.simulate();

        List<Product> products = new ArrayList<>(productStore.findAll());
        products.sort((p1, p2) -> p2.getId().compareTo(p1.getId()));

        List<Recommendation> recommendations = products.stream()
                .limit(limit)
                .map(product -> Recommendation.builder()
                        .productId(product.getId())
                        .productName(product.getName())
                        .score(Math.round((0.6 + random.nextDouble() * 0.4) * 100.0) / 100.0)
                        .reason("新品上架推荐")
                        .build())
                .collect(Collectors.toList());

        return ApiResponse.success(recommendations);
    }
}
