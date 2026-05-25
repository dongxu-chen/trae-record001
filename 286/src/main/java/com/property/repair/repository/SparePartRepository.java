package com.property.repair.repository;

import com.property.repair.entity.SparePart;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SparePartRepository extends JpaRepository<SparePart, Long> {

    SparePart findByPartCode(String partCode);

    List<SparePart> findByCategory(String category);

    @Query("SELECT s FROM SparePart s WHERE s.stockQuantity - s.lockedQuantity < s.safeStock")
    List<SparePart> findLowStockParts();

    @Query("SELECT s FROM SparePart s WHERE s.stockQuantity - s.lockedQuantity >= :quantity")
    List<SparePart> findAvailableParts(Integer quantity);
}
