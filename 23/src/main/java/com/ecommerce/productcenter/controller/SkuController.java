package com.ecommerce.productcenter.controller;

import com.ecommerce.productcenter.entity.Sku;
import com.ecommerce.productcenter.entity.StockLog;
import com.ecommerce.productcenter.service.SkuService;
import com.ecommerce.productcenter.service.StockService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/skus")
@RequiredArgsConstructor
public class SkuController {

    private final SkuService skuService;
    private final StockService stockService;

    @GetMapping
    public ResponseEntity<Map<String, Object>> getAllSkus(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(defaultValue = "id") String sortBy,
            @RequestParam(defaultValue = "asc") String sortDir) {

        Sort sort = sortDir.equalsIgnoreCase("desc")
                ? Sort.by(sortBy).descending()
                : Sort.by(sortBy).ascending();
        Pageable pageable = PageRequest.of(page, size, sort);

        Page<Sku> skuPage = skuService.getAllSkus(pageable);

        Map<String, Object> response = new HashMap<>();
        response.put("skus", skuPage.getContent());
        response.put("currentPage", skuPage.getNumber());
        response.put("totalItems", skuPage.getTotalElements());
        response.put("totalPages", skuPage.getTotalPages());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Sku> getSkuById(@PathVariable Long id) {
        return skuService.getSkuById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/code/{skuCode}")
    public ResponseEntity<Sku> getSkuByCode(@PathVariable String skuCode) {
        return skuService.getSkuByCode(skuCode)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/product/{productId}")
    public ResponseEntity<List<Sku>> getSkusByProductId(@PathVariable Long productId) {
        List<Sku> skus = skuService.getSkusByProductId(productId);
        return ResponseEntity.ok(skus);
    }

    @PostMapping
    public ResponseEntity<Sku> createSku(@RequestBody Sku sku) {
        Sku createdSku = skuService.createSku(sku);
        return ResponseEntity.status(HttpStatus.CREATED).body(createdSku);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Sku> updateSku(
            @PathVariable Long id,
            @RequestBody Sku skuDetails) {
        return skuService.updateSku(id, skuDetails)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteSku(@PathVariable Long id) {
        boolean deleted = skuService.deleteSku(id);
        if (deleted) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.notFound().build();
    }

    @DeleteMapping("/{id}/hard")
    public ResponseEntity<Void> hardDeleteSku(@PathVariable Long id) {
        boolean deleted = skuService.hardDeleteSku(id);
        if (deleted) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.notFound().build();
    }

    @GetMapping("/{skuId}/stock")
    public ResponseEntity<Map<String, Object>> getStock(@PathVariable Long skuId) {
        Integer stock = stockService.getStock(skuId);
        if (stock == null) {
            return ResponseEntity.notFound().build();
        }
        Map<String, Object> response = new HashMap<>();
        response.put("skuId", skuId);
        response.put("stock", stock);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{skuId}/stock/deduct")
    public ResponseEntity<Map<String, Object>> deductStock(
            @PathVariable Long skuId,
            @RequestBody Map<String, Object> request) {

        Integer quantity = (Integer) request.get("quantity");
        String orderNo = (String) request.get("orderNo");

        if (quantity == null || orderNo == null) {
            return ResponseEntity.badRequest().build();
        }

        boolean success = stockService.deductStock(skuId, quantity, orderNo);

        Map<String, Object> response = new HashMap<>();
        response.put("success", success);
        response.put("skuId", skuId);
        response.put("quantity", quantity);
        response.put("orderNo", orderNo);

        if (success) {
            return ResponseEntity.ok(response);
        } else {
            response.put("message", "库存不足或扣减失败");
            return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
        }
    }

    @PostMapping("/{skuId}/stock/increase")
    public ResponseEntity<Map<String, Object>> increaseStock(
            @PathVariable Long skuId,
            @RequestBody Map<String, Object> request) {

        Integer quantity = (Integer) request.get("quantity");
        String remark = (String) request.get("remark");

        if (quantity == null) {
            return ResponseEntity.badRequest().build();
        }

        boolean success = stockService.increaseStock(skuId, quantity, remark);

        Map<String, Object> response = new HashMap<>();
        response.put("success", success);
        response.put("skuId", skuId);
        response.put("quantity", quantity);

        if (success) {
            return ResponseEntity.ok(response);
        } else {
            response.put("message", "库存增加失败");
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    @PostMapping("/{skuId}/stock/release")
    public ResponseEntity<Map<String, Object>> releaseStock(
            @PathVariable Long skuId,
            @RequestBody Map<String, Object> request) {

        Integer quantity = (Integer) request.get("quantity");
        String orderNo = (String) request.get("orderNo");

        if (quantity == null || orderNo == null) {
            return ResponseEntity.badRequest().build();
        }

        boolean success = stockService.releaseStock(skuId, quantity, orderNo);

        Map<String, Object> response = new HashMap<>();
        response.put("success", success);
        response.put("skuId", skuId);
        response.put("quantity", quantity);
        response.put("orderNo", orderNo);

        if (success) {
            return ResponseEntity.ok(response);
        } else {
            response.put("message", "库存释放失败");
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }

    @GetMapping("/{skuId}/stock/logs")
    public ResponseEntity<List<StockLog>> getStockLogs(@PathVariable Long skuId) {
        List<StockLog> logs = stockService.getStockLogs(skuId);
        return ResponseEntity.ok(logs);
    }

    @PostMapping("/stock/batch-deduct")
    public ResponseEntity<Map<String, Object>> batchDeductStock(
            @RequestBody Map<String, Object> request) {

        @SuppressWarnings("unchecked")
        Map<String, Integer> skuQuantityMap = (Map<String, Integer>) request.get("skuQuantities");
        String orderNo = (String) request.get("orderNo");

        if (skuQuantityMap == null || orderNo == null) {
            return ResponseEntity.badRequest().build();
        }

        Map<Long, Integer> convertedMap = new HashMap<>();
        for (Map.Entry<String, Integer> entry : skuQuantityMap.entrySet()) {
            convertedMap.put(Long.parseLong(entry.getKey()), entry.getValue());
        }

        boolean success = stockService.batchDeductStock(convertedMap, orderNo);

        Map<String, Object> response = new HashMap<>();
        response.put("success", success);
        response.put("orderNo", orderNo);

        if (success) {
            return ResponseEntity.ok(response);
        } else {
            response.put("message", "批量扣减库存失败");
            return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
        }
    }
}
