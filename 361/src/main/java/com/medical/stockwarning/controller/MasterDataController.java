package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.entity.Supplier;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import com.medical.stockwarning.repository.SupplierRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/master")
@RequiredArgsConstructor
public class MasterDataController {

    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;
    private final SupplierRepository supplierRepository;

    @GetMapping("/medicines")
    public ApiResponse<List<Medicine>> getMedicines() {
        return ApiResponse.success(medicineRepository.findByIsActive(1));
    }

    @GetMapping("/medicines/{id}")
    public ApiResponse<Medicine> getMedicineById(@PathVariable Long id) {
        return ApiResponse.success(medicineRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Medicine not found: " + id)));
    }

    @PostMapping("/medicines")
    public ApiResponse<Medicine> createMedicine(@RequestBody Medicine medicine) {
        return ApiResponse.success(medicineRepository.save(medicine));
    }

    @PutMapping("/medicines/{id}")
    public ApiResponse<Medicine> updateMedicine(@PathVariable Long id, @RequestBody Medicine medicine) {
        medicine.setId(id);
        return ApiResponse.success(medicineRepository.save(medicine));
    }

    @DeleteMapping("/medicines/{id}")
    public ApiResponse<Void> deleteMedicine(@PathVariable Long id) {
        Medicine medicine = medicineRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Medicine not found: " + id));
        medicine.setIsActive(0);
        medicineRepository.save(medicine);
        return ApiResponse.success();
    }

    @GetMapping("/warehouses")
    public ApiResponse<List<Warehouse>> getWarehouses() {
        return ApiResponse.success(warehouseRepository.findByStatus(1));
    }

    @GetMapping("/warehouses/{id}")
    public ApiResponse<Warehouse> getWarehouseById(@PathVariable Long id) {
        return ApiResponse.success(warehouseRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Warehouse not found: " + id)));
    }

    @PostMapping("/warehouses")
    public ApiResponse<Warehouse> createWarehouse(@RequestBody Warehouse warehouse) {
        return ApiResponse.success(warehouseRepository.save(warehouse));
    }

    @PutMapping("/warehouses/{id}")
    public ApiResponse<Warehouse> updateWarehouse(@PathVariable Long id, @RequestBody Warehouse warehouse) {
        warehouse.setId(id);
        return ApiResponse.success(warehouseRepository.save(warehouse));
    }

    @GetMapping("/suppliers")
    public ApiResponse<List<Supplier>> getSuppliers() {
        return ApiResponse.success(supplierRepository.findByIsActive(1));
    }

    @PostMapping("/suppliers")
    public ApiResponse<Supplier> createSupplier(@RequestBody Supplier supplier) {
        return ApiResponse.success(supplierRepository.save(supplier));
    }
}
