package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.dto.MedicineAssociationDTO;
import com.medical.stockwarning.service.MedicineAssociationService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/associations")
@RequiredArgsConstructor
public class AssociationController {

    private final MedicineAssociationService associationService;

    @GetMapping
    public ApiResponse<List<MedicineAssociationDTO>> analyzeAssociations(
            @RequestParam(required = false) Long warehouseId) {
        return ApiResponse.success(associationService.analyzeAssociations(warehouseId));
    }

    @GetMapping("/strong")
    public ApiResponse<List<MedicineAssociationDTO>> getStrongAssociations() {
        return ApiResponse.success(associationService.getStrongAssociations());
    }

    @GetMapping("/medicine/{medicineId}")
    public ApiResponse<List<MedicineAssociationDTO>> getAssociationsForMedicine(
            @PathVariable Long medicineId) {
        return ApiResponse.success(associationService.getAssociationsForMedicine(medicineId));
    }

    @GetMapping("/medicine/{medicineId}/related")
    public ApiResponse<List<Long>> getAssociatedMedicineIds(@PathVariable Long medicineId) {
        return ApiResponse.success(associationService.getAssociatedMedicineIds(medicineId));
    }

    @GetMapping("/groups")
    public ApiResponse<List<List<Long>>> findFrequentMedicineGroups() {
        return ApiResponse.success(associationService.findFrequentMedicineGroups());
    }

    @PostMapping("/check-combined-stockout")
    public ApiResponse<List<MedicineAssociationDTO>> checkCombinedStockout(
            @RequestBody List<Long> medicineIds) {
        return ApiResponse.success(associationService.checkCombinedStockout(medicineIds));
    }

    @GetMapping("/stats")
    public ApiResponse<Map<String, Object>> getAssociationStats() {
        return ApiResponse.success(associationService.getAssociationStats());
    }
}
