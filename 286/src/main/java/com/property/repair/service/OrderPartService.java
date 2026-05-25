package com.property.repair.service;

import com.property.repair.dto.OrderPartDTO;
import com.property.repair.entity.OrderPart;
import com.property.repair.entity.RepairOrder;
import com.property.repair.entity.SparePart;
import com.property.repair.repository.OrderPartRepository;
import com.property.repair.repository.RepairOrderRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;

@Service
public class OrderPartService {

    @Autowired
    private OrderPartRepository orderPartRepository;

    @Autowired
    private RepairOrderRepository orderRepository;

    @Autowired
    private SparePartService sparePartService;

    @Autowired
    private RepairLogService logService;

    @Transactional
    public OrderPart addPartToOrder(OrderPartDTO dto) {
        RepairOrder order = orderRepository.findById(dto.getOrderId()).orElse(null);
        if (order == null) {
            throw new RuntimeException("工单不存在");
        }

        SparePart part = sparePartService.getById(dto.getPartId());
        if (part == null) {
            throw new RuntimeException("备件不存在");
        }

        if (!sparePartService.lockStock(dto.getPartId(), dto.getQuantity())) {
            throw new RuntimeException("库存不足，可用数量：" + part.getAvailableQuantity());
        }

        OrderPart orderPart = new OrderPart();
        orderPart.setOrderId(dto.getOrderId());
        orderPart.setOrderNo(order.getOrderNo());
        orderPart.setPartId(dto.getPartId());
        orderPart.setPartCode(part.getPartCode());
        orderPart.setPartName(part.getPartName());
        orderPart.setSpecification(part.getSpecification());
        orderPart.setUnit(part.getUnit());
        orderPart.setUnitPrice(part.getUnitPrice());
        orderPart.setQuantity(dto.getQuantity());
        orderPart.setTotalPrice(part.getUnitPrice() * dto.getQuantity());
        orderPart.setStatus("LOCKED");
        orderPart = orderPartRepository.save(orderPart);

        logService.addLog(order, "备件锁定", dto.getOperatorId(), dto.getOperatorName(),
            "锁定备件：" + part.getPartName() + "，数量：" + dto.getQuantity() + part.getUnit());

        return orderPart;
    }

    @Transactional
    public List<OrderPart> addPartsToOrder(Long orderId, List<OrderPartDTO> parts, 
                                           Long operatorId, String operatorName) {
        List<OrderPart> result = new ArrayList<>();
        
        for (OrderPartDTO partDTO : parts) {
            partDTO.setOrderId(orderId);
            partDTO.setOperatorId(operatorId);
            partDTO.setOperatorName(operatorName);
            result.add(addPartToOrder(partDTO));
        }
        
        return result;
    }

    @Transactional
    public boolean removePartFromOrder(Long orderPartId, Long operatorId, String operatorName) {
        OrderPart orderPart = orderPartRepository.findById(orderPartId).orElse(null);
        if (orderPart == null) {
            return false;
        }

        if (!"LOCKED".equals(orderPart.getStatus())) {
            throw new RuntimeException("只能删除锁定状态的备件");
        }

        sparePartService.unlockStock(orderPart.getPartId(), orderPart.getQuantity());
        orderPartRepository.delete(orderPart);

        RepairOrder order = orderRepository.findById(orderPart.getOrderId()).orElse(null);
        if (order != null) {
            logService.addLog(order, "备件解锁", operatorId, operatorName,
                "解锁备件：" + orderPart.getPartName() + "，数量：" + orderPart.getQuantity() + orderPart.getUnit());
        }

        return true;
    }

    @Transactional
    public void confirmPartsUsage(Long orderId, Long operatorId, String operatorName) {
        List<OrderPart> parts = orderPartRepository.findByOrderIdAndStatus(orderId, "LOCKED");
        
        for (OrderPart part : parts) {
            sparePartService.confirmUsage(part.getPartId(), part.getQuantity(), 
                orderId, operatorId, operatorName);
            part.setStatus("USED");
            orderPartRepository.save(part);
        }

        RepairOrder order = orderRepository.findById(orderId).orElse(null);
        if (order != null) {
            logService.addLog(order, "备件领用", operatorId, operatorName,
                "确认领用" + parts.size() + "种备件");
        }
    }

    public List<OrderPart> getOrderParts(Long orderId) {
        return orderPartRepository.findByOrderId(orderId);
    }
}
