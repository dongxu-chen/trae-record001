package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.SupplierOrderDTO;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.PurchasePlan;
import com.medical.stockwarning.entity.Supplier;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.enums.ApprovalStatus;
import com.medical.stockwarning.enums.PurchaseStatus;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.PurchasePlanRepository;
import com.medical.stockwarning.repository.StockRepository;
import com.medical.stockwarning.repository.SupplierRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class SupplierIntegrationService {

    private final PurchasePlanRepository purchasePlanRepository;
    private final SupplierRepository supplierRepository;
    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;
    private final StockRepository stockRepository;
    private final MedicineAssociationService associationService;
    private final TrendForecastService trendForecastService;

    @Value("${app.supplier.endpoint:http://localhost:8081/api/supplier/orders}")
    private String supplierEndpoint;

    @Value("${app.supplier.api-key:}")
    private String supplierApiKey;

    @Value("${app.supplier.connect-timeout:30000}")
    private int connectTimeout;

    private static final DateTimeFormatter ORDER_NO_FORMAT = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    @Transactional
    public SupplierOrderDTO generateSupplierOrder(Long supplierId, Long warehouseId,
                                                   List<PurchasePlan> plans) {
        Supplier supplier = supplierRepository.findById(supplierId)
                .orElseThrow(() -> new IllegalArgumentException("Supplier not found: " + supplierId));
        Warehouse warehouse = warehouseRepository.findById(warehouseId)
                .orElseThrow(() -> new IllegalArgumentException("Warehouse not found: " + warehouseId));

        String orderNo = generateOrderNo();

        List<SupplierOrderDTO.OrderItem> items = new ArrayList<>();
        BigDecimal totalAmount = BigDecimal.ZERO;

        for (PurchasePlan plan : plans) {
            Medicine medicine = medicineRepository.findById(plan.getMedicineId()).orElse(null);

            SupplierOrderDTO.OrderItem item = SupplierOrderDTO.OrderItem.builder()
                    .medicineId(plan.getMedicineId())
                    .medicineCode(medicine != null ? medicine.getMedicineCode() : null)
                    .medicineName(medicine != null ? medicine.getMedicineName() : null)
                    .specification(medicine != null ? medicine.getSpecification() : null)
                    .quantity(plan.getPlanQuantity())
                    .unitPrice(plan.getUnitPrice() != null ? plan.getUnitPrice() : BigDecimal.ZERO)
                    .totalAmount(plan.getTotalAmount() != null ? plan.getTotalAmount() :
                            (plan.getUnitPrice() != null ? plan.getUnitPrice().multiply(BigDecimal.valueOf(plan.getPlanQuantity())) : BigDecimal.ZERO))
                    .expectedDeliveryDate(plan.getExpectedDate() != null ? plan.getExpectedDate() :
                            LocalDate.now().plusDays(supplier.getLeadTimeDays()))
                    .build();

            items.add(item);
            totalAmount = totalAmount.add(item.getTotalAmount());

            plan.setStatus(PurchaseStatus.ORDERED);
            plan.setOrderDate(LocalDateTime.now());
            plan.setSupplierId(supplierId);
            purchasePlanRepository.save(plan);
        }

        SupplierOrderDTO order = SupplierOrderDTO.builder()
                .orderNo(orderNo)
                .supplierId(supplierId)
                .supplierName(supplier.getSupplierName())
                .supplierCode(supplier.getSupplierCode())
                .warehouseId(warehouseId)
                .warehouseName(warehouse.getWarehouseName())
                .orderDate(LocalDate.now())
                .expectedDeliveryDate(LocalDate.now().plusDays(supplier.getLeadTimeDays()))
                .totalAmount(totalAmount)
                .totalItems(items.size())
                .status("PENDING")
                .orderType("NORMAL")
                .items(items)
                .build();

        log.info("Generated supplier order: orderNo={}, supplier={}, items={}, totalAmount={}",
                orderNo, supplier.getSupplierName(), items.size(), totalAmount);

        return order;
    }

    @Transactional
    public List<SupplierOrderDTO> generateOrdersBySupplier() {
        List<PurchasePlan> approvedPlans = purchasePlanRepository.findByApprovalStatus(ApprovalStatus.APPROVED)
                .stream()
                .filter(p -> p.getStatus() == PurchaseStatus.APPROVED)
                .toList();

        if (approvedPlans.isEmpty()) {
            log.info("No approved plans to convert to supplier orders");
            return Collections.emptyList();
        }

        Map<Long, List<PurchasePlan>> plansByWarehouse = approvedPlans.stream()
                .collect(Collectors.groupingBy(PurchasePlan::getWarehouseId));

        List<SupplierOrderDTO> orders = new ArrayList<>();

        for (Map.Entry<Long, List<PurchasePlan>> entry : plansByWarehouse.entrySet()) {
            Long warehouseId = entry.getKey();
            List<PurchasePlan> warehousePlans = entry.getValue();

            Long supplierId = findBestSupplier(warehousePlans);

            if (supplierId != null) {
                SupplierOrderDTO order = generateSupplierOrder(supplierId, warehouseId, warehousePlans);
                orders.add(order);
            }
        }

        return orders;
    }

    @Transactional
    public List<SupplierOrderDTO> generateAssociatedOrders(Long medicineId, Long warehouseId) {
        List<Long> associatedMedicineIds = associationService.getAssociatedMedicineIds(medicineId);

        if (associatedMedicineIds.isEmpty()) {
            log.info("No associated medicines found for medicineId={}", medicineId);
            return Collections.emptyList();
        }

        List<Long> allMedicineIds = new ArrayList<>(associatedMedicineIds);
        allMedicineIds.add(medicineId);

        List<PurchasePlan> existingPlans = purchasePlanRepository.findByStatus(PurchaseStatus.PENDING)
                .stream()
                .filter(p -> p.getWarehouseId().equals(warehouseId))
                .filter(p -> allMedicineIds.contains(p.getMedicineId()))
                .toList();

        Set<Long> existingMedicineIds = existingPlans.stream()
                .map(PurchasePlan::getMedicineId)
                .collect(Collectors.toSet());

        List<PurchasePlan> newPlans = new ArrayList<>(existingPlans);

        for (Long associatedId : associatedMedicineIds) {
            if (!existingMedicineIds.contains(associatedId)) {
                PurchasePlan plan = createAssociatedPlan(associatedId, warehouseId);
                if (plan != null) {
                    newPlans.add(plan);
                }
            }
        }

        if (newPlans.isEmpty()) {
            return Collections.emptyList();
        }

        Long supplierId = findBestSupplier(newPlans);
        if (supplierId == null) {
            log.warn("No suitable supplier found for associated orders");
            return Collections.emptyList();
        }

        SupplierOrderDTO order = generateSupplierOrder(supplierId, warehouseId, newPlans);
        order.setOrderType("ASSOCIATED");
        order.setRemark("Auto-generated based on medicine association analysis");

        return List.of(order);
    }

    public SupplierOrderDTO sendOrderToSupplier(SupplierOrderDTO order) {
        log.info("Sending order to supplier system: orderNo={}", order.getOrderNo());

        try {
            RestTemplate restTemplate = new RestTemplate();

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            if (supplierApiKey != null && !supplierApiKey.isEmpty()) {
                headers.set("X-API-Key", supplierApiKey);
            }

            HttpEntity<SupplierOrderDTO> requestEntity = new HttpEntity<>(order, headers);

            ResponseEntity<SupplierOrderDTO> response = restTemplate.exchange(
                    supplierEndpoint,
                    HttpMethod.POST,
                    requestEntity,
                    SupplierOrderDTO.class
            );

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                SupplierOrderDTO result = response.getBody();
                result.setSupplierSystemRef(response.getHeaders().getFirst("X-Order-Ref"));
                result.setStatus("SENT");

                log.info("Order sent successfully: orderNo={}, supplierRef={}",
                        result.getOrderNo(), result.getSupplierSystemRef());

                return result;
            } else {
                log.warn("Failed to send order: status={}", response.getStatusCode());
                order.setStatus("SEND_FAILED");
                return order;
            }
        } catch (Exception e) {
            log.error("Error sending order to supplier: {}", e.getMessage());
            order.setStatus("ERROR");
            order.setRemark("Send error: " + e.getMessage());
            return order;
        }
    }

    @Transactional
    public List<SupplierOrderDTO> sendAllPendingOrders() {
        List<SupplierOrderDTO> orders = generateOrdersBySupplier();
        List<SupplierOrderDTO> results = new ArrayList<>();

        for (SupplierOrderDTO order : orders) {
            SupplierOrderDTO sentOrder = sendOrderToSupplier(order);
            results.add(sentOrder);
        }

        return results;
    }

    public SupplierOrderDTO querySupplierOrderStatus(String orderNo) {
        String queryUrl = supplierEndpoint + "/" + orderNo;

        try {
            RestTemplate restTemplate = new RestTemplate();
            HttpHeaders headers = new HttpHeaders();
            if (supplierApiKey != null && !supplierApiKey.isEmpty()) {
                headers.set("X-API-Key", supplierApiKey);
            }
            HttpEntity<Void> requestEntity = new HttpEntity<>(headers);

            ResponseEntity<SupplierOrderDTO> response = restTemplate.exchange(
                    queryUrl,
                    HttpMethod.GET,
                    requestEntity,
                    SupplierOrderDTO.class
            );

            return response.getBody();
        } catch (Exception e) {
            log.error("Error querying supplier order status: {}", e.getMessage());
            return null;
        }
    }

    @Transactional
    public List<SupplierOrderDTO> generateForecastBasedOrders(Long warehouseId) {
        List<TrendForecastDTO> forecasts = trendForecastService.forecastAllMedicines(warehouseId, 30);

        List<PurchasePlan> forecastPlans = new ArrayList<>();

        for (TrendForecastDTO forecast : forecasts) {
            if (forecast.getIsSeasonal() && forecast.getTrendDirection().equals("UP")) {
                BigDecimal totalForecast = forecast.getTotalForecastedQuantity();

                Integer currentStock = getCurrentStock(warehouseId, forecast.getMedicineId());

                if (currentStock < totalForecast.intValue()) {
                    int quantityNeeded = totalForecast.intValue() - currentStock;
                    PurchasePlan plan = createForecastPlan(forecast, warehouseId, quantityNeeded);
                    if (plan != null) {
                        forecastPlans.add(plan);
                    }
                }
            }
        }

        if (forecastPlans.isEmpty()) {
            return Collections.emptyList();
        }

        Map<Long, List<PurchasePlan>> plansBySupplier = forecastPlans.stream()
                .filter(p -> p.getSupplierId() != null)
                .collect(Collectors.groupingBy(PurchasePlan::getSupplierId));

        List<SupplierOrderDTO> orders = new ArrayList<>();
        for (Map.Entry<Long, List<PurchasePlan>> entry : plansBySupplier.entrySet()) {
            SupplierOrderDTO order = generateSupplierOrder(entry.getKey(), warehouseId, entry.getValue());
            order.setOrderType("FORECAST");
            order.setRemark("Auto-generated based on trend forecast");
            orders.add(order);
        }

        return orders;
    }

    private PurchasePlan createAssociatedPlan(Long medicineId, Long warehouseId) {
        try {
            Medicine medicine = medicineRepository.findById(medicineId).orElse(null);
            if (medicine == null) return null;

            PurchasePlan plan = new PurchasePlan();
            plan.setPlanNo(generateOrderNo());
            plan.setMedicineId(medicineId);
            plan.setWarehouseId(warehouseId);
            plan.setPlanQuantity(10);
            plan.setPlanDate(LocalDate.now());
            plan.setStatus(PurchaseStatus.PENDING);
            plan.setApprovalStatus(ApprovalStatus.PENDING);
            plan.setRemark("Auto-generated based on association");

            return purchasePlanRepository.save(plan);
        } catch (Exception e) {
            log.error("Error creating associated plan: {}", e.getMessage());
            return null;
        }
    }

    private PurchasePlan createForecastPlan(TrendForecastDTO forecast, Long warehouseId, int quantity) {
        try {
            PurchasePlan plan = new PurchasePlan();
            plan.setPlanNo(generateOrderNo());
            plan.setMedicineId(forecast.getMedicineId());
            plan.setWarehouseId(warehouseId);
            plan.setPlanQuantity(quantity);
            plan.setPlanDate(LocalDate.now());
            plan.setStatus(PurchaseStatus.PENDING);
            plan.setApprovalStatus(ApprovalStatus.PENDING);
            plan.setRemark("Forecast-based: " + forecast.getTrendDirection() + " trend, season=" + forecast.getSeasonPattern());

            return purchasePlanRepository.save(plan);
        } catch (Exception e) {
            log.error("Error creating forecast plan: {}", e.getMessage());
            return null;
        }
    }

    private Integer getCurrentStock(Long warehouseId, Long medicineId) {
        Integer stock = stockRepository.sumAvailableQuantity(warehouseId, medicineId);
        return stock != null ? stock : 0;
    }

    private Long findBestSupplier(List<PurchasePlan> plans) {
        for (PurchasePlan plan : plans) {
            if (plan.getSupplierId() != null) {
                return plan.getSupplierId();
            }
        }
        List<Supplier> suppliers = supplierRepository.findByIsActive(1);
        return suppliers.isEmpty() ? null : suppliers.get(0).getId();
    }

    private String generateOrderNo() {
        String timestamp = LocalDateTime.now().format(ORDER_NO_FORMAT);
        int random = new Random().nextInt(1000);
        return "SO" + timestamp + String.format("%03d", random);
    }

    public Map<String, Object> getSupplierIntegrationStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("supplierEndpoint", supplierEndpoint);
        status.put("apiKeyConfigured", supplierApiKey != null && !supplierApiKey.isEmpty());
        status.put("connectTimeout", connectTimeout);

        long pendingPlans = purchasePlanRepository.findByApprovalStatus(ApprovalStatus.APPROVED)
                .stream()
                .filter(p -> p.getStatus() == PurchaseStatus.APPROVED)
                .count();
        status.put("pendingPlans", pendingPlans);

        return status;
    }
}
