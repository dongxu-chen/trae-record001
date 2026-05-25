package com.property.repair.service;

import com.property.repair.dto.OrderCompleteDTO;
import com.property.repair.dto.RepairSubmitDTO;
import com.property.repair.entity.RepairOrder;
import com.property.repair.entity.RepairType;
import com.property.repair.entity.SysUser;
import com.property.repair.repository.RepairOrderRepository;
import com.property.repair.repository.SysUserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.UUID;

@Service
public class RepairOrderService {

    @Autowired
    private RepairOrderRepository orderRepository;

    @Autowired
    private RepairTypeService repairTypeService;

    @Autowired
    private DispatchService dispatchService;

    @Autowired
    private RepairWorkerService workerService;

    @Autowired
    private RepairLogService logService;

    @Autowired
    private SysUserRepository userRepository;

    @Transactional
    public RepairOrder submitRepair(RepairSubmitDTO dto) {
        RepairType type = repairTypeService.getById(dto.getRepairTypeId());
        if (type == null) {
            throw new RuntimeException("报修类型不存在");
        }

        RepairOrder order = new RepairOrder();
        order.setOrderNo(generateOrderNo());
        order.setOwnerId(dto.getOwnerId());
        order.setOwnerName(dto.getOwnerName());
        order.setOwnerPhone(dto.getOwnerPhone());
        order.setRepairTypeId(dto.getRepairTypeId());
        order.setRepairTypeName(type.getTypeName());
        order.setAddress(dto.getAddress());
        order.setLongitude(dto.getLongitude());
        order.setLatitude(dto.getLatitude());
        order.setDescription(dto.getDescription());
        order.setImages(dto.getImages());
        order.setCompressedImages(dto.getCompressedImages());
        order.setPriority(type.getPriority());
        order.setEstimatedHours(type.getEstimatedHours());
        order.setStatus("PENDING");

        order = orderRepository.save(order);

        logService.addLog(order, "提交报修", dto.getOwnerId(), dto.getOwnerName(), 
            "报修类型：" + type.getTypeName() + "，描述：" + dto.getDescription());

        dispatchService.autoDispatch(order);

        return order;
    }

    @Transactional
    public RepairOrder acceptOrder(Long orderId, Long workerId) {
        RepairOrder order = orderRepository.findById(orderId).orElse(null);
        if (order == null) {
            throw new RuntimeException("工单不存在");
        }
        if (!"ASSIGNED".equals(order.getStatus())) {
            throw new RuntimeException("只有已派单的工单才能接单");
        }
        if (!order.getWorkerId().equals(workerId)) {
            throw new RuntimeException("只能接分配给自己的工单");
        }

        order.setStatus("IN_PROGRESS");
        order.setAcceptTime(LocalDateTime.now());
        orderRepository.save(order);

        SysUser worker = userRepository.findById(workerId).orElse(null);
        logService.addLog(order, "接单", workerId, worker != null ? worker.getRealName() : "维修工", "维修工已接单");

        return order;
    }

    @Transactional
    public RepairOrder completeOrder(OrderCompleteDTO dto) {
        RepairOrder order = orderRepository.findById(dto.getOrderId()).orElse(null);
        if (order == null) {
            throw new RuntimeException("工单不存在");
        }
        if (!"IN_PROGRESS".equals(order.getStatus())) {
            throw new RuntimeException("只有进行中的工单才能完成");
        }

        order.setStatus("COMPLETED");
        order.setCompleteTime(LocalDateTime.now());
        order.setActualHours(dto.getActualHours());
        order.setFeedBack(dto.getFeedBack());
        orderRepository.save(order);

        workerService.decreaseWorkload(order.getWorkerId());

        SysUser worker = userRepository.findById(order.getWorkerId()).orElse(null);
        logService.addLog(order, "完工", order.getWorkerId(), 
            worker != null ? worker.getRealName() : "维修工", 
            "实际耗时：" + dto.getActualHours() + "小时，反馈：" + dto.getFeedBack());

        return order;
    }

    @Transactional
    public RepairOrder manualAssign(Long orderId, Long workerId, Long operatorId) {
        RepairOrder order = orderRepository.findById(orderId).orElse(null);
        if (order == null) {
            throw new RuntimeException("工单不存在");
        }

        SysUser worker = workerService.getWorkerUser(workerId);
        if (worker == null) {
            throw new RuntimeException("维修工不存在");
        }

        if (order.getWorkerId() != null) {
            workerService.decreaseWorkload(order.getWorkerId());
        }

        order.setWorkerId(workerId);
        order.setWorkerName(worker.getRealName());
        order.setWorkerPhone(worker.getPhone());
        order.setStatus("ASSIGNED");
        order.setAssignTime(LocalDateTime.now());
        orderRepository.save(order);

        workerService.increaseWorkload(workerId);

        SysUser operator = userRepository.findById(operatorId).orElse(null);
        logService.addLog(order, "人工派单", operatorId, 
            operator != null ? operator.getRealName() : "管理员", 
            "分配给维修工：" + worker.getRealName());

        return order;
    }

    public RepairOrder getById(Long id) {
        return orderRepository.findById(id).orElse(null);
    }

    public RepairOrder getByOrderNo(String orderNo) {
        return orderRepository.findByOrderNo(orderNo);
    }

    public List<RepairOrder> getOwnerOrders(Long ownerId) {
        return orderRepository.findByOwnerIdOrderByCreateTimeDesc(ownerId);
    }

    public List<RepairOrder> getWorkerOrders(Long workerId) {
        return orderRepository.findByWorkerIdOrderByCreateTimeDesc(workerId);
    }

    public List<RepairOrder> getPendingOrders() {
        return orderRepository.findByStatus("PENDING");
    }

    public List<RepairOrder> getAllOrders() {
        return orderRepository.findAll();
    }

    private String generateOrderNo() {
        String date = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        String uuid = UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
        return "BX" + date + uuid;
    }
}
