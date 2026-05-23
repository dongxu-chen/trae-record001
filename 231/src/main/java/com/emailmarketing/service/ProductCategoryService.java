package com.emailmarketing.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.ProductCategory;
import com.emailmarketing.mapper.ProductCategoryMapper;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ProductCategoryService extends ServiceImpl<ProductCategoryMapper, ProductCategory> {

    public List<ProductCategory> getCategoriesByCodes(List<String> categoryCodes) {
        LambdaQueryWrapper<ProductCategory> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(ProductCategory::getCategoryCode, categoryCodes);
        wrapper.eq(ProductCategory::getStatus, 1);
        return list(wrapper);
    }

    public List<ProductCategory> getAllActiveCategories() {
        LambdaQueryWrapper<ProductCategory> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ProductCategory::getStatus, 1);
        wrapper.orderByAsc(ProductCategory::getId);
        return list(wrapper);
    }

    public List<ProductCategory> getSubCategories(Long parentId) {
        LambdaQueryWrapper<ProductCategory> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ProductCategory::getParentId, parentId);
        wrapper.eq(ProductCategory::getStatus, 1);
        wrapper.orderByAsc(ProductCategory::getId);
        return list(wrapper);
    }
}
