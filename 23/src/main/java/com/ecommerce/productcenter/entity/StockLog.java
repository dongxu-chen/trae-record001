package com.ecommerce.productcenter.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "stock_logs", indexes = {
    @Index(name = "idx_sku_id", columnList = "sku_id"),
    @Index(name = "idx_order_no", columnList = "order_no")
})
public class StockLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sku_id", nullable = false)
    private Long skuId;

    @Column(name = "order_no", length = 64)
    private String orderNo;

    @Column(nullable = false, length = 32)
    @Enumerated(EnumType.STRING)
    private StockType type;

    @Column(nullable = false)
    private Integer quantity;

    @Column(name = "before_stock", nullable = false)
    private Integer beforeStock;

    @Column(name = "after_stock", nullable = false)
    private Integer afterStock;

    @Column(length = 500)
    private String remark;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }

    public enum StockType {
        DEDUCT,    
        FREEZE,    
        RELEASE,   
        INCREASE,  
        INIT       
    }
}
