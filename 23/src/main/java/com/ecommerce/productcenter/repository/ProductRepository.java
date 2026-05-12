package com.ecommerce.productcenter.repository;

import com.ecommerce.productcenter.entity.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {

    Optional<Product> findByIdAndActiveTrue(Long id);

    Page<Product> findByActiveTrue(Pageable pageable);

    Page<Product> findByCategoryAndActiveTrue(String category, Pageable pageable);

    @Query(
        value = "SELECT p FROM Product p WHERE p.active = true AND LOWER(p.name) LIKE LOWER(CONCAT('%', :keyword, '%'))",
        countQuery = "SELECT COUNT(p) FROM Product p WHERE p.active = true AND LOWER(p.name) LIKE LOWER(CONCAT('%', :keyword, '%'))"
    )
    Page<Product> searchByName(@Param("keyword") String keyword, Pageable pageable);

    @Query(
        value = "SELECT p FROM Product p WHERE p.active = true AND (LOWER(p.category) LIKE LOWER(CONCAT('%', :keyword, '%')) OR LOWER(p.name) LIKE LOWER(CONCAT('%', :keyword, '%')))",
        countQuery = "SELECT COUNT(p) FROM Product p WHERE p.active = true AND (LOWER(p.category) LIKE LOWER(CONCAT('%', :keyword, '%')) OR LOWER(p.name) LIKE LOWER(CONCAT('%', :keyword, '%')))"
    )
    Page<Product> searchByNameOrCategory(@Param("keyword") String keyword, Pageable pageable);

    List<Product> findByCategoryAndActiveTrue(String category);

    List<Product> findByActiveTrue();

    long countByActiveTrue();
}
