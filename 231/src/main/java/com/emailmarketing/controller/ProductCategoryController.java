package com.emailmarketing.controller;

import com.emailmarketing.common.Result;
import com.emailmarketing.entity.ProductCategory;
import com.emailmarketing.service.ProductCategoryService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/categories")
public class ProductCategoryController {

    @Autowired
    private ProductCategoryService categoryService;

    @GetMapping
    public Result<List<ProductCategory>> getAll() {
        return Result.success(categoryService.getAllActiveCategories());
    }

    @GetMapping("/{parentId}/children")
    public Result<List<ProductCategory>> getChildren(@PathVariable Long parentId) {
        return Result.success(categoryService.getSubCategories(parentId));
    }

    @PostMapping
    public Result<Void> create(@RequestBody ProductCategory category) {
        boolean success = categoryService.save(category);
        return success ? Result.success() : Result.error("创建失败");
    }

    @PutMapping
    public Result<Void> update(@RequestBody ProductCategory category) {
        boolean success = categoryService.updateById(category);
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        boolean success = categoryService.removeById(id);
        return success ? Result.success() : Result.error("删除失败");
    }
}
