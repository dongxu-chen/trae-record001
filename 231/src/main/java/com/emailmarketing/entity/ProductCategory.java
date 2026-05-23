package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("product_category")
public class ProductCategory extends BaseEntity {
    private String categoryCode;
    private String categoryName;
    private Long parentId;
    private String keywords;
    private Integer status;
}
