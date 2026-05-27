package com.medical.stockwarning.repository;

import com.medical.stockwarning.entity.Medicine;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface MedicineRepository extends JpaRepository<Medicine, Long> {

    Optional<Medicine> findByMedicineCode(String medicineCode);

    List<Medicine> findByIsActive(Integer isActive);

    @Query("SELECT m FROM Medicine m WHERE m.isActive = 1 AND m.id IN :medicineIds")
    List<Medicine> findActiveByIds(List<Long> medicineIds);
}
