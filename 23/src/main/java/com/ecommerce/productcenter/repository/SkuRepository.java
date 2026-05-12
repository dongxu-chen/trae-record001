package com.ecommerce.productcenter.repository;

import com.ecommerce.productcenter.entity.Sku;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SkuRepository extends JpaRepository<Sku, Long> {

    List<Sku> findByProductIdAndActiveTrue(Long productId);

    Optional<Sku> findBySkuCode(String skuCode);

    Optional<Sku> findByIdAndActiveTrue(Long id);

    Page<Sku> findByProductId(Long productId, Pageable pageable);

    Page<Sku> findByActiveTrue(Pageable pageable);

    @Modifying
    @Query("UPDATE Sku s SET s.stock = s.stock - :quantity WHERE s.id = :skuId AND s.stock >= :quantity AND s.active = true")
    int deductStock(@Param("skuId") Long skuId, @Param("quantity") int quantity);

    @Modifying
    @Query("UPDATE Sku s SET s.stock = s.stock + :quantity WHERE s.id = :skuId AND s.active = true")
    int increaseStock(@Param("skuId") Long skuId, @Param("quantity") int quantity);

    @Query("SELECT s.stock FROM Sku s WHERE s.id = :skuId")
    Integer findStockBySkuId(@Param("skuId") Long skuId);

    void deleteByProductId(Long productId);
}
