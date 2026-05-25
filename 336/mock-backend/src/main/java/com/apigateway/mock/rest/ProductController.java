package com.apigateway.mock.rest;

import com.apigateway.mock.common.ApiResponse;
import com.apigateway.mock.common.MockService;
import com.apigateway.mock.entity.Product;
import com.apigateway.mock.store.ProductStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/api/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductStore productStore;
    private final MockService mockService;

    @GetMapping
    public ApiResponse<List<Product>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String keyword) {
        log.info("查询商品列表: page={}, size={}, category={}, keyword={}", page, size, category, keyword);
        mockService.simulate();

        List<Product> products = new ArrayList<>(productStore.findAll());

        if (category != null && !category.isEmpty()) {
            products = products.stream()
                    .filter(p -> category.equals(p.getCategory()))
                    .collect(Collectors.toList());
        }

        if (keyword != null && !keyword.isEmpty()) {
            products = products.stream()
                    .filter(p -> p.getName().contains(keyword) ||
                            (p.getDescription() != null && p.getDescription().contains(keyword)))
                    .collect(Collectors.toList());
        }

        products.sort(Comparator.comparing(Product::getId));

        int start = (page - 1) * size;
        int end = Math.min(start + size, products.size());
        if (start >= products.size()) {
            products = new ArrayList<>();
        } else {
            products = products.subList(start, end);
        }

        return ApiResponse.success(products);
    }

    @GetMapping("/{id}")
    public ApiResponse<Product> getById(@PathVariable Long id) {
        log.info("查询商品详情: id={}", id);
        mockService.simulate();

        Product product = productStore.findById(id);
        if (product == null) {
            return ApiResponse.error(404, "商品不存在");
        }
        return ApiResponse.success(product);
    }

    @PostMapping
    public ApiResponse<Product> create(@RequestBody Product product) {
        log.info("创建商品: {}", product);
        mockService.simulate();

        Product saved = productStore.save(product);
        return ApiResponse.success("创建成功", saved);
    }

    @PutMapping("/{id}")
    public ApiResponse<Product> update(@PathVariable Long id, @RequestBody Product product) {
        log.info("更新商品: id={}, product={}", id, product);
        mockService.simulate();

        if (!productStore.existsById(id)) {
            return ApiResponse.error(404, "商品不存在");
        }
        product.setId(id);
        Product saved = productStore.save(product);
        return ApiResponse.success("更新成功", saved);
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        log.info("删除商品: id={}", id);
        mockService.simulate();

        if (!productStore.existsById(id)) {
            return ApiResponse.error(404, "商品不存在");
        }
        productStore.deleteById(id);
        return ApiResponse.success("删除成功", null);
    }

    @GetMapping("/count")
    public ApiResponse<Long> count() {
        log.info("统计商品数量");
        mockService.simulate();
        return ApiResponse.success(productStore.count());
    }
}
