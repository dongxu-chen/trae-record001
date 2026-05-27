package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.dto.MedicineStockDTO;
import com.medical.stockwarning.entity.Stock;
import com.medical.stockwarning.service.StockService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/stocks")
@RequiredArgsConstructor
public class StockController {

    private final StockService stockService;

    @GetMapping("/warehouse/{warehouseId}")
    public ApiResponse<List<MedicineStockDTO>> getStockOverview(@PathVariable Long warehouseId) {
        return ApiResponse.success(stockService.getStockOverview(warehouseId));
    }

    @GetMapping("/warehouse/{warehouseId}/medicine/{medicineId}")
    public ApiResponse<MedicineStockDTO> getMedicineStock(
            @PathVariable Long warehouseId,
            @PathVariable Long medicineId) {
        return ApiResponse.success(stockService.getMedicineStock(warehouseId, medicineId));
    }

    @GetMapping("/warehouse/{warehouseId}/medicine/{medicineId}/details")
    public ApiResponse<List<Stock>> getStockDetails(
            @PathVariable Long warehouseId,
            @PathVariable Long medicineId) {
        return ApiResponse.success(stockService.getStockDetails(warehouseId, medicineId));
    }

    @GetMapping("/warehouse/{warehouseId}/medicine/{medicineId}/available")
    public ApiResponse<List<Stock>> getAvailableStocks(
            @PathVariable Long warehouseId,
            @PathVariable Long medicineId) {
        return ApiResponse.success(stockService.getAvailableStocks(warehouseId, medicineId));
    }

    @PostMapping
    public ApiResponse<Stock> addStock(@RequestBody Stock stock) {
        return ApiResponse.success(stockService.addStock(stock));
    }

    @PutMapping("/{stockId}")
    public ApiResponse<Stock> updateStock(
            @PathVariable Long stockId,
            @RequestParam Integer quantity) {
        return ApiResponse.success(stockService.updateStock(stockId, quantity));
    }

    @PostMapping("/consume")
    public ApiResponse<Void> consumeStock(
            @RequestParam Long warehouseId,
            @RequestParam Long medicineId,
            @RequestParam Integer quantity,
            @RequestParam(required = false) String department) {
        stockService.consumeStock(warehouseId, medicineId, quantity, department);
        return ApiResponse.success();
    }

    @GetMapping("/{stockId}")
    public ApiResponse<Stock> getStockById(@PathVariable Long stockId) {
        return ApiResponse.success(stockService.getStockById(stockId));
    }

    @GetMapping("/warehouse/{warehouseId}")
    public ApiResponse<List<Stock>> getStocksByWarehouse(@PathVariable Long warehouseId) {
        return ApiResponse.success(stockService.getStocksByWarehouse(warehouseId));
    }

    @GetMapping("/medicine/{medicineId}")
    public ApiResponse<List<Stock>> getStocksByMedicine(@PathVariable Long medicineId) {
        return ApiResponse.success(stockService.getStocksByMedicine(medicineId));
    }
}
