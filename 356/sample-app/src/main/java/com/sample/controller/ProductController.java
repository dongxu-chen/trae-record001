package com.sample.controller;

import com.sample.dto.ProductRequest;
import com.sample.dto.ProductResponse;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    @GetMapping
    public List<ProductResponse> getAllProducts(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String category) {
        return new ArrayList<>();
    }

    @GetMapping("/{id}")
    public ProductResponse getProductById(@PathVariable Long id) {
        return new ProductResponse();
    }

    @PostMapping
    public ProductResponse createProduct(@RequestBody ProductRequest request) {
        return new ProductResponse();
    }

    @PutMapping("/{id}")
    public ProductResponse updateProduct(@PathVariable Long id, @RequestBody ProductRequest request) {
        return new ProductResponse();
    }

    @DeleteMapping("/{id}")
    public void deleteProduct(@PathVariable Long id) {
    }
}